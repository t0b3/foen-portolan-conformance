"""End-to-end offline runs: report files, determinism, diffs, regression issue logic."""

from __future__ import annotations

import json
import re

from conformance.cli import main
from conformance.regression import decide
from conformance.report import build_report, write_outputs
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
