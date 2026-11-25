"""rashid: the Portolan catalog validator (primary check).

`rashid check <catalog-url> --json --all [--schema] [--live] [--no-data]`
Exit code 0: no MUST broken. 1: at least one MUST broken. Anything else is a tool error.
"""

from __future__ import annotations

from ..normalize import extract_spec_id, map_severity
from ..toolchain import run, supports
from .base import Adapter, Context, parse_json_loose

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

    def build_cmd(self, ctx: Context) -> list[str]:
        url = ctx.crawl.root_url
        cmd = [self.binary, "check", url]
        for flag in ("--json", "--all"):
            if supports(self.binary, flag, "check"):
                cmd.append(flag)
        if supports(self.binary, "--schema", "check"):
            cmd.append("--schema")
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
            return [self.tool_error(ctx, r, ctx.crawl.root_url)]
        out = self.parse(ctx, r.stdout, r.returncode, cmd)
        if ctx.mode == "full" and not any(f.rule_id == "tool-error" for f in out):
            # rashid's data pass reads asset bytes (formats, sizes, checksums, extents).
            for a in ctx.crawl.assets:
                if not ctx.too_big(a):
                    ctx.verified.setdefault(a.href, set()).add(self.name)
        return out

    def parse(self, ctx: Context, stdout: str, returncode: int, cmd: list[str] | None = None):
        doc = parse_json_loose(stdout)
        if doc is None:
            from ..toolchain import RunResult

            return [
                self.tool_error(
                    ctx,
                    RunResult(cmd or [], returncode, stdout, "no JSON on stdout"),
                    ctx.crawl.root_url,
                )
            ]
        raw = doc.get("findings", []) if isinstance(doc, dict) else doc
        out = []
        for f in raw or []:
            rule = str(_first(f, "rule", "rule_id", "code", "id") or "PTL-UNKNOWN")
            msg = str(_first(f, "message", "msg", "detail") or "")
            where = _first(f, "path", "file", "href", "url", "location", "object")
            spec = _first(f, "requirement", "requirement_id", "spec_id", "spec") or None
            spec = extract_spec_id(spec, msg, f.get("references"))
            col, item, href = ctx.locate(where if isinstance(where, str) else None)
            if rule in COVERAGE_CODES:
                out.append(
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
            sev = map_severity(_first(f, "severity", "level"))
            fmt = (
                ctx.fmt(next(a for a in ctx.crawl.assets if a.href == href))
                if href and any(a.href == href for a in ctx.crawl.assets)
                else None
            )
            out.append(
                self.finding(
                    ctx,
                    rule,
                    sev,
                    msg,
                    collection=col,
                    item=item,
                    asset_href=href,
                    fmt=fmt,
                    spec_id=spec,
                    location=where if isinstance(where, str) else None,
                )
            )
        if returncode == 1 and not any(x.severity == "error" for x in out):
            out.append(
                self.finding(
                    ctx,
                    "PTL-EXIT-1",
                    "error",
                    "rashid reported at least one broken MUST requirement (exit code 1) "
                    "but listed no error finding.",
                )
            )
        return out


def _first(d: dict, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None
