"""Scores and breakdowns derived from findings. Pure functions over plain dicts."""

from __future__ import annotations

from collections import defaultdict

# Cloud-native formats count as conformant only after a format validator read them.
VALIDATED_FORMATS = {"geoparquet", "cog", "geotiff", "pmtiles", "zarr", "copc"}

FORMAT_GROUPS = {
    "geoparquet": "GeoParquet",
    "cog": "COG",
    "pmtiles": "PMTiles",
    "zarr": "Zarr",
    "copc": "COPC",
}


def group_of(fmt: str | None) -> str:
    return FORMAT_GROUPS.get(fmt or "", "Other")


def is_coverage(f: dict) -> bool:
    return f["rule_id"] in {
        "tool-error",
        "tool-missing",
        "skipped-size",
        "coverage-limit",
        "skipped-mode",
    }


def summarize(assets: list[dict], findings: list[dict], declared: dict, spec: dict) -> dict:
    """assets: [{href, catalog_id, collection, item, key, format, scored, ...}]"""
    conf = [f for f in findings if not is_coverage(f)]
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for f in conf:
        if f.get("asset_href"):
            by_asset[f["asset_href"]].append(f)

    scored = [a for a in assets if a["scored"]]
    for a in assets:
        fs = by_asset.get(a["href"], [])
        a["errors"] = sum(f["severity"] == "error" for f in fs)
        a["warnings"] = sum(f["severity"] == "warning" for f in fs)
        needs_validator = a["format"] in VALIDATED_FORMATS
        if a["errors"]:
            a["status"] = "fail"
        elif a["warnings"]:
            a["status"] = "warn"
        elif needs_validator and not a.get("verified_by"):
            a["status"] = "unverified"
        else:
            a["status"] = "pass"

    def pct(n: int, d: int) -> float | None:
        return round(100.0 * n / d, 1) if d else None

    fully = sum(a["status"] == "pass" for a in scored)
    must_ok = sum(a["errors"] == 0 and a["status"] != "unverified" for a in scored)
    unverified = sum(a["status"] == "unverified" for a in scored)

    fmt: dict[str, dict] = {}
    for a in scored:
        g = fmt.setdefault(
            group_of(a["format"]),
            {"assets": 0, "fully_conformant": 0, "unverified": 0, "errors": 0, "warnings": 0},
        )
        g["assets"] += 1
        g["unverified"] += a["status"] == "unverified"
        g["fully_conformant"] += a["status"] == "pass"
        g["errors"] += a["errors"]
        g["warnings"] += a["warnings"]
    order = ["GeoParquet", "COG", "PMTiles", "Zarr", "COPC", "Other"]
    by_format = {
        k: fmt[k] | {"pct": pct(fmt[k]["fully_conformant"], fmt[k]["assets"])}
        for k in order
        if k in fmt
    }

    cols: dict[tuple, dict] = {}
    for a in assets:
        key = (a["catalog_id"], a["collection"] or "")
        c = cols.setdefault(
            key,
            {
                "catalog_id": key[0],
                "collection": key[1],
                "assets": 0,
                "scored_assets": 0,
                "fully_conformant": 0,
            },
        )
        c["assets"] += 1
        if a["scored"]:
            c["scored_assets"] += 1
            c["fully_conformant"] += a["status"] == "pass"
    for f in conf:
        key = (f["catalog_id"], f.get("collection") or "")
        c = cols.setdefault(
            key,
            {
                "catalog_id": key[0],
                "collection": key[1],
                "assets": 0,
                "scored_assets": 0,
                "fully_conformant": 0,
            },
        )
        c[f["severity"] + "s"] = c.get(f["severity"] + "s", 0) + 1
    collections = []
    for _, c in sorted(cols.items()):
        c.setdefault("errors", 0), c.setdefault("warnings", 0), c.setdefault("infos", 0)
        c["pct"] = pct(c["fully_conformant"], c["scored_assets"])
        collections.append(c)

    must_latest = [f for f in conf if f["severity"] == "error"]
    declared_ids = set(declared.get("requirement_ids") or [])
    latest_ids = set(spec.get("requirement_ids") or [])
    if declared.get("requirements_available"):
        must_declared = [
            f
            for f in must_latest
            if not f.get("spec_requirement_id") or f["spec_requirement_id"] in declared_ids
        ]
        declared_must: int | None = len(must_declared)
    else:
        declared_must = None
    return {
        "scored_assets": len(scored),
        "ancillary_assets": len(assets) - len(scored),
        "fully_conformant_assets": fully,
        "must_conformant_assets": must_ok,
        "unverified_assets": unverified,
        "pct_fully_conformant": pct(fully, len(scored)),
        "pct_must_conformant": pct(must_ok, len(scored)),
        "must_failures": len(must_latest),
        "should_warnings": sum(f["severity"] == "warning" for f in conf),
        "infos": sum(f["severity"] == "info" for f in conf),
        "coverage_notes": sum(is_coverage(f) for f in findings),
        "by_format": by_format,
        "collections": collections,
        "spec_conformance": {
            "latest": {"version": spec.get("version"), "must_failures": len(must_latest)},
            "declared": {
                "version": declared.get("primary"),
                "must_failures": declared_must,
                "note": None
                if declared_must is not None
                else "Requirements manifest for the declared version is not available, so "
                "conformance to it could not be computed separately.",
            },
            "behind_latest": declared.get("behind_latest"),
            "requirements_added_since_declared": sorted(latest_ids - declared_ids)
            if declared_ids
            else None,
        },
    }


def diff(current: list[dict], previous: list[dict] | None) -> dict:
    if previous is None:
        return {"baseline": True, "new": [], "resolved": []}
    cur = {f["fingerprint"]: f for f in current if not is_coverage(f)}
    prev = {f["fingerprint"]: f for f in previous if not is_coverage(f)}
    new = [cur[k] for k in sorted(cur.keys() - prev.keys(), key=lambda k: _sk(cur[k]))]
    res = [prev[k] for k in sorted(prev.keys() - cur.keys(), key=lambda k: _sk(prev[k]))]
    return {"baseline": False, "new": new, "resolved": res}


def _sk(f: dict) -> tuple:
    return (
        f["catalog_id"],
        f.get("collection") or "",
        f.get("asset_href") or "",
        f["severity"],
        f["rule_id"],
        f["message"],
    )
