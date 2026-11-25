"""Real validators against the generated fixtures. Skipped when a tool is not on PATH.

CI installs the latest tools and runs these, so a breaking upstream CLI change shows up here
(and in the weekly tool-canary job) rather than as silently empty reports.
"""

from __future__ import annotations

import shutil

import pytest

from conformance.adapters import Context, Probe
from conformance.adapters.gpio import Gpio
from conformance.adapters.pmtiles import Pmtiles
from conformance.adapters.rio_cogeo import RioCogeo
from conformance.config import CatalogConfig
from conformance.crawl import crawl
from conformance.formats import detect
from conformance.http import Fetcher

pytestmark = pytest.mark.tools


@pytest.fixture
def mctx(mini_config, mini_dir):
    f = Fetcher(retries=0)
    cr = crawl(CatalogConfig(id="mini", url=mini_config.catalogs[0].url), f)
    ctx = Context(config=mini_config, fetcher=f, crawl=cr)
    for a in cr.assets:
        r = f.get_range(a.href, 0, 1023)
        ctx.probes[a.href] = Probe(range=r, size=None)
        ctx.formats[a.href] = detect(a.href, a.media_type, r.body)
    return ctx


def _asset(ctx, name):
    return next(a for a in ctx.crawl.assets if a.href.endswith(name))


@pytest.mark.skipif(not shutil.which("gpio"), reason="gpio not installed")
def test_gpio_real(mctx, mini_dir):
    if not mini_dir[1]["geoparquet"]:
        pytest.skip("pyarrow missing: no real GeoParquet fixture")
    good = Gpio().check(mctx, _asset(mctx, "good.parquet"))
    bad = Gpio().check(mctx, _asset(mctx, "bad.parquet"))
    assert not any(f.rule_id == "tool-error" for f in good + bad)
    assert sum(f.severity == "error" for f in bad) > sum(f.severity == "error" for f in good)


@pytest.mark.skipif(not shutil.which("rio"), reason="rio-cogeo not installed")
def test_rio_cogeo_real(mctx, mini_dir):
    if not mini_dir[1]["cog"]:
        pytest.skip("GDAL missing: no COG fixture")
    good = RioCogeo().check(mctx, _asset(mctx, "good.tif"))
    bad = RioCogeo().check(mctx, _asset(mctx, "bad.tif"))
    assert not any(f.severity == "error" for f in good)
    assert any(f.severity == "error" for f in bad)


@pytest.mark.skipif(not shutil.which("pmtiles"), reason="go-pmtiles not installed")
def test_pmtiles_real(mctx):
    good = Pmtiles().tool_checks(mctx, _asset(mctx, "good.pmtiles"))
    assert not any(f.severity == "error" for f in good), good


@pytest.mark.skipif(not shutil.which("stac-validator"), reason="stac-validator not installed")
def test_stac_validator_real(tmp_path):
    """The adapter runs the real stac-validator and parses its JSON (valid + invalid object)."""
    import json

    from conformance.adapters.stac_validator import StacValidator
    from conformance.config import load_config

    from conftest import FIXTURES

    good = FIXTURES / "smoke" / "collection.json"
    bad = tmp_path / "bad.json"
    doc = json.loads(good.read_text())
    del doc["license"]
    bad.write_text(json.dumps(doc))
    cfg = load_config(FIXTURES.parents[1] / "config.yaml")
    for path, expect_error in ((good, False), (bad, True)):
        cr = crawl(CatalogConfig(id="smoke", url=str(path)), Fetcher(retries=0))
        ctx = Context(config=cfg, fetcher=Fetcher(retries=0), crawl=cr)
        obj = cr.objects[0]
        ad = StacValidator()
        fs = ad.record_object(ctx, obj, ad.check(ctx, obj), ad.cmd(obj.url))
        assert not any(f.rule_id == "tool-error" for f in fs), fs
        assert any(f.severity == "error" for f in fs) is expect_error, fs
        assert ctx.checks and ctx.checks[0].command.startswith("uvx --from stac-valid==")
