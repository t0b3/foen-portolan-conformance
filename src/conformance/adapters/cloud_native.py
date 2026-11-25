"""Cloud-native classification: every scored asset must be a Portolan cloud-native format."""

from __future__ import annotations

from ..formats import CLOUD_NATIVE, INCUBATING, from_magic, from_media_type
from .base import Adapter, Context

LABEL = {
    "geopackage": "GeoPackage",
    "shapefile": "Shapefile",
    "geojson": "GeoJSON",
    "csv": "CSV",
    "geotiff": "GeoTIFF",
    "zip": "ZIP archive",
    "flatgeobuf": "FlatGeobuf",
    "las": "LAS",
    "laz": "LAZ (not COPC)",
    "unknown": "unknown format",
}


class CloudNative(Adapter):
    name = "cloud-native-classifier"
    key = "cloud_native"
    binary = None
    layer = "Formats"
    light = True

    def jobs(self, ctx: Context):
        return [lambda: self.check(ctx)]

    def check(self, ctx: Context):
        out = []
        sev = ctx.config.checks.get("non_cloud_native_severity", "warning")
        rio_will_decide = ctx.mode == "full" and ctx.config.tool_enabled("rio_cogeo") and _rio()
        for a in ctx.crawl.assets:
            if ctx.is_ancillary(a):
                continue
            fmt, how = ctx.formats.get(a.href, ("unknown", "unknown"))
            if fmt in CLOUD_NATIVE:
                pass
            elif fmt in INCUBATING:
                out.append(
                    self.finding(
                        ctx,
                        "CNC-FMT-004",
                        "info",
                        f"{fmt.upper()} is incubating in the Portolan spec",
                        asset=a,
                    )
                )
            elif fmt == "geotiff":
                if not rio_will_decide:
                    out.append(
                        self.finding(
                            ctx,
                            "CNC-FMT-006",
                            "warning",
                            "GeoTIFF not typed as COG; COG status not verified (rio-cogeo not run)",
                            asset=a,
                        )
                    )
            elif fmt == "unknown":
                out.append(
                    self.finding(
                        ctx,
                        "CNC-FMT-002",
                        "warning",
                        "Format could not be detected from type, extension or magic bytes",
                        asset=a,
                    )
                )
            else:
                out.append(
                    self.finding(
                        ctx,
                        "CNC-FMT-001",
                        sev,
                        f"non-cloud-native asset: {LABEL.get(fmt, fmt)} ({a.media_type or 'no type'})",
                        asset=a,
                        detected_by=how,
                    )
                )
            # Declared type vs bytes on the wire.
            p = ctx.probes.get(a.href)
            declared = from_media_type(a.media_type)
            magic = from_magic(p.first_bytes) if p else None
            if (
                declared
                and magic
                and declared != magic
                and not {declared, magic} <= {"geotiff", "cog"}
            ):
                out.append(
                    self.finding(
                        ctx,
                        "CNC-FMT-003",
                        "warning",
                        f"STAC type says {declared} but the file starts like {magic}",
                        asset=a,
                    )
                )
            if fmt == "geoparquet" and a.media_type and "vnd.apache.parquet" not in a.media_type:
                out.append(
                    self.finding(
                        ctx,
                        "CNC-FMT-007",
                        "info",
                        f"Parquet asset typed '{a.media_type}'; the registered media type "
                        "is 'application/vnd.apache.parquet'",
                        asset=a,
                    )
                )
        return out


def _rio() -> bool:
    from ..toolchain import which

    return which("rio") is not None
