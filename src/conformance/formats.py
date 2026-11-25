"""Format detection: STAC asset `type` first, then file extension, then magic bytes."""

from __future__ import annotations

import struct
from pathlib import PurePosixPath
from urllib.parse import urlparse

# Portolan cloud-native formats. Zarr and COPC are incubating in the spec.
CLOUD_NATIVE = {"geoparquet", "cog", "pmtiles"}
INCUBATING = {"zarr", "copc"}
SCORED_FORMATS = CLOUD_NATIVE | INCUBATING

MEDIA_TYPES: list[tuple[str, str]] = [
    ("application/vnd.apache.parquet", "geoparquet"),
    ("application/x-parquet", "geoparquet"),
    ("application/parquet", "geoparquet"),
    ("profile=cloud-optimized", "cog"),
    ("image/tiff", "geotiff"),
    ("application/vnd.pmtiles", "pmtiles"),
    ("application/vnd+zarr", "zarr"),
    ("application/vnd.zarr", "zarr"),
    ("application/x-zarr", "zarr"),
    ("application/vnd.laszip+copc", "copc"),
    ("application/geopackage+sqlite3", "geopackage"),
    ("application/x-shapefile", "shapefile"),
    ("application/geo+json", "geojson"),
    ("text/csv", "csv"),
    ("application/flatgeobuf", "flatgeobuf"),
    ("application/vnd.flatgeobuf", "flatgeobuf"),
    ("application/vnd.las", "las"),
    ("application/vnd.laszip", "laz"),
    ("image/jpeg", "image"),
    ("image/png", "image"),
    ("image/webp", "image"),
    ("text/markdown", "document"),
    ("text/html", "document"),
    ("application/pdf", "document"),
    ("application/vnd.mapbox.style+json", "style"),
    ("application/json", "json"),
]

EXTENSIONS = {
    ".parquet": "geoparquet",
    ".geoparquet": "geoparquet",
    ".pmtiles": "pmtiles",
    ".zarr": "zarr",
    ".copc.laz": "copc",
    ".tif": "geotiff",
    ".tiff": "geotiff",
    ".gpkg": "geopackage",
    ".shp": "shapefile",
    ".zip": "zip",
    ".geojson": "geojson",
    ".csv": "csv",
    ".fgb": "flatgeobuf",
    ".las": "las",
    ".laz": "laz",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".md": "document",
    ".pdf": "document",
    ".json": "json",
}

ANCILLARY_FORMATS = {"image", "document", "style", "json"}


def from_media_type(media_type: str | None) -> str | None:
    if not media_type:
        return None
    mt = media_type.lower().replace(" ", "")
    # COG must be checked before plain GeoTIFF.
    if "image/tiff" in mt and "cloud-optimized" in mt:
        return "cog"
    for needle, fmt in MEDIA_TYPES:
        if needle in mt:
            return fmt
    return None


def from_extension(href: str) -> str | None:
    path = urlparse(href).path.lower().rstrip("/")
    if path.endswith(".copc.laz"):
        return "copc"
    return EXTENSIONS.get(PurePosixPath(path).suffix)


def from_magic(head: bytes) -> str | None:
    if len(head) < 4:
        return None
    if head[:4] == b"PAR1":
        return "geoparquet"
    if head[:7] == b"PMTiles":
        return "pmtiles"
    if head[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return "geotiff"  # COG vs plain GeoTIFF needs a validator
    if head[:16] == b"SQLite format 3\x00":
        return "geopackage"
    if head[:4] == b"LASF":
        # COPC: the first VLR (at offset 375) has user_id "copc".
        return "copc" if head[377:381] == b"copc" else "las"
    if head[:4] == b"PK\x03\x04":
        return "zip"
    if head[:3] == b"fgb":
        return "flatgeobuf"
    if head[:4] == b"\x00\x00\x27\x0a":
        return "shapefile"
    if head[:1] in (b"{", b"["):
        return "json"
    if head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    return None


def detect(href: str, media_type: str | None, head: bytes | None = None) -> tuple[str, str]:
    """Return (format, detected_by). detected_by is 'type' | 'extension' | 'magic' | 'unknown'."""
    fmt = from_media_type(media_type)
    if fmt and fmt not in {"json", "geotiff"}:
        return fmt, "type"
    ext = from_extension(href)
    if fmt == "geotiff" or (fmt is None and ext == "geotiff"):
        # A plain image/tiff type might still be a COG; the COG adapter decides.
        return "geotiff", "type" if fmt else "extension"
    if fmt == "json":
        return (ext or "json"), "type"
    if ext:
        return ext, "extension"
    if head:
        m = from_magic(head)
        if m:
            return m, "magic"
    return "unknown", "unknown"


def is_cloud_native(fmt: str) -> bool:
    return fmt in SCORED_FORMATS


def parse_pmtiles_header(b: bytes) -> dict | None:
    """Parse the fixed 127-byte PMTiles v3 header."""
    if len(b) < 127 or b[:7] != b"PMTiles":
        return None
    u64 = struct.unpack_from("<11Q", b, 8)
    names = [
        "root_offset",
        "root_length",
        "metadata_offset",
        "metadata_length",
        "leaf_offset",
        "leaf_length",
        "tile_data_offset",
        "tile_data_length",
        "addressed_tiles",
        "tile_entries",
        "tile_contents",
    ]
    h = dict(zip(names, u64, strict=True))
    h["spec_version"] = b[7]
    h["clustered"] = bool(b[96])
    h["internal_compression"] = b[97]
    h["tile_compression"] = b[98]
    h["tile_type"] = {0: "unknown", 1: "mvt", 2: "png", 3: "jpeg", 4: "webp", 5: "avif"}.get(
        b[99], str(b[99])
    )
    h["min_zoom"], h["max_zoom"] = b[100], b[101]
    mnlon, mnlat, mxlon, mxlat = struct.unpack_from("<4i", b, 102)
    h["bounds"] = [mnlon / 1e7, mnlat / 1e7, mxlon / 1e7, mxlat / 1e7]
    h["center_zoom"] = b[118]
    clon, clat = struct.unpack_from("<2i", b, 119)
    h["center"] = [clon / 1e7, clat / 1e7]
    return h
