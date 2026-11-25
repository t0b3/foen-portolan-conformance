"""geoparquet-io (`gpio`): GeoParquet spec validity and best practices.

`gpio check spec <url>`  - spec validity (1.0 / 1.1 / 2.0 auto-detected)
`gpio check all <url>`   - bbox covering, spatial ordering, ZSTD, row groups, ...
Exit codes: 0 pass, 1 failed check, 2 warnings only (older releases; current docs say warnings
exit 0). JSON is used when the subcommand advertises --json, otherwise ✓/✗/⚠ text is parsed.
"""

from __future__ import annotations

from ..toolchain import run, supports
from .base import Adapter, Context, parse_json_loose, sev_from_status, text_checks, walk_checks


class Gpio(Adapter):
    name = "gpio"
    key = "gpio"
    binary = "gpio"
    layer = "GeoParquet"

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("geoparquet",), lambda a: self.check(ctx, a))

    def check(self, ctx: Context, asset):
        out = []
        for sub in ("spec", "all"):
            cmd = [self.binary, "check", sub, asset.href]
            use_json = supports(self.binary, "--json", "check", sub)
            if use_json:
                cmd.append("--json")
            r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
            if r.returncode not in (0, 1, 2):
                out.append(self.tool_error(ctx, r, asset.href, asset=asset))
                continue
            out += self.parse(ctx, asset, sub, r.stdout, r.returncode, use_json)
        return out

    def parse(self, ctx: Context, asset, sub: str, stdout: str, rc: int, use_json: bool):
        out = []
        doc = parse_json_loose(stdout) if use_json else None
        if doc is not None:
            items = [(n, s, m) for n, s, m in walk_checks(doc) if s in ("fail", "warn")]
        else:
            items = [(line.split(":")[0][:60], s, line) for s, line in text_checks(stdout)]
        for name, status, msg in items:
            out.append(
                self.finding(
                    ctx,
                    f"gpio:{sub}:{_slug(name)}",
                    sev_from_status(status),
                    msg or name,
                    asset=asset,
                    fmt="geoparquet",
                )
            )
        if rc == 1 and not any(f.severity == "error" for f in out):
            out.append(
                self.finding(
                    ctx,
                    f"gpio:{sub}:failed",
                    "error",
                    f"gpio check {sub} failed (exit 1)",
                    asset=asset,
                    fmt="geoparquet",
                )
            )
        if rc == 2 and not out:
            out.append(
                self.finding(
                    ctx,
                    f"gpio:{sub}:warnings",
                    "warning",
                    f"gpio check {sub} reported warnings (exit 2)",
                    asset=asset,
                    fmt="geoparquet",
                )
            )
        return out


def _slug(s: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "check"
