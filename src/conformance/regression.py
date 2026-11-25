"""Decide whether to open, update or close the single `conformance-regression` issue."""

from __future__ import annotations

import re

LABEL = "conformance-regression"
TITLE = "Conformance regression: new MUST failures in the Portolan catalog"
MARK = re.compile(r"<!--\s*fingerprints:\s*([0-9a-f,\s]*)-->")


def decide(report: dict, open_issue_body: str | None, pages_url: str | None = None) -> dict:
    s = report["summary"]
    hist = report.get("history") or []
    prev_must = hist[-2]["must_failures"] if len(hist) >= 2 else None
    cur_errors = {f["fingerprint"]: f for f in report["findings"] if f["severity"] == "error"}
    new_errors = [f for f in report["changes"]["new"] if f["severity"] == "error"]
    increased = prev_must is not None and s["must_failures"] > prev_must

    tracked: set[str] = set()
    if open_issue_body:
        m = MARK.search(open_issue_body)
        if m:
            tracked = {x.strip() for x in m.group(1).split(",") if x.strip()}

    if increased and new_errors:
        fps = sorted(tracked | {f["fingerprint"] for f in new_errors})
        still = [cur_errors[fp] for fp in fps if fp in cur_errors]
        return {
            "action": "update" if open_issue_body else "open",
            "title": TITLE,
            "label": LABEL,
            "body": _body(report, still, prev_must, pages_url, fps),
        }
    if open_issue_body is not None and tracked and not (tracked & cur_errors.keys()):
        return {
            "action": "close",
            "title": TITLE,
            "label": LABEL,
            "body": f"All tracked MUST failures are resolved as of {report['run']['started']}. Closing.",
        }
    return {"action": "none", "title": TITLE, "label": LABEL, "body": ""}


def _body(
    report: dict, findings: list[dict], prev_must: int | None, pages_url: str | None, fps: list[str]
) -> str:
    s = report["summary"]
    lines = [
        f"MUST failures went from **{prev_must}** to **{s['must_failures']}** in the run of "
        f"{report['run']['started']} (spec {report['spec']['version'] or report['spec']['ref']}).",
        "",
    ]
    if pages_url:
        lines += [f"Full report: {pages_url}", ""]
    lines += [
        "| Collection | Asset | Tool | Rule | Requirement | Message |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings[:100]:
        asset = (f.get("asset_href") or "-").rsplit("/", 1)[-1]
        msg = f["message"].replace("|", "\\|").replace("\n", " ")[:300]
        lines.append(
            f"| {f.get('collection') or '-'} | {asset} | {f['tool']} {f.get('tool_version') or ''} | "
            f"`{f['rule_id']}` | {f.get('spec_requirement_id') or ''} | {msg} |"
        )
    if len(findings) > 100:
        lines.append(f"\n… and {len(findings) - 100} more.")
    lines += [
        "",
        "This issue closes automatically when every finding above is resolved.",
        f"<!-- fingerprints: {','.join(fps)} -->",
    ]
    return "\n".join(lines)
