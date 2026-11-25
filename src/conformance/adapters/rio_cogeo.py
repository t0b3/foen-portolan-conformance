"""rio-cogeo (`rio cogeo validate --strict`): COG tiling, overviews, IFD order, compression.

Runs on assets typed as COG and on plain GeoTIFFs (a GeoTIFF that validates is a COG whose
media type lacks `profile=cloud-optimized`). GDAL reads https URLs through /vsicurl/ with
range requests, so the file is not downloaded.
"""

from __future__ import annotations

import re

from ..toolchain import run, supports
from .base import Adapter, Context


class RioCogeo(Adapter):
    name = "rio-cogeo"
    key = "rio_cogeo"
    binary = "rio"
    layer = "COG"
    scope = "asset"
    formats = ("cog", "geotiff")
    install = "uv tool install rasterio --with rio-cogeo"

    def example_cmd(self, url):
        return ["rio", "cogeo", "validate", url, "--strict"]

    def version(self):
        from ..toolchain import version

        return version(self.binary, "cogeo")

    def available(self) -> bool:
        from ..toolchain import help_text, which

        return which(self.binary) is not None and "validate" in help_text(self.binary, "cogeo")

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("cog", "geotiff"), lambda a: self.check(ctx, a))

    def check(self, ctx: Context, asset):
        cmd = [self.binary, "cogeo", "validate", asset.href]
        if supports(self.binary, "--strict", "cogeo", "validate"):
            cmd.append("--strict")
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        text = r.stdout + "\n" + r.stderr
        if r.returncode not in (0, 1) and "cloud optimized" not in text.lower():
            return self.record(
                ctx,
                "rio cogeo validate",
                [self.tool_error(ctx, r, asset.href, asset=asset)],
                command=self.tool_cmd(cmd),
                asset=asset,
                evidence=f"exit code {r.returncode}",
            )
        return self.parse(ctx, asset, text, r.returncode, cmd)

    def parse(self, ctx: Context, asset, text: str, rc: int, cmd: list[str] | None = None):
        cmd = cmd or [self.binary, "cogeo", "validate", asset.href, "--strict"]
        out = self._parse(ctx, asset, text, rc)
        valid = not any(f.severity == "error" for f in out if f.rule_id.startswith("rio-cogeo"))
        return self.record(
            ctx,
            "rio cogeo validate",
            out,
            command=self.tool_cmd(cmd),
            asset=asset,
            evidence=f"exit code {rc}; {'valid' if valid else 'NOT a valid'} COG",
        )

    def _parse(self, ctx: Context, asset, text: str, rc: int):
        out = []
        declared = ctx.fmt(asset)
        valid = rc == 0 and re.search(r"is a valid cloud optimized geotiff", text, re.I) is not None
        section = None
        for line in text.splitlines():
            low = line.strip().lower()
            if "following errors" in low:
                section = "error"
            elif "following warnings" in low:
                section = "warning"
            elif section and line.strip().startswith("-"):
                out.append(
                    self.finding(
                        ctx,
                        f"rio-cogeo:{section}",
                        section,
                        line.strip(" -"),
                        asset=asset,
                        fmt="cog",
                    )
                )
        if not valid and not any(f.severity == "error" for f in out):
            out.append(
                self.finding(
                    ctx,
                    "rio-cogeo:invalid",
                    "error",
                    "File is NOT a valid cloud optimized GeoTIFF",
                    asset=asset,
                    fmt="cog",
                )
            )
        if valid and declared == "geotiff":
            out.append(
                self.finding(
                    ctx,
                    "CNC-FMT-005",
                    "warning",
                    "Valid COG, but the STAC asset type lacks "
                    "'; application=geotiff; profile=cloud-optimized'",
                    asset=asset,
                    fmt="cog",
                )
            )
            ctx.formats[asset.href] = ("cog", "validator")
        if not valid and declared == "geotiff":
            out.append(
                self.finding(
                    ctx,
                    "CNC-FMT-001",
                    ctx.config.checks["non_cloud_native_severity"],
                    "non-cloud-native asset: plain GeoTIFF (not a valid COG)",
                    asset=asset,
                    fmt="geotiff",
                )
            )
        return out
