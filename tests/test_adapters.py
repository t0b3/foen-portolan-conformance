"""Adapter parsers against recorded tool output (no tools needed)."""

from __future__ import annotations

import json

import pytest

from conformance.adapters import Context, Probe
from conformance.adapters.gpio import Gpio
from conformance.adapters.hosting import Hosting
from conformance.adapters.pmtiles import Pmtiles
from conformance.adapters.rashid import Rashid
from conformance.adapters.rio_cogeo import RioCogeo
from conformance.adapters.stac_check import StacCheck
from conformance.adapters.stac_validator import StacValidator
from conformance.config import CatalogConfig
from conformance.crawl import crawl
from conformance.formats import detect
from conformance.http import Response

from conftest import BAFU_ROOT


@pytest.fixture
def ctx(config, recorded_fetcher):
    cr = crawl(CatalogConfig(id="bafu", url=BAFU_ROOT), recorded_fetcher)
    c = Context(config=config, fetcher=recorded_fetcher, crawl=cr)
    for a in cr.assets:
        c.formats[a.href] = detect(a.href, a.media_type)
    return c


UB = "https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/"


def test_rashid_json(ctx):
    out = {
        "findings": [
            {
                "rule": "PTL-COL-001",
                "severity": "error",
                "message": "Collection lacks X (PORTO-CORE-017)",
                "path": "ub/collection.json",
            },
            {
                "rule": "PTL-FMT-010",
                "severity": "warning",
                "message": "not ZSTD",
                "path": "ub/UB.parquet",
                "requirement": "PORTO-FMT-005",
            },
            {
                "rule": "PTL-GEN-002",
                "severity": "info",
                "message": "remote crawl",
                "path": "catalog.json",
            },
        ],
        "summary": {"by_rule": {}},
    }
    fs = Rashid().parse(ctx, "banner\n" + json.dumps(out), 1)
    by = {f.rule_id: f for f in fs}
    assert by["PTL-COL-001"].severity == "error" and by["PTL-COL-001"].collection == "ub"
    assert by["PTL-COL-001"].spec_requirement_id == "PORTO-CORE-017"
    assert (
        by["PTL-FMT-010"].asset_href == UB + "UB.parquet"
        and by["PTL-FMT-010"].format == "geoparquet"
    )
    assert by["PTL-FMT-010"].spec_requirement_id == "PORTO-FMT-005"
    cov = by["coverage-limit"]
    assert cov.severity == "info" and "PTL-GEN-002" in cov.message


def test_rashid_exit1_without_errors_is_still_a_must_failure(ctx):
    fs = Rashid().parse(ctx, json.dumps({"findings": []}), 1)
    assert [f.severity for f in fs] == ["error"]


def test_stac_validator(ctx):
    obj = next(o for o in ctx.crawl.objects if o.id == "ub")
    fs = StacValidator().parse(
        ctx,
        obj,
        [
            {
                "path": obj.url,
                "valid_stac": False,
                "error_type": "JSONSchemaValidationError",
                "error_message": "'license' is a required property",
            }
        ],
    )
    assert fs[0].rule_id == "stac-validator:JSONSchemaValidationError" and fs[0].collection == "ub"
    assert StacValidator().parse(ctx, obj, [{"valid_stac": True}]) == []


def test_stac_check_text(ctx):
    obj = next(o for o in ctx.crawl.objects if o.id == "ub")
    text = """stac-check: STAC spec validation and linting tool
Valid COLLECTION: True
Schemas validated:
    https://schemas.stacspec.org/v1.1.0/collection-spec/json-schema/collection.json
STAC Best Practices:
    Object id: ub
    A STAC collection should contain a summaries field
    It is recommended to store information like eo:bands in summaries
"""
    fs = StacCheck().parse_text(ctx, obj, text)
    assert [f.severity for f in fs] == ["warning", "warning"]
    assert "summaries" in fs[0].message


def test_gpio_text_and_exit_codes(ctx):
    a = next(x for x in ctx.crawl.assets if x.href.endswith("UB.parquet"))
    txt = "✓ GeoParquet version 1.1.0\n✗ No bbox covering column\n⚠ Row groups are small\n"
    fs = Gpio().parse(ctx, a, "all", txt, 1, use_json=False)
    assert sorted(f.severity for f in fs) == ["error", "warning"]
    assert Gpio().parse(ctx, a, "spec", "", 2, use_json=False)[0].severity == "warning"
    js = json.dumps(
        {
            "checks": [
                {"name": "compression", "status": "warn", "message": "SNAPPY"},
                {"name": "bbox", "passed": True},
            ]
        }
    )
    fs = Gpio().parse(ctx, a, "all", js, 0, use_json=True)
    assert [(f.rule_id, f.severity) for f in fs] == [("gpio:all:compression", "warning")]


def test_rio_cogeo(ctx):
    a = next(
        x for x in ctx.crawl.assets if x.href.endswith("UB.parquet")
    )  # any asset works for parsing
    ctx.formats[a.href] = ("geotiff", "type")
    bad = (
        "The following errors were found:\n- The file is greater than 512xH or 512xW, but is not tiled\n"
        "The following warnings were found:\n- The file is greater than 512xH or 512xW, it is recommended "
        "to include internal overviews\n/x.tif is NOT a valid cloud optimized GeoTIFF\n"
    )
    fs = RioCogeo().parse(ctx, a, bad, 1)
    assert {f.rule_id for f in fs} == {"rio-cogeo:error", "rio-cogeo:warning", "CNC-FMT-001"}
    fs = RioCogeo().parse(ctx, a, "/x.tif is a valid cloud optimized GeoTIFF", 0)
    assert [f.rule_id for f in fs] == ["CNC-FMT-005"] and ctx.formats[a.href][0] == "cog"


