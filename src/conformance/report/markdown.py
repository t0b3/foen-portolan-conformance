"""report.md: the human summary (also used as the PR comment and the job summary)."""

from __future__ import annotations


def _p(x) -> str:
    return "n/a" if x is None else f"{x:g}%"


def render_markdown(r: dict, max_rows: int = 25) -> str:
    s, spec, dec = r["summary"], r["spec"], r["declared_spec"]
    sc = s["spec_conformance"]
    L = ["# Portolan cloud-native conformance report", ""]
    for c in r["catalogs"]:
        L.append(
            f"- **{c['id']}**: {c.get('title') or ''} <{c['url']}>"
            + (
                f" — ERROR: {c['error']}"
                if c.get("error")
                else f" ({c['collections']} collections, {c['items']} items, {c['assets']} assets)"
            )
        )
    L += [
        "",
        f"Run: {r['run']['started']} ({r['run']['mode']} mode)",
        "",
        *([f"> **Note:** {r['run']['note']}", ""] if r["run"].get("note") else []),
        "| | |",
        "|---|---|",
        f"| Fully conformant assets | **{_p(s['pct_fully_conformant'])}** "
        f"({s['fully_conformant_assets']}/{s['scored_assets']}) |",
        f"| Assets without MUST failures | {_p(s['pct_must_conformant'])} "
        f"({s['must_conformant_assets']}/{s['scored_assets']}) |",
        f"| Unverified assets (validator did not run) | {s['unverified_assets']} |",
        f"| MUST failures (errors) | **{s['must_failures']}** |",
        f"| SHOULD warnings | {s['should_warnings']} |",
        f"| Coverage notes (skipped / tool issues) | {s['coverage_notes']} |",
        "",
        "## Spec version",
        "",
        f"- Latest spec: **{spec['version'] or spec['ref']}** ({spec['source']}, commit "
        f"`{(spec['commit_sha'] or 'unknown')[:12]}`), requirements "
        + ", ".join(f"{k} {v}" for k, v in spec["requirement_counts"].items()),
        f"- Declared by the catalog: **{dec.get('primary') or 'none'}**"
        + (f" (objects per version: {dec['versions']})" if dec.get("versions") else ""),
        f"- MUST failures against latest: {sc['latest']['must_failures']}; against declared: "
        f"{sc['declared']['must_failures'] if sc['declared']['must_failures'] is not None else 'n/a'}",
    ]
    if spec.get("note"):
        L.append(f"- Note: {spec['note']}")
    if sc["declared"].get("note"):
        L.append(f"- Note: {sc['declared']['note']}")
    if sc.get("behind_latest"):
        L.append(
            f"- ⚠️ The catalog declares an older Portolan version than the latest ({spec['version']})."
        )
    L += [
        "",
        "## By format",
        "",
        "| Format | Assets | Fully conformant | Unverified | Errors | Warnings |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for k, v in s["by_format"].items():
        L.append(
            f"| {k} | {v['assets']} | {v['fully_conformant']} ({_p(v['pct'])}) | {v['unverified']} | {v['errors']} | {v['warnings']} |"
        )
    L += [
        "",
        "## By collection",
        "",
        "| Collection | Scored assets | Fully conformant | Errors | Warnings |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in s["collections"]:
        name = c["collection"] or "(catalog level)"
        if c.get("browser"):
            name = f"[{name}]({c['browser']})"
        L.append(
            f"| {name} | {c['scored_assets']} | {c['fully_conformant']} ({_p(c['pct'])}) | "
            f"{c['errors']} | {c['warnings']} |"
        )
    ch = r["changes"]
    L += ["", "## Changes since last run", ""]
    if ch["baseline"]:
        L.append("First run: this report is the baseline.")
    else:
        L.append(f"{len(ch['new'])} new, {len(ch['resolved'])} resolved.")
        for title, rows in (("New", ch["new"]), ("Resolved", ch["resolved"])):
            if rows:
                L += ["", f"**{title}**", ""]
                L += [
                    f"- `{f['severity']}` {f['collection'] or '-'} · {f['tool']} `{f['rule_id']}`: {f['message']}"
                    for f in rows[:max_rows]
                ]
                if len(rows) > max_rows:
                    L.append(f"- … and {len(rows) - max_rows} more")
    errs = [f for f in r["findings"] if f["severity"] == "error"]
    if errs:
        L += ["", "## MUST failures", ""]
        L += [
            f"- {f['collection'] or '-'} · {_short(f.get('asset_href'))} · {f['tool']} `{f['rule_id']}`"
            + (f" ({f['spec_requirement_id']})" if f.get("spec_requirement_id") else "")
            + f": {f['message']}"
            for f in errs[:max_rows]
        ]
        if len(errs) > max_rows:
            L.append(f"- … and {len(errs) - max_rows} more (see report.json)")
    L += ["", "## Coverage", ""]
    if r["coverage"]:
        seen = set()
        for c in r["coverage"]:
            key = (c["tool"], c["reason"])
            if key in seen:
                continue
            seen.add(key)
            L.append(f"- {c['tool']}: {c['reason']}")
    else:
        L.append("Every check ran.")
    L += ["", "## Tool versions", "", "| Tool | Version |", "|---|---|"]
    L += [f"| {k} | {v or 'not installed'} |" for k, v in r["tool_versions"].items()]
    return "\n".join(L) + "\n"


def _short(href: str | None) -> str:
    return "-" if not href else href.rsplit("/", 1)[-1]
