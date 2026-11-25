"""stac-validator 4.x (`stac-valid`) CLI handling, against a fake CLI that mimics it.

4.x has a `validate` subcommand and no --version; 3.x took the path directly. The real tool
is covered by tests/test_tools.py::test_stac_validator_real in CI.
"""

from __future__ import annotations

import os
import shutil
import stat

import pytest

from conformance import toolchain
from conformance.adapters import Context
from conformance.adapters.stac_validator import StacValidator, validate_subcommand
from conformance.config import CatalogConfig, load_config
from conformance.crawl import crawl
from conformance.http import Fetcher

from conftest import FIXTURES

FAKE = FIXTURES / "fakebin" / "stac-validator"


def _clear():
    for f in (toolchain.version, toolchain.help_text, toolchain.uv_tool_versions):
        f.cache_clear()


@pytest.fixture
def fake_path(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy(FAKE, bin_dir / "stac-validator")
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n[ \"$1 $2\" = 'tool list' ] && printf 'stac-valid v4.6.3\\n- stac-validator\\n'\nexit 0\n"
    )
    for p in bin_dir.iterdir():
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    _clear()
    yield bin_dir
    _clear()


def test_validate_subcommand_and_version_from_uv(fake_path):
    assert validate_subcommand() == ["validate"]
    # No --version flag in 4.x: the version comes from the uv tool that provides the command.
    assert toolchain.version("stac-validator") == "4.6.3"
    assert StacValidator().cmd("x.json") == ["stac-validator", "validate", "x.json"]


def test_adapter_runs_4x_cli(fake_path, tmp_path):
    import json

    good = FIXTURES / "smoke" / "collection.json"
    bad = tmp_path / "bad.json"
    doc = json.loads(good.read_text())
    del doc["license"]
    bad.write_text(json.dumps(doc))
    cfg = load_config(FIXTURES.parents[1] / "config.yaml")
    for path, expect_error in ((good, False), (bad, True)):
        cr = crawl(CatalogConfig(id="smoke", url=str(path)), Fetcher(retries=0))
        ctx = Context(config=cfg, fetcher=Fetcher(retries=0), crawl=cr)
        obj, ad = cr.objects[0], StacValidator()
        fs = ad.record_object(ctx, obj, ad.check(ctx, obj), ad.cmd(obj.url))
        assert not any(f.rule_id == "tool-error" for f in fs), fs
        assert any(f.severity == "error" for f in fs) is expect_error
        assert (
            ctx.checks[0].command == f"uvx --from stac-valid==4.6.3 stac-validator validate {path}"
        )


def test_3x_cli_without_subcommand(tmp_path, monkeypatch):
    b = tmp_path / "stac-validator"
    b.write_text(
        "#!/bin/sh\necho 'Usage: stac-validator [OPTIONS] STAC_FILE'\necho '  --core  Validate core only'\n"
    )
    b.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    _clear()
    try:
        assert validate_subcommand() == []
    finally:
        _clear()


def test_parse_uv_tool_list():
    text = "geoparquet-io v1.8.0\n- gpio\nstac-valid v4.6.3\n- stac-validator\nrasterio v1.4.3\n- rio\n"
    assert toolchain.parse_uv_tool_list(text) == {
        "gpio": "1.8.0",
        "stac-validator": "4.6.3",
        "rio": "1.4.3",
    }
