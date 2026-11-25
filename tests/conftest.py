from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

from conformance.config import CatalogConfig, Config, load_config  # noqa: E402
from conformance.http import Fetcher, RecordedTransport  # noqa: E402
from conformance.spec import SpecInfo  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
RECORDED = FIXTURES / "recorded" / "bafu" / "index.json"
BAFU_ROOT = "https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json"

SAMPLE_REQUIREMENTS = """
files: [specs/portolan/core.md]
requirements:
  - id: PORTO-CORE-001
    severity: MUST
    enforcement: validator
    file: specs/portolan/core.md
    quote: >-
      A Portolan catalog MUST be a valid STAC 1.1 catalog.
  - id: PORTO-CORE-002
    severity: SHOULD
    file: specs/portolan/core.md
    quote: Collections SHOULD link a README.
  - id: PORTO-FMT-001
    severity: MUST
    file: specs/portolan/formats.md
    quote: Vector data MUST be GeoParquet.
exclusions: []
"""


@pytest.fixture(scope="session")
def mini_dir(tmp_path_factory) -> tuple[Path, dict]:
    import generate

    out = tmp_path_factory.mktemp("mini")
    made = generate.mini_catalog(out)
    return out, made


@pytest.fixture
def config() -> Config:
    return load_config(ROOT / "config.yaml")


@pytest.fixture
def mini_config(mini_dir, config) -> Config:
    path, _ = mini_dir
    config.catalogs = [CatalogConfig(id="mini", url=str(path / "catalog.json"))]
    return config


@pytest.fixture
def recorded_fetcher() -> Fetcher:
    return Fetcher(transport=RecordedTransport(RECORDED), retries=0)


@pytest.fixture
def spec() -> SpecInfo:
    from conformance.spec import parse_requirements

    return SpecInfo(
        "portolan-sdi/portolan-spec",
        "v0.3.0",
        "0.3.0",
        "abc123",
        "pinned",
        parse_requirements(SAMPLE_REQUIREMENTS),
    )
