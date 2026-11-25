"""Zarr (incubating in the Portolan spec): consolidated-metadata check over HTTP.

Reads only small metadata documents: `zarr.json` (v3, consolidated metadata inline) or
`.zmetadata` (v2 consolidated). No zarr/xarray install needed.
"""

from __future__ import annotations

import json

from .. import repro
from .base import Adapter, Context

INCUBATING = "Zarr is incubating in the Portolan spec; findings are advisory."


class Zarr(Adapter):
    name = "zarr-probe"
    key = "zarr"
    binary = None
    layer = "Zarr (incubating)"
    scope = "asset"
    formats = ("zarr",)

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("zarr",), lambda a: self.check(ctx, a), header_only=True)

    def check(self, ctx: Context, asset):
        base = asset.href.rstrip("/")
        cmd = repro.lines(
            "# Zarr v3 (consolidated metadata inline):",
            repro.json_query(base + "/zarr.json", "."),
            "# Zarr v2 consolidated:",
            repro.json_query(base + "/.zmetadata", ".metadata | keys"),
        )
        return self.record(
            ctx, "Zarr consolidated metadata", self._check(ctx, asset), command=cmd, asset=asset
        )

    def _check(self, ctx: Context, asset):
        base = asset.href.rstrip("/")
        f = lambda rule, sev, msg: self.finding(
            ctx, rule, sev, msg, asset=asset, fmt="zarr", note=INCUBATING
        )
        out = [f("ZARR-000", "info", INCUBATING)]
        v3 = ctx.fetcher.get(base + "/zarr.json")
        if v3.ok:
            try:
                meta = json.loads(v3.body)
            except ValueError:
                return [*out, f("ZARR-002", "error", "zarr.json is not valid JSON")]
            if meta.get("node_type") == "group" and not meta.get("consolidated_metadata"):
                out.append(f("ZARR-003", "warning", "Zarr v3 group without consolidated metadata"))
            return out
        v2 = ctx.fetcher.get(base + "/.zmetadata")
        if v2.ok:
            return out
        if ctx.fetcher.get(base + "/.zgroup").ok or ctx.fetcher.get(base + "/.zarray").ok:
            return [*out, f("ZARR-003", "warning", "Zarr v2 store without consolidated .zmetadata")]
        return [*out, f("ZARR-001", "error", "No zarr.json, .zmetadata, .zgroup or .zarray found")]
