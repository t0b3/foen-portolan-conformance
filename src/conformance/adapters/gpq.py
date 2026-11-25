"""gpq (`gpq validate`): optional GeoParquet cross-check. Findings are capped at warning so a
disagreement between gpq and gpio never flips an asset to MUST-failing on gpq's word alone."""

from __future__ import annotations

from ..toolchain import run, supports
from .base import Adapter, Context, parse_json_loose, text_checks, walk_checks


class Gpq(Adapter):
    name = "gpq"
    key = "gpq"
    binary = "gpq"
    layer = "GeoParquet (cross-check)"

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("geoparquet",), lambda a: self.check(ctx, a))

    def check(self, ctx: Context, asset):
        cmd = [self.binary, "validate", asset.href]
        if supports(self.binary, "--format", "validate"):
            cmd += ["--format", "json"]
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        doc = parse_json_loose(r.stdout)
        if doc is None and r.returncode not in (0, 1):
            return [self.tool_error(ctx, r, asset.href, asset=asset)]
        items = (
            [(n, m or n) for n, s, m in walk_checks(doc) if s == "fail"]
            if doc is not None
            else [(line, line) for s, line in text_checks(r.stdout + r.stderr) if s == "fail"]
        )
        return [
            self.finding(
                ctx, "gpq:validate", "warning", msg, asset=asset, fmt="geoparquet", check=name
            )
            for name, msg in items
        ]
