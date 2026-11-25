"""Soft rating of GeoParquet assets from geoparquet-io (`gpio check`) output.

The rating does not change conformance (MUST/SHOULD findings stay the authority). It ranks
how well a GeoParquet file follows the spec and cloud-native best practice, so an asset that
is conformant but slow to query can be told apart from a well-optimized one.

Method (shown next to every score in the report):
- every individual check gpio reports counts: pass = 1, warn = 0.5, fail = 0 (info is ignored)
- spec checks (`gpio check spec`) weigh 2, best-practice checks (`gpio check all`) weigh 1
- score = 100 * weighted mean, rounded to one decimal
- grade: A >= 90, B >= 75, C >= 60, D >= 40, E below
- if gpio reported no individual checks, its exit code stands in for one check
  (0 pass, 2 warn, 1 fail) so a run is never silently unrated
- `gpio check optimization` (if this gpio has it) is shown beside the score, not mixed in
- grade A is reserved for files that meet *every* gpio recommendation (`gpio check all`
  reports no warning and no failure) *and* are Parquet format v2 (FileMetaData.version = 2,
  read from the footer). Otherwise, or if either cannot be confirmed, the best grade is B:
  the score is unchanged, the grade is capped, and `cap` says why
"""

from __future__ import annotations

VALUE = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
WEIGHT = {"spec": 2.0, "all": 1.0}
GRADES = [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "E")]
EXIT_OUTCOME = {0: "pass", 2: "warn", 1: "fail"}
METHOD = (
    "pass=1, warn=0.5, fail=0; spec checks weigh 2, best-practice checks 1; "
    "A>=90, B>=75, C>=60, D>=40, else E; A only if every gpio recommendation is met "
    "and the file is Parquet v2, otherwise at best B"
)


def grade(score: float) -> str:
    return next(g for t, g in GRADES if score >= t)


def rate(
    parts: dict[str, tuple],
    optimization: float | None = None,
    parquet_version: int | None = None,
    parquet_check_id: str | None = None,
) -> dict | None:
    """parts: sub-command ("spec" | "all") -> (child checks, exit code or None if it did not run,
    [id of the sub-command's own check]).

    Child checks need `.id` and `.outcome`. Every point in the score is backed by one check id
    (`check_ids`), so `checks_rated == len(check_ids)`. Returns None when gpio did not run.
    `parquet_version` is FileMetaData.version from the footer (None = could not be read).
    """
    total_w = total_v = 0.0
    sub_scores: dict[str, float | None] = {}
    counts = {"pass": 0, "warn": 0, "fail": 0}
    used: list[str] = []
    ran = False
    for sub, (children, rc, *own) in parts.items():
        children = list(children)
        if rc is None:
            sub_scores[sub] = None
            continue
        ran = True
        w = WEIGHT.get(sub, 1.0)
        rated = [c for c in children if c.outcome in VALUE]
        if not rated and rc in EXIT_OUTCOME:
            vals = [VALUE[EXIT_OUTCOME[rc]]]
            counts[EXIT_OUTCOME[rc]] += 1
            if own:
                used.append(own[0])
        else:
            vals = [VALUE[c.outcome] for c in rated]
            for c in rated:
                counts[c.outcome] += 1
                used.append(c.id)
        if vals:
            sub_scores[sub] = round(100 * sum(vals) / len(vals), 1)
            total_w += w * len(vals)
            total_v += w * sum(vals)
        else:
            sub_scores[sub] = None
    if not ran or total_w == 0:
        return None
    score = round(100 * total_v / total_w, 1)

    # Grade A needs every gpio recommendation met and Parquet v2; otherwise at best B.
    rec_children, rec_rc, *rec_own = parts.get("all", ((), None))
    rec_rated = [c for c in rec_children if c.outcome in VALUE]
    if rec_rc is None:
        recs_met, unmet = None, []
    elif rec_rated:
        unmet = [c.id for c in rec_rated if c.outcome != "pass"]
        recs_met = not unmet
    else:  # no itemised output: the exit code decides
        recs_met = rec_rc == 0
        unmet = [] if recs_met else list(rec_own[:1])
    cap: list[str] = []
    if recs_met is None:
        cap.append("gpio recommendations not checked (`gpio check all` did not run)")
    elif not recs_met:
        cap.append(f"{len(unmet) or 1} gpio recommendation(s) not met")
    if parquet_version is None:
        cap.append("Parquet format version could not be read from the footer")
    elif parquet_version != 2:
        cap.append(f"Parquet format v{parquet_version}, not v2")
    uncapped = grade(score)
    final = "B" if uncapped == "A" and cap else uncapped
    return {
        "score": score,
        "grade": final,
        "grade_uncapped": uncapped,
        "cap": cap if uncapped == "A" else [],
        "max_grade": "B" if cap else "A",
        "a_conditions": cap,  # why A is out of reach (empty = A possible)
        "recommendations_met": recs_met,
        "unmet_recommendation_ids": unmet,
        "parquet_format_version": parquet_version,
        "parquet_check_id": parquet_check_id,
        "spec_score": sub_scores.get("spec"),
        "best_practice_score": sub_scores.get("all"),
        "optimization_score": optimization,
        "checks_rated": sum(counts.values()),
        "counts": counts,
        "check_ids": used,
        "method": METHOD,
    }
