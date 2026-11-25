"""Assemble report.json and write every output file (json, md, html, csv, parquet, badge)."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from .. import repro
from ..adapters.stac_validator import validate_subcommand
from ..runner import RunOutput
from .html import render_html
from .markdown import render_markdown
from .summary import diff, is_coverage, summarize

BROWSER = "https://browser.portolan-sdi.org/#/external/"
CSV_FIELDS = [
    "fingerprint",
    "catalog_id",
    "collection",
    "item",
    "asset_href",
    "format",
    "tool",
    "tool_version",
    "rule_id",
    "severity",
    "message",
    "spec_requirement_id",
    "check_id",
    "reproduce",
]
CHECK_FIELDS = [
    "id",
    "parent",
    "catalog_id",
    "collection",
    "item",
    "asset_href",
    "format",
    "tool",
    "tool_version",
    "name",
    "outcome",
    "evidence",
    "target",
    "command",
    "findings",
]


def dataset_commands(a, fmt: str) -> list[dict]:
    """Commands to inspect one asset by hand: its STAC entry, headers, magic bytes, validator."""
    cmds = [
        {"label": "STAC asset entry", "command": repro.stac_asset(a.owner_url, a.key)},
        {"label": "Headers of a ranged, cross-origin GET", "command": repro.range_get(a.href)},
        {"label": "Size and Accept-Ranges", "command": repro.head(a.href)},
        {"label": "First 16 bytes (format magic)", "command": repro.first_bytes(a.href, 16)},
    ]
    tool = {
        "geoparquet": ["gpio", "check", "all", a.href],
        "cog": ["rio", "cogeo", "validate", a.href, "--strict"],
        "geotiff": ["rio", "cogeo", "validate", a.href, "--strict"],
        "pmtiles": ["pmtiles", "show", a.href],
        "copc": ["pdal", "info", "--summary", a.href],
    }.get(fmt)
    if tool:
        cmds.append({"label": "Format validator", "command": repro.tool(tool, None)})
    if fmt == "zarr":
        cmds.append(
            {
                "label": "Zarr metadata",
                "command": repro.json_query(a.href.rstrip("/") + "/zarr.json", "."),
            }
        )
    return cmds


def browser_link(url: str) -> str | None:
    if url.startswith("https://") or url.startswith("http://"):
        return BROWSER + url.split("://", 1)[1]
    return None


def build_report(
    run: RunOutput, previous: dict | None = None, history: list[dict] | None = None
) -> dict:
    spec = run.spec
    findings = [f.to_dict() for f in run.findings]
    assets = []
    for ctx in run.contexts:
        for a in ctx.crawl.assets:
            fmt, how = ctx.formats.get(a.href, ("unknown", "unknown"))
            p = ctx.probes.get(a.href)
            assets.append(
                {
                    "catalog_id": a.catalog_id,
                    "collection": a.collection,
                    "item": a.item,
                    "key": a.key,
                    "href": a.href,
                    "media_type": a.media_type,
                    "roles": a.roles,
                    "format": fmt,
                    "detected_by": how,
                    "size": p.size if p else None,
                    "scored": not ctx.is_ancillary(a),
                    "verified_by": sorted(ctx.verified.get(a.href, ())),
                    "commands": dataset_commands(a, fmt),
                }
            )
    collections = {}
    for ctx in run.contexts:
        for o in ctx.crawl.collections:
            collections[f"{ctx.catalog_id}/{o.id}"] = {
                "catalog_id": ctx.catalog_id,
                "id": o.id,
                "title": o.data.get("title"),
                "url": o.url,
                "license": o.data.get("license"),
                "browser": browser_link(o.url),
                "commands": [
                    {"label": "Read the collection", "command": repro.json_query(o.url, ".")},
                    {
                        "label": "Validate the STAC JSON",
                        "command": repro.tool(
                            ["stac-validator", *validate_subcommand(), o.url], None
                        ),
                    },
                    {
                        "label": "Lint STAC best practices",
                        "command": repro.tool(["stac-check", o.url], None),
                    },
                ],
            }
    checks = _checks(run)
    spec_d = spec.to_dict() | {"requirement_ids": sorted(spec.requirements)}
    all_requirements = {
        rid: r | {"link": spec.link(rid)} for rid, r in sorted(spec.requirements.items())
    }
    summary = summarize(assets, findings, run.declared, spec_d, checks, all_requirements)
    for c in summary["collections"]:
        meta = collections.get(f"{c['catalog_id']}/{c['collection']}", {})
        c.update({k: meta.get(k) for k in ("title", "url", "license", "browser")})

    referenced = sorted(
        {f["spec_requirement_id"] for f in findings if f.get("spec_requirement_id")}
    )
    requirements = dict(all_requirements)
    for rid in referenced:  # IDs reported by a tool but absent from the manifest still get an entry
        requirements.setdefault(
            rid,
            {
                "severity": None,
                "file": None,
                "quote": "(not in the spec manifest used)",
                "link": None,
            },
        )
    coverage = list(run.coverage) + [
        {
            "catalog_id": f["catalog_id"],
            "tool": f["tool"],
            "collection": f.get("collection"),
            "asset_href": f.get("asset_href"),
            "reason": f["message"],
            "rule_id": f["rule_id"],
        }
        for f in findings
        if is_coverage(f)
    ]
    changes = diff(findings, previous.get("findings") if previous else None)
    report = {
        "schema": "foen-portolan-conformance/report@1",
        "run": {
            "started": run.started,
            "finished": run.finished,
            "mode": run.mode,
            "infra_errors": run.infra_errors,
            "previous_run": previous["run"]["started"] if previous else None,
            "reproduce": run_command(run),
        },
        "spec": {k: v for k, v in spec_d.items() if k != "requirement_ids"},
        "declared_spec": {k: v for k, v in run.declared.items() if k != "requirement_ids"},
        "tool_versions": run.tool_versions,
        "catalogs": run.catalogs,
        "summary": summary,
        "changes": {
            "baseline": changes["baseline"],
            "new": changes["new"],
            "resolved": changes["resolved"],
        },
        "coverage": sorted(
            coverage,
            key=lambda c: (
                c["catalog_id"],
                c["tool"],
                c.get("collection") or "",
                c.get("asset_href") or "",
                c["reason"],
            ),
        ),
        "requirements": requirements,
        "collections": sorted(collections.values(), key=lambda c: (c["catalog_id"], c["id"])),
        "assets": assets,
        "findings": findings,
        "checks": checks,
    }
    d = summary["drill"]
    d["changes.new"] = {
        "kind": "findings",
        "ids": [f["fingerprint"] for f in changes["new"]],
        "label": "New since the last run",
    }
    d["changes.resolved"] = {
        "kind": "findings",
        "ids": [f["fingerprint"] for f in changes["resolved"]],
        "label": "Resolved since the last run",
    }
    report["history"] = _history(history or [], report)
    return report


def _checks(run: RunOutput) -> list[dict]:
    seen: dict[str, dict] = {}
    for ctx in run.contexts:
        for c in sorted(ctx.checks, key=lambda c: c.sort_key()):
            seen.setdefault(c.id, c.to_dict())
    return list(seen.values())


PIP = {
    "rashid": "rashid",
    "portolan-cli": "portolan-cli",
    "stac-validator": "stac-valid",
    "stac-check": "stac-check",
    "gpio": "geoparquet-io",
    "rio-cogeo": "rio-cogeo",
}


def run_command(run: RunOutput) -> str:
    """Commands that reproduce the whole run with the same tool versions."""
    v = run.tool_versions
    lines = ["# Validators at the versions used in this run:"]
    for tool, pkg in PIP.items():
        ver = v.get(tool)
        if not ver:
            continue
        if tool == "rio-cogeo":
            lines.append(f"uv tool install --force rasterio --with rio-cogeo=={ver}")
        else:
            name = repro.package(tool, ver) if tool == "stac-validator" else pkg
            lines.append(f"uv tool install --force {name}=={ver}")
    for tool, repo in (("pmtiles", "protomaps/go-pmtiles"),):
        ver = v.get(tool)
        if ver and not ver.startswith("native"):
            lines.append(f"# {tool} {ver}: https://github.com/{repo}/releases/tag/v{ver}")
    cats = " ".join(f"--catalog {c['id']}" for c in run.catalogs)
    lines += [
        "# This repository at the same commit, then:",
        f"conformance run --config config.yaml --out reports/ --mode {run.mode} {cats}"
        f" --max-asset-size-gb {run.max_asset_size_gb:g}".replace("  ", " "),
    ]
    if run.spec and run.spec.ref:
        lines.append(
            f"# Spec: {run.spec.repo}@{run.spec.ref}"
            + (f" ({run.spec.sha})" if run.spec.sha else "")
        )
    return "\n".join(lines)


def _history(history: list[dict], report: dict) -> list[dict]:
    s = report["summary"]
    point = {
        "date": report["run"]["started"][:10],
        "started": report["run"]["started"],
        "pct_fully_conformant": s["pct_fully_conformant"],
        "pct_must_conformant": s["pct_must_conformant"],
        "must_failures": s["must_failures"],
        "should_warnings": s["should_warnings"],
        "scored_assets": s["scored_assets"],
        "spec_version": report["spec"]["version"],
    }
    keep = [h for h in history if h["date"] != point["date"]]
    return sorted([*keep, point], key=lambda h: h["date"])[-400:]


def badge(report: dict) -> dict:
    pct = report["summary"]["pct_fully_conformant"]
    if pct is None:
        return {
            "schemaVersion": 1,
            "label": "Portolan conformance",
            "message": "n/a",
            "color": "lightgrey",
        }
    color = (
        "brightgreen"
        if pct >= 90
        else "green"
        if pct >= 75
        else "yellow"
        if pct >= 50
        else "orange"
        if pct >= 25
        else "red"
    )
    return {
        "schemaVersion": 1,
        "label": "Portolan conformance",
        "message": f"{pct:g}%",
        "color": color,
    }


def write_outputs(report: dict, out_dir: Path) -> dict[str, Path]:
    """Write <out>/<date>/ and refresh <out>/latest/. Returns written paths."""
    date = report["run"]["started"][:10]
    snap = out_dir / date
    snap.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    report["run"]["findings_parquet"] = _have_pyarrow()
    if report["run"]["findings_parquet"]:
        report["run"]["parquet"] = {
            "format_version": PARQUET_FORMAT_VERSION,
            "data_page_version": PARQUET_DATA_PAGE_VERSION,
            "compression": "zstd",
        }
    (snap / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    )
    (snap / "report.md").write_text(render_markdown(report))
    (snap / "index.html").write_text(render_html(report))
    with (snap / "findings.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for f in report["findings"]:
            w.writerow(f)
    with (snap / "checks.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CHECK_FIELDS, extrasaction="ignore")
        w.writeheader()
        for c in report["checks"]:
            w.writerow(c | {"findings": " ".join(c["findings"])})
    (snap / "badge.json").write_text(json.dumps(badge(report)) + "\n")
    try:
        written |= write_parquet(report, snap)
    except ImportError:
        # pyarrow is a dependency; this only happens in a broken environment. The page says so.
        for stale in ("findings.parquet", "checks.parquet"):
            (snap / stale).unlink(missing_ok=True)

    latest = out_dir / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(snap, latest)
    (out_dir / "history.json").write_text(json.dumps(report["history"], indent=2) + "\n")
    (out_dir / "badge.json").write_text(json.dumps(badge(report)) + "\n")
    _write_root_index(out_dir)
    for n in ("report.json", "report.md", "index.html", "findings.csv", "checks.csv", "badge.json"):
        written[n] = snap / n
    return written


# Parquet output: format version 2.6 (the current 2.x format) with V2 data pages
# ("Parquet v2"), ZSTD, dictionary encoding and statistics. Typed, not all-strings.
PARQUET_FORMAT_VERSION = "2.6"
PARQUET_DATA_PAGE_VERSION = "2.0"


def _parquet_schemas():
    import pyarrow as pa

    s, ls = pa.string(), pa.list_(pa.string())
    findings = pa.schema(
        [
            ("fingerprint", s),
            ("catalog_id", s),
            ("collection", s),
            ("item", s),
            ("asset_href", s),
            ("format", s),
            ("tool", s),
            ("tool_version", s),
            ("rule_id", s),
            ("severity", s),
            ("message", s),
            ("spec_requirement_id", s),
            ("check_id", s),
            ("reproduce", s),
            ("is_coverage", pa.bool_()),
        ]
    )
    checks = pa.schema(
        [
            ("id", s),
            ("parent", s),
            ("catalog_id", s),
            ("collection", s),
            ("item", s),
            ("asset_href", s),
            ("format", s),
            ("tool", s),
            ("tool_version", s),
            ("name", s),
            ("outcome", s),
            ("evidence", s),
            ("target", s),
            ("command", s),
            ("findings", ls),
        ]
    )
    return findings, checks


def _have_pyarrow() -> bool:
    try:
        import pyarrow.parquet  # noqa: F401
    except ImportError:
        return False
    return True


def write_parquet(report: dict, snap: Path) -> dict[str, Path]:
    """findings.parquet and checks.parquet. Raises ImportError if pyarrow is missing."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    fs_schema, ck_schema = _parquet_schemas()
    meta = {
        b"foen-portolan-conformance": json.dumps(
            {
                "report_schema": report["schema"],
                "run_started": report["run"]["started"],
                "mode": report["run"]["mode"],
                "spec_version": report["spec"]["version"],
                "spec_ref": report["spec"]["ref"],
                "tool_versions": report["tool_versions"],
            }
        ).encode()
    }
    rows = [f | {"is_coverage": is_coverage(f)} for f in report["findings"]]
    tables = {
        "findings.parquet": pa.Table.from_pylist(rows, schema=fs_schema.with_metadata(meta)),
        "checks.parquet": pa.Table.from_pylist(
            report["checks"], schema=ck_schema.with_metadata(meta)
        ),
    }
    out = {}
    for name, table in tables.items():
        pq.write_table(
            table,
            snap / name,
            version=PARQUET_FORMAT_VERSION,
            data_page_version=PARQUET_DATA_PAGE_VERSION,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        out[name] = snap / name
    return out


def _write_root_index(out_dir: Path) -> None:
    snaps = sorted(
        (p.name for p in out_dir.iterdir() if p.is_dir() and p.name[:2] == "20"), reverse=True
    )
    links = "\n".join(f'<li><a href="{s}/">{s}</a></li>' for s in snaps)
    light = (
        '<p><a href="light/latest/">Lightweight daily run</a></p>'
        if (out_dir / "light" / "latest").exists()
        else ""
    )
    (
        out_dir / "index.html"
    ).write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=latest/"><title>Portolan conformance reports</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:2rem;color:#191919}}</style></head><body>
<h1>Portolan conformance reports</h1><p><a href="latest/">Latest report</a></p>{light}
<h2>Snapshots</h2><ul>{links}</ul></body></html>
""")


def load_previous(out_dir: Path) -> tuple[dict | None, list[dict]]:
    prev = None
    p = out_dir / "latest" / "report.json"
    if p.exists():
        try:
            prev = json.loads(p.read_text())
        except ValueError:
            prev = None
    hist = []
    h = out_dir / "history.json"
    if h.exists():
        try:
            hist = json.loads(h.read_text())
        except ValueError:
            hist = []
    return prev, hist
