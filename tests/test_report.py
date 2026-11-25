"""End-to-end offline runs: report files, determinism, diffs, regression issue logic."""

from __future__ import annotations

import json
import re

from conformance.cli import main
from conformance.regression import decide
from conformance.report import build_report, write_outputs
from conformance.report.markdown import render_markdown
from conformance.runner import execute

from conftest import RECORDED


def _run(config, fetcher, spec, mode="full"):
    return execute(config, fetcher, mode=mode, spec=spec, log=lambda *_: None)


def test_offline_bafu_report(config, recorded_fetcher, spec, tmp_path):
    run = _run(config, recorded_fetcher, spec)
    rep = build_report(run)
    s = rep["summary"]
    assert (
        s["scored_assets"] == 15
    )  # 9 parquet + 5 gpkg + 1 pmtiles; thumbnails/styles are ancillary
    # No validator ran offline, so nothing may be called conformant.
    assert s["fully_conformant_assets"] == 0 and s["unverified_assets"] == 10
    nc = [f for f in rep["findings"] if f["rule_id"] == "CNC-FMT-001"]
    assert len(nc) == 5 and all("GeoPackage" in f["message"] for f in nc)
    assert any(
        f["rule_id"] == "CNC-META-001" and f["collection"] == "naqua_regions"
        for f in rep["findings"]
    )
    assert (
        rep["declared_spec"]["primary"] == "0.1.2" and rep["declared_spec"]["behind_latest"] is True
    )
    assert rep["spec"]["version"] == "0.3.0"
    for f in rep["findings"]:  # acceptance 3: traceable to a tool and version
        assert f["tool"] and "tool_version" in f
    paths = write_outputs(rep, tmp_path)
    for name in ("report.json", "report.md", "index.html", "findings.csv", "badge.json"):
        assert paths[name].exists() and (tmp_path / "latest" / name).exists()
    html = (tmp_path / "latest" / "index.html").read_text()
    assert not re.search(r"<(script|link)[^>]+(src|href)=\"https?://", html), "no external CDN"
    assert json.loads((tmp_path / "badge.json").read_text())["schemaVersion"] == 1


def test_rerun_is_deterministic(config, recorded_fetcher, spec):
    a = build_report(_run(config, recorded_fetcher, spec))
    b = build_report(_run(config, recorded_fetcher, spec))
    assert json.dumps(a["findings"]) == json.dumps(b["findings"])
    assert json.dumps(a["summary"]) == json.dumps(b["summary"])


def test_changes_and_regression_issue(config, recorded_fetcher, spec):
    first = build_report(_run(config, recorded_fetcher, spec))
    assert first["changes"]["baseline"]
    # Second run: inject a new MUST failure.
    run = _run(config, recorded_fetcher, spec)
    from conformance.normalize import Finding

    run.findings.append(
        Finding(
            catalog_id="bafu-portolan",
            tool="rashid",
            tool_version="0.5.0",
            rule_id="PTL-COL-001",
            severity="error",
            message="new problem",
            collection="ub",
            spec_requirement_id="PORTO-CORE-001",
        )
    )
    second = build_report(
        run,
        previous=first,
        history=first["history"][:-1] + [first["history"][-1] | {"date": "2000-01-01"}],
    )
    assert [f["rule_id"] for f in second["changes"]["new"]] == ["PTL-COL-001"]
    assert second["requirements"]["PORTO-CORE-001"]["quote"].startswith("A Portolan catalog MUST")
    d = decide(second, None)
    assert d["action"] == "open" and "new problem" in d["body"] and "fingerprints:" in d["body"]
    # Third run: the problem is gone -> close.
    third = build_report(
        _run(config, recorded_fetcher, spec), previous=second, history=second["history"]
    )
    assert decide(third, d["body"])["action"] == "close"
    assert decide(third, None)["action"] == "none"


def test_light_mode_skips_data_adapters(config, recorded_fetcher, spec):
    run = _run(config, recorded_fetcher, spec, mode="light")
    tools = {f.tool for f in run.findings}
    assert "gpio" not in tools and "hosting-probe" not in tools
    assert any(c["tool"] == "gpio" and "lightweight" in c["reason"] for c in run.coverage)


def test_cli_offline(tmp_path, capsys):
    req = tmp_path / "req.yaml"
    req.write_text("requirements: []\n")
    rc = main(
        [
            "run",
            "--config",
            "config.yaml",
            "--out",
            str(tmp_path),
            "--offline",
            str(RECORDED),
            "--quiet",
            "--spec-version",
            "0.3.0",
            "--spec-file",
            str(req),
        ]
    )
    assert rc == 0
    assert "MUST failures" in capsys.readouterr().out
    assert main(
        [
            "run",
            "--config",
            "config.yaml",
            "--out",
            str(tmp_path),
            "--offline",
            str(RECORDED),
            "--quiet",
            "--spec-file",
            str(tmp_path / "req.yaml"),
            "--fail-on-tool-error",
        ]
    ) in (0, 4)


