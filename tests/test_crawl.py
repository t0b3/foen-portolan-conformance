from __future__ import annotations

from conformance.config import CatalogConfig
from conformance.crawl import crawl, declared_portolan_versions
from conformance.http import Fetcher

from conftest import BAFU_ROOT


def test_recorded_bafu_catalog(recorded_fetcher):
    res = crawl(CatalogConfig(id="bafu", url=BAFU_ROOT), recorded_fetcher)
    ids = sorted(c.id for c in res.collections)
    assert ids == sorted(
        [
            "ub",
            "ba",
            "ei",
            "ip",
            "nk",
            "naqua_regions",
            "nawa_trend_stations",
            "hydro_stations",
            "mfm-u_stations",
        ]
    )
    assert not res.items  # this catalog keeps assets on collections
    assert len(res.assets) == 31
    gpkg = [a for a in res.assets if a.href.endswith(".gpkg")]
    assert len(gpkg) == 5 and all(a.roles == ["data"] for a in gpkg)
    assert res.assets[0].href.startswith(
        "https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/"
    )
    declared = declared_portolan_versions(res.objects)
    assert list(declared) == ["0.1.2"]
    # naqua_regions does not declare the Portolan extension.
    assert not any("naqua_regions" in u for u in declared["0.1.2"])
    assert not res.findings


def test_include_exclude(recorded_fetcher):
    cat = CatalogConfig(id="bafu", url=BAFU_ROOT, include=["n*"], exclude=["nk"])
    res = crawl(cat, recorded_fetcher)
    assert sorted(c.id for c in res.collections) == ["naqua_regions", "nawa_trend_stations"]
    assert "ub" in res.skipped_collections and "nk" in res.skipped_collections


def test_local_catalog_with_items_and_broken_link(mini_dir):
    path, _ = mini_dir
    res = crawl(CatalogConfig(id="mini", url=str(path / "catalog.json")), Fetcher(retries=0))
    assert sorted(c.id for c in res.collections) == ["raster", "tiles", "vector"]
    assert [i.id for i in res.items] == ["item-1"]
    item_assets = [a for a in res.assets if a.item == "item-1"]
    assert {a.key for a in item_assets} == {"cog", "plain"} and item_assets[
        0
    ].collection == "raster"
    assert [f.rule_id for f in res.findings] == ["CRAWL-001"]  # ./missing/collection.json


def test_crawl_order_is_deterministic(recorded_fetcher):
    a = crawl(CatalogConfig(id="b", url=BAFU_ROOT), recorded_fetcher)
    b = crawl(CatalogConfig(id="b", url=BAFU_ROOT), recorded_fetcher)
    assert [o.url for o in a.objects] == [o.url for o in b.objects]
    assert [x.href for x in a.assets] == [x.href for x in b.assets]
