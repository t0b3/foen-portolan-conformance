"""COPC (incubating in the Portolan spec): native header check plus `pdal info` when installed."""

from __future__ import annotations

from .. import repro
from ..toolchain import run, which
from .base import Adapter, Context

INCUBATING = "COPC is incubating in the Portolan spec; findings are advisory."


class Copc(Adapter):
    name = "copc"
    key = "pdal"
    binary = None
    layer = "COPC (incubating)"
    scope = "asset"
    formats = ("copc",)

    def version(self):
        from .. import __version__
        from ..toolchain import version

        return f"pdal-{version('pdal')}" if which("pdal") else f"native-{__version__}"

    def jobs(self, ctx: Context):
        jobs = self.per_asset(ctx, ("copc",), lambda a: self._rec_header(ctx, a), header_only=True)
        if which("pdal"):
            jobs += self.per_asset(ctx, ("copc",), lambda a: self.pdal(ctx, a))
        return jobs

    def _rec_header(self, ctx: Context, asset):
        out = self.header(ctx, asset)
        if out is None:
            return None
        cmd = repro.lines(
            "# bytes 0-3 must be LASF, bytes 377-380 must be 'copc':",
            repro.first_bytes(asset.href, 589),
        )
        return self.record(ctx, "COPC header", out, command=cmd, asset=asset)

    def header(self, ctx: Context, asset):
        b = ctx.probes[asset.href].first_bytes if asset.href in ctx.probes else b""
        f = lambda rule, sev, msg: self.finding(
            ctx, rule, sev, msg, asset=asset, fmt="copc", note=INCUBATING
        )
        out = [f("COPC-000", "info", INCUBATING)]
        if not b:
            return None
        if b[:4] != b"LASF":
            return [*out, f("COPC-001", "error", "Not a LAS/LAZ file (missing LASF signature)")]
        if b[377:381] != b"copc":
            out.append(
                f(
                    "COPC-002",
                    "error",
                    "LAZ file without the COPC info VLR at offset 375 (not COPC)",
                )
            )
        return out

    def pdal(self, ctx: Context, asset):
        cmd = ["pdal", "info", "--summary", asset.href]
        r = run(
            cmd,
            timeout=float(ctx.config.limits["tool_timeout_s"]),
        )
        fs = []
        if r.returncode != 0:
            fs = [
                self.finding(
                    ctx,
                    "pdal:info",
                    "error",
                    "pdal info failed: " + ((r.stderr or "").strip().splitlines() or [""])[-1],
                    asset=asset,
                    fmt="copc",
                )
            ]
        return self.record(
            ctx,
            "pdal info",
            fs,
            command=repro.tool(cmd, None),
            asset=asset,
            evidence=f"exit code {r.returncode}",
        )