def test_pmtiles_bounds_against_stac_bbox(ctx):
    import generate

    a = next(x for x in ctx.crawl.assets if x.href.endswith(".pmtiles"))
    import tempfile
    from pathlib import Path

    p = Path(tempfile.mkdtemp()) / "x.pmtiles"
    generate.pmtiles(p, clustered=False, bounds=(5.95590196, 45.81796213, 10.4920634, 47.80845431))
    ctx.probes[a.href] = Probe(range=Response(a.href, 206, {}, p.read_bytes()[:1024]))
    fs = Pmtiles().header_checks(ctx, a)
    assert [f.rule_id for f in fs] == ["PMT-003"]  # bounds match, but not clustered
    generate.pmtiles(p, bounds=(20, 50, 21, 51))
    ctx.probes[a.href] = Probe(range=Response(a.href, 206, {}, p.read_bytes()[:1024]))
    assert [f.rule_id for f in Pmtiles().header_checks(ctx, a)] == ["PMT-010"]


def test_hosting_probe(ctx):
    a = next(x for x in ctx.crawl.assets if x.href.endswith("UB.parquet"))
    good = Response(
        a.href,
        206,
        {
            "Content-Range": "bytes 0-1023/9999",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Range, Content-Length, ETag",
            "Content-Type": "application/x-parquet",
            "ETag": '"x"',
        },
        b"PAR1",
    )
    head = Response(a.href, 200, {"Accept-Ranges": "bytes", "Content-Length": "9999"})
    ctx.probes[a.href] = Probe(head=head, range=good, size=9999)
    assert Hosting().check(ctx, a) == []
    bad = Response(a.href, 200, {"Content-Type": "binary/octet-stream"}, b"PAR1")
    ctx.probes[a.href] = Probe(head=Response(a.href, 200, {}), range=bad, size=9999)
    rules = sorted(f.rule_id for f in Hosting().check(ctx, a))
    assert rules == ["CNC-HOST-001", "CNC-HOST-002", "CNC-HOST-003", "CNC-HOST-005", "CNC-HOST-006"]
    ctx.probes[a.href] = Probe(range=Response(a.href, 403, {}), head=Response(a.href, 403, {}))
    assert [f.rule_id for f in Hosting().check(ctx, a)] == ["CNC-HOST-000"]


def test_gpio_optimization_score_parsing():
    from conformance.adapters.gpio import parse_score

    assert parse_score('{"score": 73.5, "factors": []}') == 73.5
    assert parse_score("Optimization score: 4/5 factors ... 80/100") == 80.0
    assert parse_score("Spatial query optimization score: 64") == 64.0
    assert parse_score("nothing here") is None


def test_parquet_footer_version_decoding():
    from conformance.adapters.parquet_footer import footer_length, metadata_version

    assert metadata_version(b"\x15\x04rest") == 2  # field 1, i32, zigzag(4) = 2
    assert metadata_version(b"\x15\x02rest") == 1
    assert metadata_version(b"\x05\x02\x04") == 2  # long-form field header
    assert metadata_version(b"\x16\x04") is None  # not an i32
    assert metadata_version(b"\x25\x04") is None  # field 2, not version
    assert footer_length(b"\x10\x00\x00\x00PAR1") == 16
    assert footer_length(b"\x10\x00\x00\x00PAR2") is None


def _parquet_like(path, version: int):
    """Minimal file with a real Parquet tail: PAR1 ... <footer><len>PAR1 (footer: version + filler)."""
    import struct

    footer = bytes([0x15, version * 2]) + b"\x00" * 30
    path.write_bytes(b"PAR1" + b"\x00" * 100 + footer + struct.pack("<I", len(footer)) + b"PAR1")


def test_parquet_footer_check_reads_two_ranges(tmp_path, config):
    from conformance.adapters.parquet_footer import ParquetFooter
    from conformance.crawl import Asset, CrawlResult
    from conformance.http import Fetcher

    cat = CatalogConfig(id="t", url=str(tmp_path / "catalog.json"))
    for v in (1, 2):
        p = tmp_path / f"v{v}.parquet"
        _parquet_like(p, v)
        a = Asset(
            "t",
            "data",
            str(p),
            "application/vnd.apache.parquet",
            ["data"],
            "c",
            None,
            str(tmp_path / "c.json"),
        )
        ctx = Context(
            config=config,
            fetcher=Fetcher(retries=0),
            crawl=CrawlResult(catalog=cat, root_url=cat.url),
        )
        version, cid = ParquetFooter().check(ctx, a)
        assert version == v
        c = ctx.checks[0]
        assert c.id == cid and c.outcome == ("pass" if v == 2 else "warn")
        assert f"FileMetaData.version={v}" in c.evidence and "tail -c 8" in c.command
    junk = tmp_path / "junk.parquet"
    junk.write_bytes(b"not a parquet file at all")
    a = Asset("t", "data", str(junk), None, ["data"], "c", None, str(tmp_path / "c.json"))
    ctx = Context(
        config=config, fetcher=Fetcher(retries=0), crawl=CrawlResult(catalog=cat, root_url=cat.url)
    )
    assert ParquetFooter().check(ctx, a)[0] is None and ctx.checks[0].outcome == "skipped"
