"""gpq (`gpq validate`): optional GeoParquet cross-check. Findings are capped at warning so a
disagreement between gpq and gpio never flips an asset to MUST-failing on gpq's word alone."""

from __future__ import annotations

from ..toolchain import run, supports
from .base import Adapter, Context, parse_json_loose, text_checks, walk_checks, worst


class Gpq(Adapter):
    name = "gpq"
    key = "gpq"
    binary = "gpq"
    layer = "GeoParquet (cross-check)"
    scope = "asset"
    formats = ("geoparquet",)
    install = "download from https://github.com/planetlabs/gpq/releases"

    def example_cmd(self, url):
        return ["gpq", "validate", url]

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("geoparquet",), lambda a: self.check(ctx, a))

    def check(self, ctx: Context, asset):
        cmd = [self.binary, "validate", asset.href]
        if supports(self.binary, "--format", "validate"):
            cmd += ["--format", "json"]
        command = self.tool_cmd(cmd)
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        doc = parse_json_loose(r.stdout)
        if doc is None and r.returncode not in (0, 1):
            return self.record(
                ctx,
                "gpq validate",
                [self.tool_error(ctx, r, asset.href, asset=asset)],
                command=command,
                asset=asset,
                evidence=f"exit code {r.returncode}",
            )
        parent = self.make_check(ctx, "gpq validate", command=command, asset=asset).id
        items = (
            list(walk_checks(doc))
            if doc is not None
            else [(line, s, line) for s, line in text_checks(r.stdout + r.stderr)]
        )
        out = []
        for name, status, msg in items:
            fs = (
                [
                    self.finding(
                        ctx,
                        "gpq:validate",
                        "warning",
                        msg or name,
                        asset=asset,
                        fmt="geoparquet",
                        check=name,
                    )
                ]
                if status == "fail"
                else []
            )
            out += self.record(
                ctx,
                name,
                fs,
                command=command,
                asset=asset,
                parent=parent,
                outcome="warn" if status == "fail" else "pass" if status == "pass" else "info",
                evidence=msg or status,
            )
        self.record(
            ctx,
            "gpq validate",
            [],
            command=command,
            asset=asset,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
            evidence=f"exit code {r.returncode}; {len(items)} check(s) reported",
        )
        return out
