"""The normalized finding model shared by every adapter."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any

SEVERITIES = ("error", "warning", "info")
_SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}

# Portolan requirement IDs, e.g. PORTO-CORE-012, PORTO-FMT-031
SPEC_ID_RE = re.compile(r"\bPORTO-[A-Z]+-\d{3}\b")

# Tool-level coverage categories (not conformance failures).
COVERAGE_RULES = {"tool-error", "tool-missing", "skipped-size", "coverage-limit", "skipped-mode"}


@dataclass(frozen=True)
class Finding:
    catalog_id: str
    tool: str
    rule_id: str
    severity: str
    message: str
    collection: str | None = None
    item: str | None = None
    asset_href: str | None = None
    format: str | None = None
    tool_version: str | None = None
    spec_requirement_id: str | None = None
    # Extra context (never part of the fingerprint).
    details: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)
    # Copy-paste shell command that reproduces this finding, and the check that produced it.
    reproduce: str | None = field(default=None, compare=False, hash=False)
    check_id: str | None = field(default=None, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self.severity not in _SEV_RANK:
            raise ValueError(f"bad severity {self.severity!r}")

    @property
    def is_coverage(self) -> bool:
        return self.rule_id in COVERAGE_RULES or self.rule_id == "PTL-GEN-002"

    @property
    def fingerprint(self) -> str:
        """Stable identity used for 'changes since last run'.

        Excludes tool_version and details so that a tool upgrade that reports the same
        problem does not show up as resolved + new.
        """
        key = "\x1f".join(
            str(x or "")
            for x in (
                self.catalog_id,
                self.collection,
                self.item,
                self.asset_href,
                self.tool,
                self.rule_id,
                self.severity,
                _normalize_msg(self.message),
            )
        )
        return hashlib.sha1(key.encode()).hexdigest()[:16]

    def sort_key(self) -> tuple:
        return (
            self.catalog_id,
            self.collection or "",
            self.item or "",
            self.asset_href or "",
            _SEV_RANK[self.severity],
            self.tool,
            self.rule_id,
            self.message,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        if not d["details"]:
            d.pop("details")
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


def _normalize_msg(msg: str) -> str:
    # Collapse whitespace; timings like "took 1.23s" would otherwise churn fingerprints.
    msg = re.sub(r"\s+", " ", msg.strip())
    return re.sub(r"\b\d+(\.\d+)?\s?(ms|s)\b", "<t>", msg)


def map_severity(raw: Any) -> str:
    """Map a tool's severity vocabulary to error|warning|info."""
    s = str(raw or "").strip().lower()
    if s in {"error", "err", "fail", "failed", "failure", "must", "critical", "fatal"}:
        return "error"
    if s in {"warning", "warn", "should", "warnings"}:
        return "warning"
    return "info"


def extract_spec_id(*texts: Any) -> str | None:
    for t in texts:
        if not t:
            continue
        m = SPEC_ID_RE.search(str(t))
        if m:
            return m.group(0)
    return None


def sort_findings(findings: list[Finding]) -> list[Finding]:
    # De-duplicate on fingerprint (keep first in sorted order) for deterministic output.
    seen: set[str] = set()
    out: list[Finding] = []
    for f in sorted(findings, key=Finding.sort_key):
        if f.fingerprint in seen:
            continue
        seen.add(f.fingerprint)
        out.append(f)
    return out


OUTCOMES = ("fail", "warn", "info", "pass", "skipped", "error")


@dataclass
class Check:
    """One check that ran (or was skipped), pass or fail, with the command to reproduce it.

    Tool invocations are parent checks; the individual tests they report (or that a native
    probe makes) are children with `parent` set.
    """

    catalog_id: str
    tool: str
    name: str
    outcome: str  # pass | fail | warn | info | skipped | error
    command: str | None = None
    tool_version: str | None = None
    target: str | None = None  # URL the check looked at
    collection: str | None = None
    item: str | None = None
    asset_href: str | None = None
    format: str | None = None
    evidence: str | None = None  # what was observed (header value, exit code, ...)
    parent: str | None = None
    findings: list[str] = field(default_factory=list)  # fingerprints

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"bad outcome {self.outcome!r}")

    @property
    def id(self) -> str:
        key = "\x1f".join(
            str(x or "")
            for x in (
                self.catalog_id,
                self.tool,
                self.name,
                self.target,
                self.collection,
                self.item,
                self.asset_href,
                self.parent,
            )
        )
        return "c" + hashlib.sha1(key.encode()).hexdigest()[:12]

    def sort_key(self) -> tuple:
        return (
            self.catalog_id,
            self.collection or "",
            self.item or "",
            self.asset_href or "",
            self.tool,
            self.parent or "",
            self.name,
            self.target or "",
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        return d


def outcome_of(findings: list[Finding]) -> str:
    rules = {f.rule_id for f in findings}
    if rules & {"tool-error"}:
        return "error"
    if rules & {"tool-missing", "skipped-size", "skipped-mode"}:
        return "skipped"
    sev = {f.severity for f in findings if not f.is_coverage}
    if "error" in sev:
        return "fail"
    if "warning" in sev:
        return "warn"
    if sev or rules & {"coverage-limit"}:
        return "info"
    return "pass"
