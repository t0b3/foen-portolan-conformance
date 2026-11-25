"""Grade rule: start at A, one level down per best practice not met; A only if all are met."""

from __future__ import annotations

from conformance.antipatterns import CATALOG, classify
from conformance.antipatterns import summarize as summarize_aps
from conformance.grading import grade_asset


def _asset(fmt="geoparquet", verified=("gpio",), scored=True):
    return {"format": fmt, "scored": scored, "verified_by": list(verified)}


def _f(rule, sev="warning", msg=None, tool="gpio", fp=None, href="https://x/a.parquet", col="c"):
    return {
        "rule_id": rule,
        "severity": sev,
        "message": msg or rule,
        "tool": tool,
        "fingerprint": fp or f"fp-{rule}-{msg}",
        "catalog_id": "k",
        "collection": col,
        "asset_href": href,
    }


def test_all_best_practices_met_is_a():
    g = grade_asset(_asset(), [])
    assert (g["grade"], g["levels_dropped"], g["unmet"]) == ("A", 0, [])


def test_only_parquet_v2_missing_drops_one_level():
    g = grade_asset(_asset(), [_f("CNC-PQ-001", tool="parquet-footer")])
    assert (g["grade"], g["levels_dropped"]) == ("B", 1)


def test_each_further_recommendation_drops_one_more_level():
    fs = [
        _f("CNC-PQ-001", tool="parquet-footer"),
        _f("gpio:all:compression", msg="not ZSTD"),
        _f("gpio:all:bbox", msg="no bbox covering"),
    ]
    assert grade_asset(_asset(), fs)["grade"] == "D"
    many = fs + [_f(f"gpio:all:x{i}", msg=f"x{i}") for i in range(5)]
    assert grade_asset(_asset(), many)["grade"] == "F"  # floor


def test_unconfirmed_parquet_version_also_blocks_a_but_other_info_does_not():
    assert (
        grade_asset(_asset(), [_f("CNC-PQ-002", sev="info", tool="parquet-footer")])["grade"] == "B"
    )
    assert (
        grade_asset(_asset(), [_f("CNC-HOST-006", sev="info", tool="hosting-probe")])["grade"]
        == "A"
    )


def test_same_problem_twice_from_one_tool_counts_once():
    fs = [
        _f("gpio:spec:x", msg="Geometry column is not WKB"),
        _f("gpio:all:x", msg="geometry column is not  WKB"),
    ]
    assert grade_asset(_asset(), fs)["levels_dropped"] == 1


def test_same_rule_for_cog_pmtiles_copc_zarr():
    assert (
        grade_asset(_asset("cog", ["rio-cogeo"]), [_f("rio-cogeo:warning", tool="rio-cogeo")])[
            "grade"
        ]
        == "B"
    )
    assert (
        grade_asset(
            _asset("pmtiles", ["pmtiles"]),
            [_f("PMT-003", tool="pmtiles"), _f("PMT-011", tool="pmtiles")],
        )["grade"]
        == "C"
    )
    assert (
        grade_asset(_asset("copc", ["copc"]), [_f("COPC-002", sev="error", tool="copc")])["grade"]
        == "B"
    )
    assert (
        grade_asset(_asset("zarr", ["zarr-probe"]), [_f("ZARR-003", tool="zarr-probe")])["grade"]
        == "B"
    )
    # Hosting problems are best practices of the asset too.
    assert (
        grade_asset(_asset("cog", ["rio-cogeo"]), [_f("CNC-HOST-003", tool="hosting-probe")])[
            "grade"
        ]
        == "B"
    )


def test_not_cloud_native_is_f_and_unverified_is_ungraded():
    g = grade_asset(_asset("geopackage", []), [_f("CNC-FMT-001", tool="cloud-native-classifier")])
    assert g["grade"] == "F" and "cloud-native" in g["reason"]
    g = grade_asset(_asset("geoparquet", []), [])
    assert g["grade"] is None and "unverified" in g["reason"]
    assert grade_asset(_asset(scored=False), []) is None


def test_anti_pattern_classification():
    assert classify(_f("CNC-FMT-001", tool="cloud-native-classifier")) == "not_cloud_native"
    assert classify(_f("CNC-HOST-001", sev="error", tool="hosting-probe")) == "not_range_readable"
    assert classify(_f("CNC-HOST-004", tool="hosting-probe")) == "browser_blocked"
    assert (
        classify(_f("gpio:all:x", msg="Data is not spatially sorted (Hilbert)"))
        == "no_spatial_index"
    )
    assert (
        classify(_f("gpio:all:y", msg="Compression is SNAPPY, ZSTD recommended"))
        == "inefficient_layout"
    )
    assert classify(_f("CNC-PQ-001", tool="parquet-footer")) == "inefficient_layout"
    assert classify(_f("gpio:spec:z", sev="error", msg="primary column missing")) == "invalid"
    assert (
        classify(_f("PTL-COL-001", sev="error", msg="bbox missing", tool="rashid"))
        == "portolan_must"
    )
    assert (
        classify(_f("PTL-FMT-010", msg="not ZSTD compressed", tool="rashid"))
        == "inefficient_layout"
    )
    assert classify(_f("PTL-DOC-002", msg="no example", tool="rashid")) == "portolan_should"
    assert classify(_f("CNC-DOC-001", tool="docs-check")) == "missing_docs"
    assert classify(_f("gpio:all:q", msg="something new")) == "other"
    assert len({a.key for a in CATALOG}) == len(CATALOG)


def test_anti_patterns_ranked_by_severity_then_reach():
    fs = [
        _f("CNC-DOC-001", tool="docs-check", href=None),
        _f("gpio:all:a", msg="not spatially sorted", href="h1"),
        _f("gpio:all:b", msg="not spatially sorted", href="h2"),
        _f("CNC-HOST-003", tool="hosting-probe", href="h1"),
        _f("CNC-FMT-001", tool="cloud-native-classifier", href="h3"),
        _f("CNC-PQ-001", tool="parquet-footer", href="h1"),
        _f(
            "CNC-HOST-006", sev="info", tool="hosting-probe", href="h1"
        ),  # info: not an anti-pattern
    ]
    ids = {("k", "h1"): "a1", ("k", "h2"): "a2", ("k", "h3"): "a3"}
    aps = summarize_aps(fs, ids)
    assert [g["key"] for g in aps] == [
        "not_cloud_native",
        "browser_blocked",
        "no_spatial_index",
        "inefficient_layout",
        "missing_docs",
    ]
    assert [g["rank"] for g in aps] == [1, 2, 3, 4, 5]
    spatial = aps[2]
    assert spatial["assets"] == ["a1", "a2"] and spatial["rules"][0]["count"] == 1
    assert sum(len(g["findings"]) for g in aps) == 6
