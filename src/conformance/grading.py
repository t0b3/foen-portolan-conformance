"""Asset grade (the report's score): A to F, the same rule for every cloud-native format.

Rule:
- every asset starts at A
- each best practice or recommendation that is not met drops the grade by one level:
  every MUST failure or SHOULD warning on the asset, from any tool (gpio, rio-cogeo, the
  PMTiles/COPC/Zarr checks, the hosting probe, rashid, ...), counts once
- GeoParquet: not being Parquet format v2 is one of them (CNC-PQ-001). A version that could not
  be confirmed counts too (CNC-PQ-002), because A needs every best practice to be *confirmed*
- the same problem reported twice by one tool counts once
- floor is F; a data asset in a format that is not cloud-native (GeoPackage, Shapefile, plain
  GeoTIFF, unknown, ...) is F outright
- an asset that no format validator could read gets no grade ("unverified"): an unchecked file
  must not look like an A

So A means: verified, and every best practice met. B means exactly one missing, and so on.
Info-level notes (ETag missing, media type spelling, ...) do not count.
"""

from __future__ import annotations

import re

GRADES = "ABCDEF"
NOT_CLOUD_NATIVE = {"CNC-FMT-001", "CNC-FMT-002"}
UNCONFIRMED = {"CNC-PQ-002"}  # a best practice that could not be confirmed
VALIDATED_FORMATS = {"geoparquet", "cog", "geotiff", "pmtiles", "zarr", "copc"}
SEV_RANK = {"error": 0, "warning": 1, "info": 2}
METHOD = (
    "Start at A; each best practice or recommendation not met (any MUST or SHOULD finding on the "
    "asset; for GeoParquet also Parquet v2 missing or unconfirmed) drops one level; floor F. "
    "Not a cloud-native format: F. No validator could read it: no grade. A only if every best "
    "practice is met."
)


def _key(f: dict) -> tuple:
    msg = re.sub(r"\s+", " ", f["message"].strip().lower())
    return (f["tool"], msg)


def grade_asset(asset: dict, findings: list[dict]) -> dict | None:
    """findings: every non-coverage finding on this asset. Returns None for ancillary assets."""
    if not asset["scored"]:
        return None
    nc = [f for f in findings if f["rule_id"] in NOT_CLOUD_NATIVE]
    if nc:
        return {
            "grade": "F",
            "levels_dropped": None,
            "unmet": [f["fingerprint"] for f in nc],
            "reason": "not a cloud-native format",
            "method": METHOD,
        }
    if asset["format"] in VALIDATED_FORMATS and not asset.get("verified_by"):
        return {
            "grade": None,
            "levels_dropped": None,
            "unmet": [],
            "reason": "unverified: no format validator could read it",
            "method": METHOD,
        }
    unmet, seen = [], set()
    for f in sorted(findings, key=lambda f: (SEV_RANK[f["severity"]], f["rule_id"], f["message"])):
        if f["severity"] not in ("error", "warning") and f["rule_id"] not in UNCONFIRMED:
            continue
        k = _key(f)
        if k in seen:
            continue
        seen.add(k)
        unmet.append(f)
    n = len(unmet)
    grade = GRADES[min(n, len(GRADES) - 1)]
    return {
        "grade": grade,
        "levels_dropped": n,
        "unmet": [f["fingerprint"] for f in unmet],
        "reason": "every best practice met"
        if n == 0
        else f"{n} best practice(s) or recommendation(s) not met",
        "method": METHOD,
    }
