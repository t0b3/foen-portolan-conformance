"""Resolve the 'latest' Portolan spec at run time and load its requirements manifest."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

from .http import Fetcher

API = "https://api.github.com/repos/{repo}"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
BLOB = "https://github.com/{repo}/blob/{ref}/{file}"


@dataclass
class SpecInfo:
    repo: str
    ref: str  # tag or branch actually used
    version: str | None  # e.g. "0.3.0"
    sha: str | None
    source: str  # latest-release | main-fallback | pinned | unavailable
    requirements: dict[str, dict] = field(default_factory=dict)
    note: str | None = None

    @property
    def counts(self) -> dict[str, int]:
        c = {"MUST": 0, "SHOULD": 0, "MAY": 0}
        for r in self.requirements.values():
            sev = str(r.get("severity", "")).upper()
            c[sev] = c.get(sev, 0) + 1
        return c

    def link(self, req_id: str) -> str | None:
        r = self.requirements.get(req_id)
        if not r or not r.get("file"):
            return None
        return BLOB.format(repo=self.repo, ref=self.sha or self.ref, file=r["file"])

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "ref": self.ref,
            "version": self.version,
            "commit_sha": self.sha,
            "source": self.source,
            "requirement_counts": self.counts,
            "note": self.note,
        }


def _gh_headers() -> dict[str, str]:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    h = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def resolve_spec(fetcher: Fetcher, repo: str, path: str, ref: str = "latest-release") -> SpecInfo:
    source, note = "pinned", None
    if ref == "latest-release":
        r = fetcher.get(API.format(repo=repo) + "/releases/latest", _gh_headers())
        if r.ok:
            ref, source = r.json()["tag_name"], "latest-release"
        else:
            ref, source = "main", "main-fallback"
            note = f"No release found (HTTP {r.status}); using the main branch."
    sha = None
    r = fetcher.get(API.format(repo=repo) + f"/commits/{ref}", _gh_headers())
    if r.ok:
        sha = r.json().get("sha")
    reqs = load_requirements(fetcher, repo, ref, path)
    if reqs is None:
        return SpecInfo(
            repo, ref, _ver(ref), sha, "unavailable", {}, f"Could not read {path} at {ref}."
        )
    return SpecInfo(repo, ref, _ver(ref), sha, source, reqs, note)


def load_requirements(fetcher: Fetcher, repo: str, ref: str, path: str) -> dict[str, dict] | None:
    r = fetcher.get(RAW.format(repo=repo, ref=ref, path=path))
    if not r.ok:
        return None
    return parse_requirements(r.body.decode("utf-8"))


def parse_requirements(text: str) -> dict[str, dict]:
    doc = yaml.safe_load(text) or {}
    entries = doc.get("requirements", doc if isinstance(doc, list) else [])
    out: dict[str, dict] = {}
    for e in entries or []:
        if isinstance(e, dict) and e.get("id"):
            out[str(e["id"])] = {
                "severity": str(e.get("severity", "")).upper(),
                "file": e.get("file"),
                "quote": " ".join(str(e.get("quote", "")).split()),
                "enforcement": e.get("enforcement"),
            }
    return out


def _ver(ref: str) -> str | None:
    return ref[1:] if ref.startswith("v") and ref[1:2].isdigit() else None


def compare_versions(a: str | None, b: str | None) -> int:
    """-1 if a<b, 0 if equal, 1 if a>b. Unknown sorts lowest."""

    def key(v):
        if not v:
            return (-1,)
        return tuple(int(p) if p.isdigit() else 0 for p in v.split("-")[0].split("."))

    ka, kb = key(a), key(b)
    return (ka > kb) - (ka < kb)
