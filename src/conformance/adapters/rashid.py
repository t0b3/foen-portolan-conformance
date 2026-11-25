"""rashid: the Portolan catalog validator (primary check).

`rashid check <catalog-url> --json --all [--schema] [--live] [--no-data]`
Exit code 0: no MUST broken. 1: at least one MUST broken. Anything else is a tool error.
"""

from __future__ import annotations

from collections import defaultdict

from .. import repro
from ..normalize import extract_spec_id, map_severity
from ..toolchain import RunResult, run, supports
from .base import Adapter, Context, parse_json_loose, worst

COVERAGE_CODES = {
    # Remote crawl: rules needing a directory listing (PTL-LNK-002, PTL-COL-005) do not run.
    "PTL-GEN-002": "Remote crawl: rashid reads only linked documents, so checks that need a "
    "directory listing (e.g. PTL-LNK-002 orphan objects, PTL-COL-005) did not run.",
}


class Rashid(Adapter):
    name = "rashid"
    key = "rashid"
    binary = "rashid"
    layer = "Portolan catalog"
    light = True
    install = "uv tool install rashid"

    def example_cmd(self, url):
        return ["rashid", "check", url, "--json", "--all"]

    def build_cmd(self, ctx: Context) -> list[str]:
        cmd = [self.binary, "check", ctx.crawl.root_url]
        for flag in ("--json", "--all", "--schema"):
            if supports(self.binary, flag, "check"):
                cmd.append(flag)
        if ctx.mode == "light":
            if supports(self.binary, "--no-data", "check"):
                cmd.append("--no-data")
        elif supports(self.binary, "--live", "check"):
            # Live hosting checks (range + CORS) already run by default for URLs; pass the flag
            # explicitly so a future change of default does not silently drop them.
            cmd.append("--live")
        return cmd

    def jobs(self, ctx: Context):
        return [lambda: self.check(ctx)]

    def check(self, ctx: Context):
        cmd = self.build_cmd(ctx)
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        if r.returncode not in (0, 1):
            return self.record(
                ctx,
                "rashid check",
                [self.tool_error(ctx, r, ctx.crawl.root_url)],
                command=self.tool_cmd(cmd),
                target=ctx.crawl.root_url,
                evidence=f"exit code {r.returncode}",
            )
        out = self.parse(ctx, r.stdout, r.returncode, cmd)
        if ctx.mode == "full" and not any(f.rule_id == "tool-error" for f in out):
            # rashid's data pass reads asset bytes (formats, sizes, checksums, extents).
            for a in ctx.crawl.assets:
                if not ctx.too_big(a):
                    ctx.verified.setdefault(a.href, set()).add(self.name)
        return out

    def parse(self, ctx: Context, stdout: str, returncode: int, cmd: list[str] | None = None):
        cmd = cmd or [self.binary, "check", ctx.crawl.root_url, "--json", "--all"]
        base = self.tool_cmd(cmd)
        root = ctx.crawl.root_url
        parent = self.make_check(ctx, "rashid check", command=base, target=root).id
        doc = parse_json_loose(stdout)
        if doc is None:
            err = self.tool_error(
                ctx, RunResult(cmd, returncode, stdout, "no JSON on stdout"), root
            )
            return self.record(
                ctx,
                "rashid check",
                [err],
                command=base,
                target=root,
                evidence=f"exit code {returncode}, no JSON",
            )
        raw = doc.get("findings", []) if isinstance(doc, dict) else doc
        groups = defaultdict(list)  # rule -> findings (one child check per rule)
        rule_key = "rule"
        for f in raw or []:
            rule_key = next((k for k in ("rule", "rule_id", "code", "id") if f.get(k)), rule_key)
            rule = str(f.get(rule_key) or "PTL-UNKNOWN")
            msg = str(_first(f, "message", "msg", "detail") or "")
            where = _first(f, "path", "file", "href", "url", "location", "object")
            spec = extract_spec_id(
                _first(f, "requirement", "requirement_id", "spec_id", "spec"),
                msg,
                f.get("references"),
            )
            col, item, href = ctx.locate(where if isinstance(where, str) else None)
            if rule in COVERAGE_CODES:
                groups[rule].append(
                    self.finding(
                        ctx,
                        "coverage-limit",
                        "info",
                        COVERAGE_CODES[rule] + f" ({rule})",
                        collection=col,
                        item=item,
                        upstream_rule=rule,
                    )
                )
                continue
            asset = next((a for a in ctx.crawl.assets if a.href == href), None)
            groups[rule].append(
                self.finding(
                    ctx,
                    rule,
                    map_severity(_first(f, "severity", "level")),
                    msg,
                    collection=col,
                    item=item,
                    asset_href=href,
                    fmt=ctx.fmt(asset) if asset else None,
                    spec_id=spec,
                    location=where if isinstance(where, str) else None,
                )
            )
        out = []
        for rule in sorted(groups):
            jq = ".findings[] | select(." + rule_key + ' == "' + rule + '")'
            cmd_rule = f"{base} | jq {repro.q(jq)}"
            out += self.record(
                ctx,
                rule,
                groups[rule],
                command=cmd_rule,
                target=root,
                parent=parent,
                evidence=f"{len(groups[rule])} finding(s)",
            )
        if returncode == 1 and not any(x.severity == "error" for x in out):
            out += self.record(
                ctx,
                "exit code",
                [
                    self.finding(
                        ctx,
                        "PTL-EXIT-1",
                        "error",
                        "rashid reported at least one broken MUST requirement (exit code 1) but listed no error finding.",
                    )
                ],
                command=f"{base}; echo exit=$?",
                target=root,
                parent=parent,
            )
        self.record(
            ctx,
            "rashid check",
            [],
            command=base,
            target=root,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent] or ["pass"]),
            evidence=f"exit code {returncode}; {len(raw or [])} finding(s) in {len(groups)} rule(s)",
        )
        return out


def _first(d: dict, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None
