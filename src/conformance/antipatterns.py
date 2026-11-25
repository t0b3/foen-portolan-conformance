"""Group findings into general anti-patterns and rank them, so readers know where to start.

Each MUST or SHOULD finding (info notes and coverage gaps excluded) is put in exactly one
general anti-pattern, by rule ID first and keywords in the message second. Groups are ranked by
severity (critical > high > medium > low), then by how many assets they hit, then by how many
findings they have. The table is the single place to change a classification.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

SEVERITY_ORDER = ["critical", "high", "medium", "low"]


@dataclass(frozen=True)
class AntiPattern:
    key: str
    title: str
    severity: str
    why: str
    fix: str
    rules: tuple[str, ...] = ()  # exact rule IDs or prefixes ending in ":" or "-"
    keywords: tuple[str, ...] = ()  # regexes on the lower-cased message (tools without stable IDs)
    tools: tuple[str, ...] = ()  # keywords only apply to findings from these tools


CATALOG: list[AntiPattern] = [
    AntiPattern(
        "not_cloud_native",
        "Data not in a cloud-native format",
        "critical",
        "Clients must download the whole file before reading anything; no partial or remote reads.",
        "Convert: vector to GeoParquet (`gpio convert`), raster to COG (`rio cogeo create`), "
        "tiles to PMTiles. Keep the old format only as an extra download.",
        rules=("CNC-FMT-001", "CNC-FMT-002", "CNC-FMT-006"),
    ),
    AntiPattern(
        "not_range_readable",
        "Not readable with HTTP range requests",
        "critical",
        "Cloud-native formats depend on reading byte ranges; without them every read is a full download "
        "or fails.",
        "Serve the files from storage that honours `Range` (S3, GCS, most CDNs) and returns 206 and "
        "`Accept-Ranges: bytes`; make them public for anonymous reads.",
        rules=("CNC-HOST-000", "CNC-HOST-001", "CNC-HOST-002"),
    ),
    AntiPattern(
        "invalid",
        "Invalid or broken files and metadata",
        "critical",
        "Readers may reject the file or silently misread it.",
        "Fix the reported validation errors; re-run the tool command shown with each finding.",
        rules=(
            "stac-validator:",
            "stac-check:invalid",
            "PMT-001",
            "PMT-002",
            "PMT-004",
            "pmtiles:verify",
            "COPC-001",
            "COPC-002",
            "ZARR-001",
            "ZARR-002",
            "rio-cogeo:invalid",
            "gpio:spec:",
            "CRAWL-001",
            "PTL-EXIT-1",
            "pdal:info",
        ),
    ),
    AntiPattern(
        "portolan_must",
        "Portolan MUST requirements broken",
        "high",
        "The catalog does not meet the Portolan specification it declares.",
        "Follow the requirement text linked with each finding (rashid rule and PORTO- ID).",
        rules=("PTL-",),  # rashid errors; rashid warnings go to portolan_should (see classify)
    ),
    AntiPattern(
        "browser_blocked",
        "Blocked for browser clients (CORS)",
        "high",
        "Web maps and the Portolan browser cannot read the data from another origin.",
        "Add a CORS rule: allow GET/HEAD from any origin, allow the `Range` header, expose "
        "`Content-Range`, `Content-Length` and `ETag`.",
        rules=("CNC-HOST-003", "CNC-HOST-004", "CNC-HOST-010", "CNC-HOST-011"),
    ),
    AntiPattern(
        "no_spatial_index",
        "No spatial index or ordering",
        "medium",
        "A query for a small area still reads most of the file.",
        "GeoParquet: sort spatially (`gpio sort hilbert`) and add a bbox covering column (see `gpio add --help`). "
        "COG: internal tiling and overviews. PMTiles: write a clustered archive.",
        rules=("PMT-003",),
        keywords=(
            r"bbox|covering|hilbert|spatial(ly)? (order|sort|index)|sorted|partition|overview|"
            r"\btil(ed|ing|es)\b|block size|internal tiling",
        ),
        tools=("gpio", "rio-cogeo", "rashid"),
    ),
    AntiPattern(
        "inefficient_layout",
        "Inefficient storage layout",
        "medium",
        "More bytes and more requests than needed for every read.",
        "GeoParquet: Parquet format v2, ZSTD compression, row groups of roughly 64-256 MB (`gpio convert`). "
        "COG: DEFLATE/ZSTD/LERC compression. Zarr: consolidated metadata.",
        rules=("CNC-PQ-001", "ZARR-003"),
        keywords=(
            r"compress|zstd|snappy|gzip|row.?group|page size|dictionary|statistic|encoding|"
            r"interleav|predictor|consolidat",
        ),
        tools=("gpio", "rio-cogeo", "rashid"),
    ),
    AntiPattern(
        "metadata_mismatch",
        "Metadata does not match the data",
        "medium",
        "Catalog search and clients make wrong assumptions: wrong format, extent or licence.",
        "Set the STAC asset `type` to the registered media type, keep bboxes in sync with the data, "
        "declare the Portolan extension and a licence.",
        rules=(
            "CNC-FMT-003",
            "CNC-FMT-005",
            "CNC-HOST-005",
            "PMT-005",
            "PMT-010",
            "PMT-011",
            "CNC-META-001",
            "CNC-LIC-",
        ),
        keywords=(r"\bcrs\b|projjson|epsg|media type|content.?type|extent|bounds",),
        tools=("gpio", "rio-cogeo", "rashid"),
    ),
    AntiPattern(
        "portolan_should",
        "Portolan recommendations (SHOULD) not followed",
        "medium",
        "Not wrong, but harder to find, use or trust than the spec intends.",
        "Follow the requirement text linked with each finding.",
    ),
    AntiPattern(
        "missing_docs",
        "Missing documentation",
        "low",
        "People and agents cannot tell what the data is or how to use it.",
        "Add README.md and AGENTS.md beside the catalog and each collection (and llms.txt at the root), "
        "linked from the STAC JSON.",
        rules=("CNC-DOC-",),
    ),
    AntiPattern(
        "stac_best_practice",
        "STAC best practices not followed",
        "low",
        "Interoperability and discoverability suffer in generic STAC tools.",
        "Apply the stac-check suggestions shown with each finding.",
        rules=("stac-check:best-practice",),
    ),
    AntiPattern(
        "other",
        "Other best practices not met",
        "low",
        "Reported by a validator but not matched to a general pattern above.",
        "See the tool message and the reproduce command with each finding.",
    ),
]
BY_KEY = {a.key: a for a in CATALOG}
assert all(isinstance(a.keywords, tuple) and isinstance(a.rules, tuple) for a in CATALOG), (
    "keywords/rules must be tuples (a missing trailing comma turns them into one string)"
)


def _rule_match(rule: str, patterns: tuple[str, ...]) -> bool:
    return any(rule == p or (p.endswith((":", "-")) and rule.startswith(p)) for p in patterns)


def classify(f: dict) -> str:
    rule, tool, msg = f["rule_id"], f["tool"], f["message"].lower()
    # Exact rule IDs first (everything except the rashid catch-all).
    for ap in CATALOG:
        if ap.key != "portolan_must" and ap.rules and _rule_match(rule, ap.rules):
            return ap.key
    # Tool messages without stable IDs: keywords.
    for ap in CATALOG:
        if ap.keywords and tool in ap.tools and any(re.search(k, msg) for k in ap.keywords):
            if tool == "rashid" and f["severity"] == "error":
                break  # a broken MUST stays a MUST, whatever it is about
            return ap.key
    if rule.startswith("PTL-"):
        return "portolan_must" if f["severity"] == "error" else "portolan_should"
    if tool == "rio-cogeo" and f["severity"] == "error":
        return "invalid"
    return "other"


def summarize(findings: list[dict], asset_ids_by_href: dict[tuple, str]) -> list[dict]:
    """Ranked anti-pattern groups. Only MUST/SHOULD findings; coverage and info excluded."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        if f["severity"] in ("error", "warning"):
            groups[classify(f)].append(f)
    out = []
    for key, fs in groups.items():
        ap = BY_KEY[key]
        assets = sorted(
            {
                asset_ids_by_href[(f["catalog_id"], f["asset_href"])]
                for f in fs
                if (f["catalog_id"], f.get("asset_href")) in asset_ids_by_href
            }
        )
        cols = sorted({f"{f['catalog_id']}/{f.get('collection') or ''}" for f in fs})
        by_rule: dict[str, list[dict]] = defaultdict(list)
        for f in fs:
            by_rule[f["rule_id"]].append(f)
        out.append(
            {
                "key": key,
                "title": ap.title,
                "severity": ap.severity,
                "why": ap.why,
                "fix": ap.fix,
                "findings": [f["fingerprint"] for f in fs],
                "must": sum(f["severity"] == "error" for f in fs),
                "should": sum(f["severity"] == "warning" for f in fs),
                "assets": assets,
                "collections": cols,
                "rules": [
                    {
                        "rule_id": r,
                        "count": len(v),
                        "findings": [f["fingerprint"] for f in v],
                        "example": v[0]["message"],
                        "tool": v[0]["tool"],
                    }
                    for r, v in sorted(by_rule.items(), key=lambda kv: (-len(kv[1]), kv[0]))
                ],
            }
        )
    out.sort(
        key=lambda g: (
            SEVERITY_ORDER.index(g["severity"]),
            -len(g["assets"]),
            -len(g["findings"]),
            g["key"],
        )
    )
    for i, g in enumerate(out, 1):
        g["rank"] = i
    return out
