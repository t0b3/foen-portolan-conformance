"""Cloud-native classification: every scored asset must be a Portolan cloud-native format."""

from __future__ import annotations

from .. import repro
from ..formats import CLOUD_NATIVE, INCUBATING, from_extension, from_magic, from_media_type
from .base import Adapter, Context, worst

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
        return [
            (lambda a=a: self.check_asset(ctx, a))
            for a in ctx.crawl.assets
            if not ctx.is_ancillary(a)
        ]

    def check(self, ctx: Context):
        """All assets at once (kept for callers that want a flat list)."""
        return [
            f for a in ctx.crawl.assets if not ctx.is_ancillary(a) for f in self.check_asset(ctx, a)
        ]

    def check_asset(self, ctx: Context, a):
        sev = ctx.config.checks.get("non_cloud_native_severity", "warning")
        rio_will_decide = ctx.mode == "full" and ctx.config.tool_enabled("rio_cogeo") and _rio()
        fmt, how = ctx.formats.get(a.href, ("unknown", "unknown"))
        p = ctx.probes.get(a.href)
        declared = from_media_type(a.media_type)
        magic = from_magic(p.first_bytes) if p and p.first_bytes else None
        detect_cmd = repro.lines(
            "# STAC asset entry (type, roles):",
            repro.stac_asset(a.owner_url, a.key),
            "# first bytes on the wire (magic number):",
            repro.first_bytes(a.href, 16),
        )
        evidence = (
            f"type={a.media_type or '-'}; extension={from_extension(a.href) or '-'}; "
            f"magic={magic or ('not read' if not p else '-')}; detected={fmt} (by {how})"
        )
        parent = self.make_check(ctx, "format classification", command=detect_cmd, asset=a).id
        out = []

        def sub(name, findings, ev, outcome=None):
            return self.record(
                ctx,
                name,
                findings,
                command=detect_cmd,
                asset=a,
                parent=parent,
                evidence=ev,
                outcome=outcome,
            )

        f = lambda rule, severity, msg, **d: self.finding(ctx, rule, severity, msg, asset=a, **d)
        if fmt in CLOUD_NATIVE:
            out += sub("is a Portolan cloud-native format", [], evidence)
        elif fmt in INCUBATING:
            out += sub(
                "is a Portolan cloud-native format",
                [f("CNC-FMT-004", "info", f"{fmt.upper()} is incubating in the Portolan spec")],
                evidence,
            )
        elif fmt == "geotiff":
            if rio_will_decide:
                out += sub(
                    "is a Portolan cloud-native format",
                    [],
                    evidence + "; COG status decided by rio-cogeo",
                    outcome="info",
                )
            else:
                out += sub(
                    "is a Portolan cloud-native format",
                    [
                        f(
                            "CNC-FMT-006",
                            "warning",
                            "GeoTIFF not typed as COG; COG status not verified (rio-cogeo not run)",
                        )
                    ],
                    evidence,
                )
        elif fmt == "unknown":
            out += sub(
                "format detectable",
                [
                    f(
                        "CNC-FMT-002",
                        "warning",
                        "Format could not be detected from type, extension or magic bytes",
                    )
                ],
                evidence,
            )
        else:
            out += sub(
                "is a Portolan cloud-native format",
                [
                    f(
                        "CNC-FMT-001",
                        sev,
                        f"non-cloud-native asset: {LABEL.get(fmt, fmt)} ({a.media_type or 'no type'})",
                        detected_by=how,
                    )
                ],
                evidence,
            )
        # Declared type vs bytes on the wire.
        if declared and magic:
            mismatch = declared != magic and not {declared, magic} <= {"geotiff", "cog"}
            out += sub(
                "STAC type matches file content",
                [
                    f(
                        "CNC-FMT-003",
                        "warning",
                        f"STAC type says {declared} but the file starts like {magic}",
                    )
                ]
                if mismatch
                else [],
                f"type says {declared}; bytes look like {magic}",
            )
        if fmt == "geoparquet" and a.media_type:
            ok = "vnd.apache.parquet" in a.media_type
            out += sub(
                "registered Parquet media type",
                []
                if ok
                else [
                    f(
                        "CNC-FMT-007",
                        "info",
                        f"Parquet asset typed '{a.media_type}'; the registered media type "
                        "is 'application/vnd.apache.parquet'",
                    )
                ],
                f"type={a.media_type}",
            )
        self.record(
            ctx,
            "format classification",
            [],
            command=detect_cmd,
            asset=a,
            evidence=evidence,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
        )
        return out


def _rio() -> bool:
    from ..toolchain import which

    return which("rio") is not None
