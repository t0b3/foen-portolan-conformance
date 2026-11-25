"""Command line: `conformance run`, `conformance regression`, `conformance versions`."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config import load_config
from .http import Fetcher, RecordedTransport

EXIT_OK, EXIT_INFRA, EXIT_STRICT, EXIT_TOOL = 0, 2, 3, 4


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="conformance", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="crawl, validate and write the report")
    r.add_argument("--config", default="config.yaml")
    r.add_argument("--out", default="reports")
    r.add_argument("--catalog", action="append", help="catalog id (repeatable; default: all)")
    r.add_argument(
        "--mode",
        choices=["full", "light"],
        default="full",
        help="light = metadata + STAC only (no asset byte reads)",
    )
    r.add_argument("--max-asset-size-gb", type=float)
    r.add_argument("--strict", action="store_true", help="exit 3 if any MUST requirement fails")
    r.add_argument(
        "--require",
        action="append",
        default=[],
        metavar="BINARY",
        help="exit 4 before running if this tool is not on PATH (repeatable)",
    )
    r.add_argument(
        "--fail-on-tool-error",
        action="store_true",
        help="exit 4 if a tool crashed, timed out or is missing (used by the tool canary)",
    )
    r.add_argument(
        "--offline",
        metavar="INDEX_JSON",
        help="replay recorded HTTP responses instead of using the network",
    )
    r.add_argument(
        "--spec-file",
        metavar="REQUIREMENTS_YAML",
        help="use a local requirements.yaml instead of resolving the latest release",
    )
    r.add_argument("--spec-version", help="version label for --spec-file (e.g. 0.3.0)")
    r.add_argument("--quiet", action="store_true")

    g = sub.add_parser("regression", help="decide open/update/close for the regression issue")
    g.add_argument("--report", required=True)
    g.add_argument("--open-issue-body", help="file with the body of the currently open issue")
    g.add_argument("--pages-url")

    sub.add_parser("versions", help="print the installed tool versions as JSON")

    a = p.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "regression":
        return cmd_regression(a)
    if a.cmd == "versions":
        from .adapters import ALL_ADAPTERS
        from .runner import _tool_versions

        print(json.dumps(_tool_versions([c() for c in ALL_ADAPTERS]), indent=2))
        return 0
    return 1


def cmd_run(a) -> int:
    from .report import build_report, load_previous, write_outputs
    from .runner import execute
    from .spec import SpecInfo, parse_requirements
    from .toolchain import which

    missing = [b for b in a.require if not which(b)]
    if missing:
        print(f"required tool(s) not installed: {', '.join(missing)}", file=sys.stderr)
        return EXIT_TOOL
    cfg = load_config(a.config)
    if a.max_asset_size_gb is not None:
        cfg.limits["max_asset_size_gb"] = a.max_asset_size_gb
    transport = RecordedTransport(a.offline) if a.offline else None
    fetcher = Fetcher(
        timeout=float(cfg.limits["http_timeout_s"]),
        retries=int(cfg.limits["http_retries"]),
        transport=transport,
    )
    spec = None
    if a.spec_file:
        ver = a.spec_version
        spec = SpecInfo(
            cfg.spec["repo"],
            f"v{ver}" if ver else "local",
            ver,
            None,
            "local-file",
            parse_requirements(Path(a.spec_file).read_text()),
            f"Loaded from {a.spec_file}",
        )
    log = (lambda *_: None) if a.quiet else (lambda m: print(m, file=sys.stderr))
    run = execute(cfg, fetcher, mode=a.mode, catalog_ids=a.catalog, spec=spec, log=log)
    if not run.contexts:
        for e in run.infra_errors:
            print(f"infrastructure error: {e}", file=sys.stderr)
        return EXIT_INFRA

    out = Path(a.out) / ("light" if a.mode == "light" else "")
    out.mkdir(parents=True, exist_ok=True)
    prev, hist = load_previous(out)
    report = build_report(run, prev, hist)
    if a.offline:
        report["run"]["note"] = (
            f"Offline replay of recorded responses ({a.offline}): no network and only the tools "
            "installed locally. Hosting, data and docs checks that need live HTTP show up under Coverage."
        )
    written = write_outputs(report, out)
    s = report["summary"]
    log(f"wrote {', '.join(str(p) for p in written.values())}")
    print(
        f"conformance: {s['pct_fully_conformant']}% fully conformant, {s['must_failures']} MUST failures, "
        f"{s['should_warnings']} SHOULD warnings"
    )
    if summary_file := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary_file, "a") as fh:
            fh.write((out / "latest" / "report.md").read_text())

    if run.infra_errors:
        for e in run.infra_errors:
            print(f"infrastructure error: {e}", file=sys.stderr)
        return EXIT_INFRA
    if a.fail_on_tool_error and any(
        f.rule_id in ("tool-error", "tool-missing") for f in run.findings
    ):
        return EXIT_TOOL
    if a.strict and s["must_failures"] > 0:
        return EXIT_STRICT
    return EXIT_OK


def cmd_regression(a) -> int:
    from .regression import decide

    report = json.loads(Path(a.report).read_text())
    body = Path(a.open_issue_body).read_text() if a.open_issue_body else None
    print(json.dumps(decide(report, body or None, a.pages_url)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