def test_mini_catalog_native_checks(mini_config, spec):
    from conformance.http import Fetcher

    run = _run(mini_config, Fetcher(retries=0), spec)
    rep = build_report(run)
    rules = {(f["collection"], f["rule_id"]) for f in rep["findings"]}
    assert ("vector", "CNC-FMT-001") in rules  # legacy.gpkg
    assert ("tiles", "CNC-LIC-001") in rules and ("tiles", "CNC-META-001") in rules
    assert (None, "CRAWL-001") in rules
    pm = {
        (f["asset_href"].rsplit("/", 1)[-1], f["rule_id"])
        for f in rep["findings"]
        if f["tool"] == "pmtiles" and f["rule_id"].startswith("PMT")
    }
    assert pm == {("bad.pmtiles", "PMT-003"), ("bad.pmtiles", "PMT-010")}
    good = next(a for a in rep["assets"] if a["href"].endswith("good.pmtiles"))
    assert good["status"] == "pass" and "pmtiles" in good["verified_by"]


def _numbers(summary: dict):
    """Yield (drill_path, value) for every count shown in the summary."""
    for k in (
        "scored_assets",
        "ancillary_assets",
        "fully_conformant_assets",
        "must_conformant_assets",
        "unverified_assets",
        "must_failures",
        "should_warnings",
        "infos",
        "coverage_notes",
    ):
        yield k, summary[k]
    for k, v in summary["checks"].items():
        yield f"checks.{k}", v
    for g, v in summary["by_format"].items():
        for k in ("assets", "fully_conformant", "unverified", "errors", "warnings"):
            yield f"by_format.{g}.{k}", v[k]
    for c in summary["collections"]:
        for k in (
            "assets",
            "scored_assets",
            "fully_conformant",
            "unverified",
            "errors",
            "warnings",
            "infos",
            "checks",
            "checks_failed",
            "object_checks",
        ):
            yield f"{c['drill']}.{k}", c[k]
    gs = summary["grades"]
    yield "grades.graded", gs["graded"]
    yield "grades.ungraded", gs["ungraded"]
    for g, v in gs["overall"].items():
        yield f"grades.overall.{g}", v
    for fmt, row in gs["by_format"].items():
        for g, v in row.items():
            yield f"grades.{fmt}.{g}", v
    for ap in summary["anti_patterns"]:
        yield f"{ap['drill']}.findings", len(ap["findings"])
        yield f"{ap['drill']}.assets", len(ap["assets"])
        yield f"{ap['drill']}.must", ap["must"]
        yield f"{ap['drill']}.should", ap["should"]
        for r in ap["rules"]:
            yield r["drill"], r["count"]
    sc = summary["spec_conformance"]
    yield "spec_conformance.latest.must_failures", sc["latest"]["must_failures"]
    if sc["declared"]["must_failures"] is not None:
        yield "spec_conformance.declared.must_failures", sc["declared"]["must_failures"]


def test_every_number_drills_down_to_exactly_its_children(
    config, recorded_fetcher, spec, mini_config
):
    from conformance.http import Fetcher

    for cfg, fetcher in ((config, recorded_fetcher), (mini_config, Fetcher(retries=0))):
        rep = build_report(_run(cfg, fetcher, spec))
        s, d = rep["summary"], rep["summary"]["drill"]
        known = {
            "assets": {a["id"] for a in rep["assets"]},
            "findings": {f["fingerprint"] for f in rep["findings"]},
            "checks": {c["id"] for c in rep["checks"]},
            "requirements": set(rep["requirements"]),
        }
        n = 0
        for path, value in _numbers(s):
            assert path in d, path
            assert value == len(d[path]["ids"]), path
            assert set(d[path]["ids"]) <= known[d[path]["kind"]], path
            n += 1
        assert n > 30
        for sev in ("MUST", "SHOULD", "MAY"):
            assert (
                len(d[f"spec.requirement_counts.{sev}"]["ids"])
                == rep["spec"]["requirement_counts"][sev]
            )
        # Children of assets and checks resolve too.
        for a in rep["assets"]:
            assert (
                set(a["finding_ids"]) <= known["findings"]
                and set(a["check_ids"]) <= known["checks"]
            )
        for c in rep["checks"]:
            assert c["parent"] is None or c["parent"] in known["checks"], c
            assert set(c["findings"]) <= known["findings"]


