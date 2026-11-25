"""Load and validate config.yaml."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CatalogConfig:
    id: str
    url: str
    browser: str | None = None
    include: list[str] = field(default_factory=lambda: ["*"])
    exclude: list[str] = field(default_factory=list)

    def wants(self, collection_id: str) -> bool:
        if not any(fnmatch.fnmatch(collection_id, p) for p in self.include):
            return False
        return not any(fnmatch.fnmatch(collection_id, p) for p in self.exclude)


@dataclass
class Config:
    catalogs: list[CatalogConfig]
    spec: dict[str, Any]
    limits: dict[str, Any]
    checks: dict[str, Any]

    @property
    def max_asset_bytes(self) -> int:
        return int(float(self.limits.get("max_asset_size_gb", 2)) * 1024**3)

    def tool_enabled(self, name: str) -> bool:
        return bool(self.checks.get("tools", {}).get(name, True))


DEFAULTS: dict[str, Any] = {
    "spec": {
        "repo": "portolan-sdi/portolan-spec",
        "requirements_path": "specs/portolan/requirements.yaml",
        "ref": "latest-release",
    },
    "limits": {
        "max_asset_size_gb": 2,
        "concurrency": 8,
        "http_timeout_s": 30,
        "http_retries": 3,
        "tool_timeout_s": 900,
        "max_items_per_collection": 5000,
    },
    "checks": {
        "non_cloud_native_severity": "warning",
        "ancillary_roles": ["thumbnail", "overview", "style", "metadata", "documentation"],
        "docs": {
            "root": ["README.md", "AGENTS.md", "llms.txt"],
            "collection": ["README.md", "AGENTS.md"],
            "severity": "warning",
        },
        "tools": {},
    },
}


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    cats = raw.get("catalogs") or []
    if not cats:
        raise ValueError("config.yaml: 'catalogs' must list at least one catalog")
    ids = [c.get("id") for c in cats]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("config.yaml: every catalog needs a unique 'id'")
    catalogs = [
        CatalogConfig(
            id=c["id"],
            url=c["url"],
            browser=c.get("browser"),
            include=list(c.get("include") or ["*"]),
            exclude=list(c.get("exclude") or []),
        )
        for c in cats
    ]
    return Config(
        catalogs=catalogs,
        spec={**DEFAULTS["spec"], **(raw.get("spec") or {})},
        limits={**DEFAULTS["limits"], **(raw.get("limits") or {})},
        checks=_deep_merge(DEFAULTS["checks"], raw.get("checks") or {}),
    )


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = (
            _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
        )
    return out
