"""Assemble report.json and write every output file (json, md, html, csv, parquet, badge)."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

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
]


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
            }
    spec_d = spec.to_dict() | {"requirement_ids": sorted(spec.requirements)}
    summary = summarize(assets, findings, run.declared, spec_d)
    for c in summary["collections"]:
        meta = collections.get(f"{c['catalog_id']}/{c['collection']}", {})
        c.update({k: meta.get(k) for k in ("title", "url", "license", "browser")})

    referenced = sorted(
        {f["spec_requirement_id"] for f in findings if f.get("spec_requirement_id")}
    )
    requirements = {
        rid: spec.requirements[rid] | {"link": spec.link(rid)}
        for rid in referenced
        if rid in spec.requirements
    }
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
    }
    report["history"] = _history(history or [], report)
    return report


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
    (snap / "badge.json").write_text(json.dumps(badge(report)) + "\n")

    latest = out_dir / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(snap, latest)
    (out_dir / "history.json").write_text(json.dumps(report["history"], indent=2) + "\n")
    (out_dir / "badge.json").write_text(json.dumps(badge(report)) + "\n")
    _write_root_index(out_dir)
    for n in ("report.json", "report.md", "index.html", "findings.csv", "badge.json"):
        written[n] = snap / n
    return written


def _write_parquet(findings: list[dict], path: Path) -> bool:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        return False
    cols = {k: [f.get(k) for f in findings] for k in CSV_FIELDS}
    table = pa.table({k: pa.array(v, type=pa.string()) for k, v in cols.items()})
    pq.write_table(table, path, compression="zstd")
    return True


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
