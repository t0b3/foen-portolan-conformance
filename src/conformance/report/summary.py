"""Scores and breakdowns derived from findings, assets and checks. Pure functions over dicts.

Every number in the summary has a matching entry in `drill`: the exact list of assets,
findings, checks or requirements it counts. The page uses it to open any number and show its
children, and `tests/test_report.py` asserts that each number equals the length of its list.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

FORMAT_GROUPS = {
    "geoparquet": "GeoParquet",
    "cog": "COG",
    "pmtiles": "PMTiles",
    "zarr": "Zarr",
    "copc": "COPC",
}
FORMAT_ORDER = ["GeoParquet", "COG", "PMTiles", "Zarr", "COPC", "Other"]
# Cloud-native formats count as conformant only after a format validator read them.
VALIDATED_FORMATS = {"geoparquet", "cog", "geotiff", "pmtiles", "zarr", "copc"}
COVERAGE_RULES = {"tool-error", "tool-missing", "skipped-size", "coverage-limit", "skipped-mode"}


def group_of(fmt: str | None) -> str:
    return FORMAT_GROUPS.get(fmt or "", "Other")


def is_coverage(f: dict) -> bool:
    return f["rule_id"] in COVERAGE_RULES


def asset_id(catalog_id: str, href: str) -> str:
    return "a" + hashlib.sha1(f"{catalog_id}\x1f{href}".encode()).hexdigest()[:12]


class Drill:
    """Collects {path: {kind, ids}} while counts are computed, so they cannot drift apart."""

    def __init__(self) -> None:
        self.d: dict[str, dict] = {}

    def put(self, path: str, kind: str, ids: list[str], label: str) -> int:
        self.d[path] = {"kind": kind, "ids": list(ids), "label": label}
        return len(ids)


def summarize(
    assets: list[dict],
    findings: list[dict],
    declared: dict,
    spec: dict,
    checks: list[dict] | None = None,
    requirements: dict | None = None,
) -> dict:
    checks = checks or []
    dr = Drill()
    conf = [f for f in findings if not is_coverage(f)]
    cov = [f for f in findings if is_coverage(f)]
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for f in conf:
        if f.get("asset_href"):
            by_asset[(f["catalog_id"], f["asset_href"])].append(f)

    top_by_asset: dict[tuple, list[str]] = defaultdict(list)
    for c in checks:
        if c.get("asset_href") and not c.get("parent"):
            top_by_asset[(c["catalog_id"], c["asset_href"])].append(c["id"])
    for a in assets:
        a.setdefault("id", asset_id(a["catalog_id"], a["href"]))
        fs = by_asset.get((a["catalog_id"], a["href"]), [])
        a["errors"] = sum(f["severity"] == "error" for f in fs)
        a["warnings"] = sum(f["severity"] == "warning" for f in fs)
        a["finding_ids"] = [f["fingerprint"] for f in fs]
        a["check_ids"] = top_by_asset.get((a["catalog_id"], a["href"]), [])
        if a["errors"]:
            a["status"] = "fail"
        elif a["warnings"]:
            a["status"] = "warn"
        elif a["format"] in VALIDATED_FORMATS and not a.get("verified_by"):
            a["status"] = "unverified"
        else:
            a["status"] = "pass"

    scored = [a for a in assets if a["scored"]]
    ids = lambda xs: [x["id"] for x in xs]
    fps = lambda xs: [x["fingerprint"] for x in xs]

    def pct(n: int, d: int) -> float | None:
        return round(100.0 * n / d, 1) if d else None

    s: dict = {}
    s["scored_assets"] = dr.put(
        "scored_assets", "assets", ids(scored), "Scored assets (data and tiles)"
    )
    s["ancillary_assets"] = dr.put(
        "ancillary_assets",
        "assets",
        ids([a for a in assets if not a["scored"]]),
        "Ancillary assets (thumbnails, styles, documents) - hosting-probed, not scored",
    )
    s["fully_conformant_assets"] = dr.put(
        "fully_conformant_assets",
        "assets",
        ids([a for a in scored if a["status"] == "pass"]),
        "Fully conformant assets: no MUST or SHOULD finding, validated",
    )
    s["must_conformant_assets"] = dr.put(
        "must_conformant_assets",
        "assets",
        ids([a for a in scored if a["errors"] == 0 and a["status"] != "unverified"]),
        "Assets without MUST failures (validated)",
    )
    s["unverified_assets"] = dr.put(
        "unverified_assets",
        "assets",
        ids([a for a in scored if a["status"] == "unverified"]),
        "Unverified assets: no format validator could read them",
    )
    s["pct_fully_conformant"] = pct(s["fully_conformant_assets"], s["scored_assets"])
    s["pct_must_conformant"] = pct(s["must_conformant_assets"], s["scored_assets"])
    s["must_failures"] = dr.put(
        "must_failures",
        "findings",
        fps([f for f in conf if f["severity"] == "error"]),
        "MUST failures (severity error)",
    )
    s["should_warnings"] = dr.put(
        "should_warnings",
        "findings",
        fps([f for f in conf if f["severity"] == "warning"]),
        "SHOULD warnings (severity warning)",
    )
    s["infos"] = dr.put(
        "infos", "findings", fps([f for f in conf if f["severity"] == "info"]), "Info findings"
    )
    s["coverage_notes"] = dr.put(
        "coverage_notes",
        "findings",
        fps(cov),
        "Coverage notes: what did not run and why (not failures)",
    )
    top = [c for c in checks if not c.get("parent")]
    s["checks"] = {
        "total": dr.put(
            "checks.total", "checks", ids(checks), "Every check (tool runs and their sub-checks)"
        )
    }
    for o in ("pass", "fail", "warn", "info", "skipped", "error"):
        s["checks"][o] = dr.put(
            f"checks.{o}",
            "checks",
            ids([c for c in checks if c["outcome"] == o]),
            f"Checks with outcome '{o}'",
        )
    s["checks"]["top_level"] = dr.put(
        "checks.top_level", "checks", ids(top), "Top-level checks (one per tool run)"
    )

    must_fps = {f["fingerprint"] for f in conf if f["severity"] == "error"}
    should_fps = {f["fingerprint"] for f in conf if f["severity"] == "warning"}
    # Grades (A-F) for every scored asset; see grading.py. Every grade drills down to the
    # findings that cost it a level.
    from .. import antipatterns
    from ..grading import GRADES, METHOD, grade_asset

    for a in assets:
        a["grade"] = grade_asset(a, by_asset.get((a["catalog_id"], a["href"]), []))
    graded = [a for a in scored if a["grade"] and a["grade"]["grade"]]
    gs: dict = {
        "method": METHOD,
        "graded": dr.put("grades.graded", "assets", ids(graded), "Graded assets"),
        "ungraded": dr.put(
            "grades.ungraded",
            "assets",
            ids([a for a in scored if a not in graded]),
            "Not graded: no format validator could read them",
        ),
        "overall": {},
        "by_format": {},
    }
    order = {g: i for i, g in enumerate(GRADES)}
    for g in GRADES:
        gs["overall"][g] = dr.put(
            f"grades.overall.{g}",
            "assets",
            ids(sorted([a for a in graded if a["grade"]["grade"] == g], key=lambda a: a["href"])),
            f"Assets graded {g}",
        )
    for grp in FORMAT_ORDER:
        al = [a for a in graded if group_of(a["format"]) == grp]
        if not al:
            continue
        gs["by_format"][grp] = {
            g: dr.put(
                f"grades.{grp}.{g}",
                "assets",
                ids([a for a in al if a["grade"]["grade"] == g]),
                f"{grp} assets graded {g}",
            )
            for g in GRADES
        }
    for a in scored:
        if a["grade"]:
            a["grade"]["drill"] = f"grades.unmet.{a['id']}"
            dr.put(
                a["grade"]["drill"],
                "findings",
                a["grade"]["unmet"],
                f"Why {a['key']} is {a['grade']['grade'] or 'ungraded'}: one level per item",
            )
    gs["ranked"] = ids(sorted(graded, key=lambda a: (order[a["grade"]["grade"]], a["href"])))
    s["grades"] = gs

    # Anti-patterns: general problems ranked by severity, so readers know where to start.
    aps = antipatterns.summarize(findings, {(a["catalog_id"], a["href"]): a["id"] for a in assets})
    for g in aps:
        p = f"antipatterns.{g['key']}"
        dr.put(f"{p}.findings", "findings", g["findings"], f"{g['title']}: findings")
        dr.put(f"{p}.assets", "assets", g["assets"], f"{g['title']}: affected assets")
        dr.put(
            f"{p}.must",
            "findings",
            [fp for fp in g["findings"] if fp in must_fps],
            f"{g['title']}: MUST failures",
        )
        dr.put(
            f"{p}.should",
            "findings",
            [fp for fp in g["findings"] if fp in should_fps],
            f"{g['title']}: SHOULD warnings",
        )
        for r in g["rules"]:
            r["drill"] = f"{p}.rule.{r['rule_id']}"
            dr.put(r["drill"], "findings", r["findings"], f"{g['title']}: {r['rule_id']}")
        g["drill"] = p
    s["anti_patterns"] = aps

    # Per format.
    by_format = {}
    groups: dict[str, list[dict]] = defaultdict(list)
    for a in scored:
        groups[group_of(a["format"])].append(a)
    for g in FORMAT_ORDER:
        if g not in groups:
            continue
        al = groups[g]
        hrefs = {(a["catalog_id"], a["href"]) for a in al}
        fs = [f for f in conf if (f["catalog_id"], f.get("asset_href")) in hrefs]
        p = f"by_format.{g}"
        v = {
            "assets": dr.put(f"{p}.assets", "assets", ids(al), f"{g}: scored assets"),
            "fully_conformant": dr.put(
                f"{p}.fully_conformant",
                "assets",
                ids([a for a in al if a["status"] == "pass"]),
                f"{g}: fully conformant assets",
            ),
            "unverified": dr.put(
                f"{p}.unverified",
                "assets",
                ids([a for a in al if a["status"] == "unverified"]),
                f"{g}: unverified assets",
            ),
            "errors": dr.put(
                f"{p}.errors",
                "findings",
                fps([f for f in fs if f["severity"] == "error"]),
                f"{g}: MUST failures",
            ),
            "warnings": dr.put(
                f"{p}.warnings",
                "findings",
                fps([f for f in fs if f["severity"] == "warning"]),
                f"{g}: SHOULD warnings",
            ),
        }
        v["pct"] = pct(v["fully_conformant"], v["assets"])
        by_format[g] = v

    # Per collection.
    keys = sorted(
        {(a["catalog_id"], a["collection"] or "") for a in assets}
        | {(f["catalog_id"], f.get("collection") or "") for f in findings}
        | {(c["catalog_id"], c.get("collection") or "") for c in checks}
    )
    collections = []
    for cat, col in keys:
        al = [a for a in assets if (a["catalog_id"], a["collection"] or "") == (cat, col)]
        sl = [a for a in al if a["scored"]]
        fs = [f for f in conf if (f["catalog_id"], f.get("collection") or "") == (cat, col)]
        cs = [c for c in checks if (c["catalog_id"], c.get("collection") or "") == (cat, col)]
        name = col or "(catalog level)"
        p = f"collections.{cat}/{col}"
        c = {"catalog_id": cat, "collection": col, "drill": p}
        c["assets"] = dr.put(f"{p}.assets", "assets", ids(al), f"{name}: all assets")
        c["scored_assets"] = dr.put(
            f"{p}.scored_assets", "assets", ids(sl), f"{name}: scored assets"
        )
        c["fully_conformant"] = dr.put(
            f"{p}.fully_conformant",
            "assets",
            ids([a for a in sl if a["status"] == "pass"]),
            f"{name}: fully conformant assets",
        )
        c["unverified"] = dr.put(
            f"{p}.unverified",
            "assets",
            ids([a for a in sl if a["status"] == "unverified"]),
            f"{name}: unverified assets",
        )
        for sev, key, lab in (
            ("error", "errors", "MUST failures"),
            ("warning", "warnings", "SHOULD warnings"),
            ("info", "infos", "info findings"),
        ):
            c[key] = dr.put(
                f"{p}.{key}",
                "findings",
                fps([f for f in fs if f["severity"] == sev]),
                f"{name}: {lab}",
            )
        c["checks"] = dr.put(f"{p}.checks", "checks", ids(cs), f"{name}: every check")
        c["checks_failed"] = dr.put(
            f"{p}.checks_failed",
            "checks",
            ids([x for x in cs if x["outcome"] in ("fail", "error")]),
            f"{name}: failed or errored checks",
        )
        # Collection-level checks (STAC object, docs, rashid rules) not tied to one asset.
        c["object_checks"] = dr.put(
            f"{p}.object_checks",
            "checks",
            ids([x for x in cs if not x.get("asset_href") and not x.get("parent")]),
            f"{name}: metadata checks (not tied to one asset)",
        )
        c["pct"] = pct(c["fully_conformant"], c["scored_assets"])
        collections.append(c)

    # Spec conformance.
    must = [f for f in conf if f["severity"] == "error"]
    declared_ids = set(declared.get("requirement_ids") or [])
    latest_ids = set(spec.get("requirement_ids") or [])
    sc_latest = dr.put(
        "spec_conformance.latest.must_failures",
        "findings",
        fps(must),
        f"MUST failures against the latest spec ({spec.get('version') or spec.get('ref')})",
    )
    if declared.get("requirements_available"):
        dm = [
            f
            for f in must
            if not f.get("spec_requirement_id") or f["spec_requirement_id"] in declared_ids
        ]
        sc_declared: int | None = dr.put(
            "spec_conformance.declared.must_failures",
            "findings",
            fps(dm),
            f"MUST failures against the declared spec ({declared.get('primary')}): "
            "findings whose requirement exists in that version",
        )
    else:
        sc_declared = None
    reqs = requirements or {}
    for sev in ("MUST", "SHOULD", "MAY"):
        dr.put(
            f"spec.requirement_counts.{sev}",
            "requirements",
            sorted(k for k, r in reqs.items() if r.get("severity") == sev),
            f"{sev} requirements in the latest spec",
        )
    added = sorted(latest_ids - declared_ids) if declared_ids else None
    if added is not None:
        dr.put(
            "spec_conformance.requirements_added_since_declared",
            "requirements",
            added,
            "Requirements added since the declared version",
        )

    s.update(
        {
            "by_format": by_format,
            "collections": collections,
            "spec_conformance": {
                "latest": {"version": spec.get("version"), "must_failures": sc_latest},
                "declared": {
                    "version": declared.get("primary"),
                    "must_failures": sc_declared,
                    "note": None
                    if sc_declared is not None
                    else "Requirements manifest for the declared version is not available, so conformance to it "
                    "could not be computed separately.",
                },
                "behind_latest": declared.get("behind_latest"),
                "requirements_added_since_declared": added,
            },
            "drill": dr.d,
        }
    )
    return s


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
