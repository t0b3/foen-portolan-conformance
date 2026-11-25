"""Generate small binary fixtures. Pure-Python for PMTiles and the mini catalog; GeoParquet
needs pyarrow and COG needs GDAL (`gdal_translate`) - those are skipped when missing.

    python tests/fixtures/generate.py OUT_DIR
"""

from __future__ import annotations

import gzip
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def pmtiles(
    path: Path, *, clustered: bool = True, bounds=(6.0, 46.0, 10.0, 48.0), bad_magic=False
) -> None:
    """A one-tile PMTiles v3 archive (tile 0/0/0, MVT, gzip)."""
    tile = gzip.compress(b"\x1a\x00", mtime=0)  # minimal (empty layer list) MVT, gzipped
    # Directory: 1 entry; tile_id delta=0, run_length=1, length, offset+1 encoding (0 means
    # "consecutive"; first entry must store offset+1).
    d = _varint(1) + _varint(0) + _varint(1) + _varint(len(tile)) + _varint(0 + 1)
    root = gzip.compress(d, mtime=0)
    meta = gzip.compress(json.dumps({"vector_layers": []}).encode(), mtime=0)
    root_off = 127
    meta_off = root_off + len(root)
    leaf_off = meta_off + len(meta)
    data_off = leaf_off
    hdr = bytearray(b"PMTiles" if not bad_magic else b"NOTTILE")
    hdr.append(3)
    hdr += struct.pack(
        "<11Q", root_off, len(root), meta_off, len(meta), leaf_off, 0, data_off, len(tile), 1, 1, 1
    )
    hdr += bytes(
        [1 if clustered else 0, 2, 2, 1, 0, 0]
    )  # clustered, int comp, tile comp, mvt, minz, maxz
    e7 = [round(x * 1e7) for x in bounds]
    hdr += struct.pack("<4i", *e7)
    hdr += bytes([0]) + struct.pack(
        "<2i", round((bounds[0] + bounds[2]) / 2 * 1e7), round((bounds[1] + bounds[3]) / 2 * 1e7)
    )
    assert len(hdr) == 127, len(hdr)
    path.write_bytes(bytes(hdr) + root + meta + tile)


def geoparquet(path: Path, valid: bool = True) -> bool:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        return False
    # Two WKB points.
    pts = [struct.pack("<BIdd", 1, 1, 7.4, 46.9), struct.pack("<BIdd", 1, 1, 8.5, 47.4)]
    t = pa.table({"id": [1, 2], "geometry": pa.array(pts, pa.binary())})
    if valid:
        geo = {
            "version": "1.1.0",
            "primary_column": "geometry",
            "columns": {
                "geometry": {
                    "encoding": "WKB",
                    "geometry_types": ["Point"],
                    "bbox": [7.4, 46.9, 8.5, 47.4],
                }
            },
        }
        t = t.replace_schema_metadata({b"geo": json.dumps(geo).encode()})
        pq.write_table(t, path, compression="zstd")
    else:
        # No "geo" metadata and the geometry column named in it does not exist.
        geo = {
            "version": "1.1.0",
            "primary_column": "geom",
            "columns": {"geom": {"encoding": "WKT"}},
        }
        t = t.replace_schema_metadata({b"geo": json.dumps(geo).encode()})
        pq.write_table(t, path, compression="snappy")
    return True


def cog(path: Path, valid: bool = True) -> bool:
    if not shutil.which("gdal_translate"):
        return False
    src = path.with_suffix(".src.tif")
    subprocess.run(
        [
            "gdal_translate",
            "-q",
            "-of",
            "GTiff",
            "-outsize",
            "1024",
            "1024",
            "-a_srs",
            "EPSG:2056",
            "-a_ullr",
            "2600000",
            "1200000",
            "2601024",
            "1198976",
            "/vsimem/none",
            str(src),
        ],
        check=False,
        capture_output=True,
    )
    if not src.exists():
        # Build a source raster from scratch with gdal_create (GDAL >= 3.2).
        subprocess.run(
            [
                "gdal_create",
                "-q",
                "-of",
                "GTiff",
                "-outsize",
                "1024",
                "1024",
                "-bands",
                "1",
                "-burn",
                "7",
                "-a_srs",
                "EPSG:2056",
                "-a_ullr",
                "2600000",
                "1200000",
                "2601024",
                "1198976",
                str(src),
            ],
            check=True,
            capture_output=True,
        )
    if valid:
        subprocess.run(
            ["gdal_translate", "-q", "-of", "COG", "-co", "COMPRESS=DEFLATE", str(src), str(path)],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            ["gdal_translate", "-q", "-of", "GTiff", "-co", "TILED=NO", str(src), str(path)],
            check=True,
            capture_output=True,
        )
    src.unlink(missing_ok=True)
    return True


def mini_catalog(out: Path) -> dict:
    """Copy tests/fixtures/mini to `out` and fill in binary assets. Returns what was generated."""
    shutil.copytree(HERE / "mini", out, dirs_exist_ok=True)
    made = {}
    pmtiles(out / "tiles" / "good.pmtiles")
    pmtiles(out / "tiles" / "bad.pmtiles", clustered=False, bounds=(20.0, 50.0, 21.0, 51.0))
    made["pmtiles"] = True
    (out / "vector" / "legacy.gpkg").write_bytes(b"SQLite format 3\x00" + b"\x00" * 84)
    made["geoparquet"] = geoparquet(out / "vector" / "good.parquet", True) and geoparquet(
        out / "vector" / "bad.parquet", False
    )
    if not made["geoparquet"]:
        # Magic bytes only: enough for format detection tests.
        for n in ("good.parquet", "bad.parquet"):
            (out / "vector" / n).write_bytes(b"PAR1" + b"\x00" * 60 + b"PAR1")
    made["cog"] = cog(out / "raster" / "items" / "good.tif", True) and cog(
        out / "raster" / "items" / "bad.tif", False
    )
    if not made["cog"]:
        for n in ("good.tif", "bad.tif"):
            (out / "raster" / "items" / n).write_bytes(b"II*\x00" + b"\x00" * 60)
    return made


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "build/fixtures")
    print(json.dumps(mini_catalog(target)))