def test_every_finding_is_reproducible_and_traced_to_a_check(
    config, recorded_fetcher, spec, mini_config
):
    from conformance.http import Fetcher

    for cfg, fetcher in ((config, recorded_fetcher), (mini_config, Fetcher(retries=0))):
        rep = build_report(_run(cfg, fetcher, spec))
        checks = {c["id"]: c for c in rep["checks"]}
        for f in rep["findings"]:
            assert f["reproduce"], f
            assert f["check_id"] in checks, f
            assert f["fingerprint"] in checks[f["check_id"]]["findings"]
        for c in rep["checks"]:
            assert c["command"], c
        for a in rep["assets"]:
            assert a["commands"] and all(x["command"] for x in a["commands"])
            if a["scored"]:
                assert a["check_ids"], a  # every scored dataset has at least one logged check
        assert rep["run"]["reproduce"].count("conformance run") == 1


def test_passing_checks_are_logged(mini_config, spec):
    from conformance.http import Fetcher

    rep = build_report(_run(mini_config, Fetcher(retries=0), spec))
    good = next(a for a in rep["assets"] if a["href"].endswith("good.pmtiles"))
    header = next(
        c for c in rep["checks"] if c["id"] in good["check_ids"] and c["name"] == "PMTiles header"
    )
    kids = [c for c in rep["checks"] if c["parent"] == header["id"]]
    assert {c["name"] for c in kids} >= {
        "magic bytes 'PMTiles'",
        "clustered (Hilbert order)",
        "bounds match STAC bbox",
    }
    assert all(c["outcome"] == "pass" for c in kids) and header["outcome"] == "pass"
    assert all("xxd" in c["command"] for c in kids)
    clustered = next(c for c in kids if c["name"].startswith("clustered"))
    assert clustered["evidence"] == "clustered=true"


def test_cli_require_missing_tool_exits_4(tmp_path):
    rc = main(
        [
            "run",
            "--require",
            "definitely-not-a-real-binary",
            "--offline",
            str(RECORDED),
            "--out",
            str(tmp_path),
            "--quiet",
        ]
    )
    assert rc == 4 and not any(tmp_path.iterdir())


def _parquet_file(path, version: int):
    import struct

    footer = bytes([0x15, version * 2]) + b"\x00" * 30
    path.write_bytes(b"PAR1" + b"\x00" * 64 + footer + struct.pack("<I", len(footer)) + b"PAR1")


def test_grades_and_anti_patterns_end_to_end(mini_dir, mini_config, spec, tmp_path):
    """good.parquet: v2 + every gpio check passes -> A. bad.parquet: v1 + 2 gpio warnings -> D."""
    import shutil

    from conformance.adapters.gpio import Gpio
    from conformance.config import CatalogConfig
    from conformance.http import Fetcher

    # Private copy: the shared fixture keeps its real GeoParquet files for the tool tests.
    path = tmp_path / "mini"
    shutil.copytree(mini_dir[0], path)
    mini_config.catalogs = [CatalogConfig(id="mini", url=str(path / "catalog.json"))]
    _parquet_file(path / "vector" / "good.parquet", 2)
    _parquet_file(path / "vector" / "bad.parquet", 1)
    run = _run(mini_config, Fetcher(retries=0), spec)  # parquet-footer runs as part of the run
    ctx = run.contexts[0]
    g = Gpio()
    for name, text in (
        ("good.parquet", "✓ valid\n✓ bbox covering\n✓ ZSTD\n"),
        ("bad.parquet", "✓ valid\n⚠ not spatially sorted\n⚠ compression SNAPPY\n"),
    ):
        a = next(x for x in ctx.crawl.assets if x.href.endswith(name))
        run.findings += g.parse(ctx, a, "all", text, 0, use_json=False)
        ctx.verified.setdefault(a.href, set()).add("gpio")
    from conformance.normalize import sort_findings

    run.findings = sort_findings(run.findings)
    rep = build_report(run)
    by = {a["href"].rsplit("/", 1)[-1]: a for a in rep["assets"]}
    assert by["good.parquet"]["grade"]["grade"] == "A"
    bad = by["bad.parquet"]["grade"]
    assert (bad["grade"], bad["levels_dropped"]) == ("D", 3)  # Parquet v1 + 2 gpio warnings
    rules = {f["rule_id"] for f in rep["findings"] if f["fingerprint"] in bad["unmet"]}
    assert "CNC-PQ-001" in rules
    assert by["legacy.gpkg"]["grade"]["grade"] == "F"
    d = rep["summary"]["drill"]
    assert d[bad["drill"]]["ids"] == bad["unmet"]
    aps = rep["summary"]["anti_patterns"]
    keys = [x["key"] for x in aps]
    assert keys[0] == "not_cloud_native"  # critical first
    assert "no_spatial_index" in keys and "inefficient_layout" in keys
    sev = [x["severity"] for x in aps]
    order = ["critical", "high", "medium", "low"]
    assert sev == sorted(sev, key=order.index)
    md = render_markdown(rep)
    assert "## Where to start: anti-patterns by severity" in md and "| **D** | bad.parquet |" in md
