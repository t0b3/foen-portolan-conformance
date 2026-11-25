from __future__ import annotations

from conformance.http import Fetcher, RecordedTransport
from conformance.spec import compare_versions, parse_requirements, resolve_spec

from conftest import SAMPLE_REQUIREMENTS


def test_parse_requirements_counts():
    reqs = parse_requirements(SAMPLE_REQUIREMENTS)
    assert set(reqs) == {"PORTO-CORE-001", "PORTO-CORE-002", "PORTO-FMT-001"}
    assert reqs["PORTO-CORE-001"]["quote"] == "A Portolan catalog MUST be a valid STAC 1.1 catalog."


def test_resolve_latest_release_recorded(tmp_path):
    raw = "https://raw.githubusercontent.com/o/s/v1.2.0/specs/portolan/requirements.yaml"
    idx = tmp_path / "i.json"
    import json

    idx.write_text(
        json.dumps(
            {
                "https://api.github.com/repos/o/s/releases/latest": {
                    "body": {"tag_name": "v1.2.0"}
                },
                "https://api.github.com/repos/o/s/commits/v1.2.0": {"body": {"sha": "deadbeef"}},
                raw: {"body": SAMPLE_REQUIREMENTS},
            }
        )
    )
    s = resolve_spec(
        Fetcher(transport=RecordedTransport(idx), retries=0),
        "o/s",
        "specs/portolan/requirements.yaml",
    )
    assert (s.version, s.sha, s.source) == ("1.2.0", "deadbeef", "latest-release")
    assert s.counts == {"MUST": 2, "SHOULD": 1, "MAY": 0}
    assert (
        s.link("PORTO-FMT-001") == "https://github.com/o/s/blob/deadbeef/specs/portolan/formats.md"
    )


def test_fallback_to_main(tmp_path):
    import json

    idx = tmp_path / "i.json"
    idx.write_text(
        json.dumps(
            {
                "https://api.github.com/repos/o/s/releases/latest": {"status": 404, "body": {}},
                "https://raw.githubusercontent.com/o/s/main/r.yaml": {"body": SAMPLE_REQUIREMENTS},
            }
        )
    )
    s = resolve_spec(Fetcher(transport=RecordedTransport(idx), retries=0), "o/s", "r.yaml")
    assert s.ref == "main" and s.source == "main-fallback" and "main branch" in s.note


def test_compare_versions():
    assert compare_versions("0.1.2", "0.3.0") == -1
    assert compare_versions("0.10.0", "0.9.9") == 1
    assert compare_versions(None, "0.1.0") == -1
