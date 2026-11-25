from __future__ import annotations

from conformance.formats import detect, from_magic, parse_pmtiles_header
from conformance.normalize import Finding, extract_spec_id, map_severity, sort_findings

import generate


def test_detect_prefers_type_then_extension_then_magic():
    assert detect("x/data.bin", "application/vnd.apache.parquet") == ("geoparquet", "type")
    assert detect("x/data.parquet", None) == ("geoparquet", "extension")
    assert detect("x/data", None, b"PMTiles\x03") == ("pmtiles", "magic")
    assert detect("x/a.tif", "image/tiff; application=geotiff; profile=cloud-optimized") == (
        "cog",
        "type",
    )
    assert detect("x/a.tif", "image/tiff; application=geotiff")[0] == "geotiff"
    assert detect("x/a.gpkg", "application/geopackage+sqlite3") == ("geopackage", "type")
    assert detect("x/a.copc.laz", None) == ("copc", "extension")
    assert detect("x/blob", None, b"\x00\x01\x02\x03") == ("unknown", "unknown")


def test_magic_bytes():
    assert from_magic(b"PAR1....") == "geoparquet"
    assert from_magic(b"SQLite format 3\x00rest") == "geopackage"
    assert from_magic(b"II*\x00....") == "geotiff"
    copc = bytearray(b"LASF" + b"\x00" * 400)
    copc[377:381] = b"copc"
    assert from_magic(bytes(copc)) == "copc"
    assert from_magic(b"LASF" + b"\x00" * 400) == "las"


def test_pmtiles_header_roundtrip(tmp_path):
    p = tmp_path / "t.pmtiles"
    generate.pmtiles(p, clustered=False, bounds=(6.5, 46.1, 9.9, 47.7))
    h = parse_pmtiles_header(p.read_bytes()[:127])
    assert h["spec_version"] == 3 and h["clustered"] is False and h["tile_type"] == "mvt"
    assert [round(x, 4) for x in h["bounds"]] == [6.5, 46.1, 9.9, 47.7]
    assert parse_pmtiles_header(b"x" * 127) is None


def _f(**kw):
    base = dict(catalog_id="c", tool="t", rule_id="R-1", severity="error", message="m")
    return Finding(**(base | kw))


def test_fingerprint_ignores_tool_version_and_timings():
    a = _f(tool_version="1.0", message="took 1.2s to fail")
    b = _f(tool_version="2.0", message="took  3s to fail")
    assert a.fingerprint == b.fingerprint
    assert a.fingerprint != _f(rule_id="R-2").fingerprint


def test_sort_is_deterministic_and_dedupes():
    fs = [
        _f(collection="b"),
        _f(collection="a", severity="warning"),
        _f(collection="a"),
        _f(collection="b"),
    ]
    out = sort_findings(fs)
    assert [(f.collection, f.severity) for f in out] == [
        ("a", "error"),
        ("a", "warning"),
        ("b", "error"),
    ]
    assert sort_findings(list(reversed(fs))) == out


def test_severity_and_spec_ids():
    assert (
        map_severity("MUST") == "error"
        and map_severity("warn") == "warning"
        and map_severity("x") == "info"
    )
    assert extract_spec_id(None, "violates PORTO-FMT-012 (bbox)") == "PORTO-FMT-012"
    assert extract_spec_id("PORTO-ZARR-003") == "PORTO-ZARR-003"
    assert extract_spec_id("nothing") is None
