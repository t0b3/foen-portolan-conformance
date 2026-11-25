"""Adapter contract. Each adapter turns one tool's output into normalized findings."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from typing import Any

from .. import repro
from ..config import Config
from ..crawl import Asset, CrawlResult, StacObject
from ..http import Fetcher, Response
from ..normalize import Check, Finding, extract_spec_id, map_severity, outcome_of
from ..toolchain import RunResult


@dataclass
class Probe:
    """HEAD + first-KiB range read of one asset, shared by every adapter."""

    head: Response | None = None
    range: Response | None = None
    size: int | None = None

    @property
    def first_bytes(self) -> bytes:
        if self.range is not None and self.range.status in (200, 206):
            return self.range.body[:4096]
        return b""


@dataclass
class Context:
    config: Config
    fetcher: Fetcher
    crawl: CrawlResult
    mode: str = "full"  # full | light
    probes: dict[str, Probe] = field(default_factory=dict)
    formats: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )  # href -> (format, detected_by)
    workdir: str | None = None
    # href -> tools that actually validated the asset's bytes (an asset nobody validated is
    # "unverified", never "conformant").
    verified: dict[str, set[str]] = field(default_factory=dict)
    # Every check that ran or was skipped, pass or fail (list.append is thread-safe).
    checks: list[Check] = field(default_factory=list)

    @property
    def catalog_id(self) -> str:
        return self.crawl.catalog.id

    def too_big(self, asset: Asset) -> bool:
        p = self.probes.get(asset.href)
        return bool(p and p.size and p.size > self.config.max_asset_bytes)

    def fmt(self, asset: Asset) -> str:
        return self.formats.get(asset.href, ("unknown", "unknown"))[0]

    def is_ancillary(self, asset: Asset) -> bool:
        from ..formats import ANCILLARY_FORMATS

        roles = set(asset.roles)
        anc = set(self.config.checks.get("ancillary_roles", []))
        if roles and roles <= anc:
            return True
        return not (roles & {"data", "tiles"}) and self.fmt(asset) in ANCILLARY_FORMATS

    def assets_of(self, *formats: str) -> list[Asset]:
        return [a for a in self.crawl.assets if self.fmt(a) in formats and not self.is_ancillary(a)]

    def locate(self, ref: str | None) -> tuple[str | None, str | None, str | None]:
        """Map a URL or relative path reported by a tool to (collection, item, asset_href)."""
        if not ref:
            return None, None, None
        ref = str(ref)
        for a in self.crawl.assets:
            if ref == a.href or (
                not ref.startswith("http") and a.href.endswith("/" + ref.lstrip("./"))
            ):
                return a.collection, a.item, a.href
        best: StacObject | None = None
        for o in self.crawl.objects:
            if ref == o.url or (
                not ref.startswith("http") and o.url.endswith("/" + ref.lstrip("./"))
            ):
                best = o
                break
        if best is None:
            # A directory-style path: pick the deepest object whose folder prefixes it.
            for o in self.crawl.objects:
                folder = o.url.rsplit("/", 1)[0]
                rel = folder.split("/")[-1]
                if ref.startswith(rel + "/") or ref.startswith(folder):
                    best = o
        if best is None:
            return None, None, ref if ref.startswith("http") else None
        item = best.id if best.kind == "Feature" else None
        return best.collection, item, None


Job = Callable[[], list[Finding]]


class Adapter:
    name: str = "adapter"  # tool name used in findings
    key: str = ""  # config.checks.tools key
    binary: str | None = None
    layer: str = ""
    light: bool = False  # runs in the lightweight daily mode
    # True if a clean run means the asset's bytes were validated as its format. Header-only
    # probes (e.g. the Parquet footer version) set False so they never make an asset "verified".
    verifies: bool = True
    # What the adapter runs on, used to log "not run" checks per dataset when the tool is missing.
    scope: str = "catalog"  # catalog | object | asset
    formats: tuple[str, ...] = ()
    install: str = ""

    def example_cmd(self, url: str) -> list[str]:
        return [self.binary or self.name, url]

    def missing(self, ctx: Context, reason: str, rule: str = "tool-missing") -> list[Finding]:
        """Record one skipped check per dataset this adapter would have checked."""
        hint = f"# {self.name}: {reason}" + (f"\n# install: {self.install}" if self.install else "")
        out: list[Finding] = []
        if self.scope == "asset":
            for a in ctx.assets_of(*self.formats) if self.formats else ctx.crawl.assets:
                out += self.record(
                    ctx,
                    f"{self.name} (not run)",
                    [self.finding(ctx, rule, "info", f"{self.name}: {reason}", asset=a)],
                    command=repro.lines(hint, repro.tool(self.example_cmd(a.href), None)),
                    asset=a,
                    outcome="skipped",
                )
        elif self.scope == "object":
            for o in ctx.crawl.objects:
                item = o.id if o.kind == "Feature" else None
                out += self.record(
                    ctx,
                    f"{self.name} (not run)",
                    [
                        self.finding(
                            ctx,
                            rule,
                            "info",
                            f"{self.name}: {reason}",
                            collection=o.collection,
                            item=item,
                            asset_href=None,
                        )
                    ],
                    command=repro.lines(hint, repro.tool(self.example_cmd(o.url), None)),
                    target=o.url,
                    collection=o.collection,
                    item=item,
                    outcome="skipped",
                )
        else:
            url = ctx.crawl.root_url
            out += self.record(
                ctx,
                f"{self.name} (not run)",
                [self.finding(ctx, rule, "info", f"{self.name}: {reason}")],
                command=repro.lines(hint, repro.tool(self.example_cmd(url), None)),
                target=url,
                outcome="skipped",
            )
        return out

    def available(self) -> bool:
        from ..toolchain import which

        return self.binary is None or which(self.binary) is not None

    def version(self) -> str | None:
        from .. import __version__
        from ..toolchain import version

        return version(self.binary) if self.binary else f"native-{__version__}"

    def jobs(self, ctx: Context) -> list[Job]:  # pragma: no cover - interface
        raise NotImplementedError

    # -- helpers --------------------------------------------------------------------------
    def per_asset(
        self, ctx: Context, formats: tuple[str, ...], fn, header_only: bool = False
    ) -> list[Job]:
        """One job per matching asset; assets above the size cap get a 'skipped-size' note."""
        jobs: list[Job] = []
        for a in ctx.assets_of(*formats):
            if ctx.too_big(a) and not header_only:
                size = ctx.probes[a.href].size or 0
                jobs.append(
                    lambda a=a, size=size: self.record(
                        ctx,
                        f"{self.name} data checks",
                        [
                            self.finding(
                                ctx,
                                "skipped-size",
                                "info",
                                f"skipped: size ({size / 1024**3:.2f} GB > "
                                f"{ctx.config.limits['max_asset_size_gb']} GB cap); only header checks ran",
                                asset=a,
                            )
                        ],
                        command=repro.head(a.href),
                        asset=a,
                        evidence=f"Content-Length: {size}",
                    )
                )
            else:
                jobs.append(lambda a=a: self._verify(ctx, a, fn(a)))
        return jobs

    def _verify(self, ctx: Context, asset: Asset, result: list[Finding] | None) -> list[Finding]:
        """Adapters return None when they could not look at the asset at all."""
        if result is None:
            return []
        if self.verifies and not any(f.rule_id in ("tool-error", "coverage-limit") for f in result):
            ctx.verified.setdefault(asset.href, set()).add(self.name)
        return result

    def record(
        self,
        ctx: Context,
        name: str,
        findings: list[Finding],
        *,
        command: str | None,
        asset: Asset | None = None,
        collection: str | None = None,
        item: str | None = None,
        target: str | None = None,
        evidence: str | None = None,
        outcome: str | None = None,
        parent: str | None = None,
    ) -> list[Finding]:
        """Log one check (pass or fail) and stamp its findings with the reproduce command."""
        c = self.make_check(
            ctx,
            name,
            command=command,
            asset=asset,
            collection=collection,
            item=item,
            target=target,
            evidence=evidence,
            parent=parent,
            outcome=outcome or outcome_of(findings),
        )
        out = [
            replace(f, reproduce=f.reproduce or command, check_id=f.check_id or c.id)
            for f in findings
        ]
        c.findings = sorted({f.fingerprint for f in out})
        ctx.checks.append(c)
        return out

    def make_check(
        self,
        ctx: Context,
        name: str,
        *,
        command: str | None,
        asset: Asset | None = None,
        collection: str | None = None,
        item: str | None = None,
        target: str | None = None,
        evidence: str | None = None,
        parent: str | None = None,
        outcome: str = "pass",
    ) -> Check:
        href = None
        fmt = None
        if asset is not None:
            collection, item, href = asset.collection, asset.item, asset.href
            target = target or asset.href
            fmt = ctx.fmt(asset)
        return Check(
            catalog_id=ctx.catalog_id,
            tool=self.name,
            tool_version=self.version(),
            name=name,
            outcome=outcome,
            command=command,
            target=target,
            collection=collection,
            item=item,
            asset_href=href,
            format=fmt,
            evidence=evidence,
            parent=parent,
        )

    def record_object(
        self,
        ctx: Context,
        obj: StacObject,
        findings: list[Finding],
        cmd: list[str],
        name: str | None = None,
    ) -> list[Finding]:
        """Record a check that ran on one STAC object (catalog, collection or item)."""
        return self.record(
            ctx,
            name or f"{self.name} {obj.kind.lower()}",
            findings,
            command=self.tool_cmd(cmd),
            target=obj.url,
            collection=obj.collection,
            item=obj.id if obj.kind == "Feature" else None,
        )

    def tool_cmd(self, cmd: list[str]) -> str:
        return repro.tool(cmd, self.version())

    def finding(
        self,
        ctx: Context,
        rule_id: str,
        severity: str,
        message: str,
        *,
        asset: Asset | None = None,
        collection: str | None = None,
        item: str | None = None,
        asset_href: str | None = None,
        fmt: str | None = None,
        spec_id: str | None = None,
        **details: Any,
    ) -> Finding:
        if asset is not None:
            collection, item, asset_href = asset.collection, asset.item, asset.href
            fmt = fmt or ctx.fmt(asset)
        return Finding(
            catalog_id=ctx.catalog_id,
            tool=self.name,
            tool_version=self.version(),
            rule_id=rule_id,
            severity=severity,
            message=message.strip(),
            collection=collection,
            item=item,
            asset_href=asset_href,
            format=fmt,
            spec_requirement_id=spec_id or extract_spec_id(rule_id, message),
            details={k: v for k, v in details.items() if v is not None},
        )

    def tool_error(self, ctx: Context, r: RunResult, target: str, **kw) -> Finding:
        what = "timed out" if r.timed_out else f"exited with code {r.returncode}"
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        return self.finding(
            ctx,
            "tool-error",
            "info",
            f"{self.name} {what} on {target}: {' | '.join(tail)[:400]}",
            **kw,
        )


def worst(outcomes: list[str]) -> str:
    order = ["error", "fail", "warn", "info", "skipped", "pass"]
    return min(outcomes or ["pass"], key=order.index)


def parse_json_loose(text: str) -> Any | None:
    """Parse JSON even if a tool prints banners before/after it."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = text.find(opener), text.rfind(closer)
        if 0 <= i < j:
            try:
                return json.loads(text[i : j + 1])
            except ValueError:
                continue
    return None


_STATUS_KEYS = ("status", "result", "level", "severity")
_BOOL_KEYS = ("passed", "pass", "ok", "valid", "success")
_NAME_KEYS = ("name", "check", "id", "rule", "title", "key")
_MSG_KEYS = ("message", "msg", "detail", "details", "description", "error")


def walk_checks(obj: Any, path: str = "") -> Iterator[tuple[str, str, str]]:
    """Yield (name, status, message) for every check-like dict in a nested JSON report.

    status is one of pass|fail|warn|info. Used for tools whose JSON layout is not pinned.
    """
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_checks(v, f"{path}[{i}]")
        return
    if not isinstance(obj, dict):
        return
    status = None
    for k in _STATUS_KEYS:
        if isinstance(obj.get(k), str):
            s = obj[k].lower()
            status = (
                "pass"
                if s in {"pass", "passed", "ok", "success", "valid"}
                else "fail"
                if s in {"fail", "failed", "error", "invalid", "critical"}
                else "warn"
                if s.startswith("warn")
                else "info"
            )
            break
    if status is None:
        for k in _BOOL_KEYS:
            if isinstance(obj.get(k), bool):
                status = "pass" if obj[k] else "fail"
                break
    if status is not None:
        name = next((str(obj[k]) for k in _NAME_KEYS if obj.get(k)), path.strip(".") or "check")
        msg = next((str(obj[k]) for k in _MSG_KEYS if isinstance(obj.get(k), str) and obj[k]), "")
        yield name, status, msg
    for k, v in obj.items():
        if isinstance(v, dict | list):
            yield from walk_checks(v, f"{path}.{k}")


_TEXT_FAIL = re.compile(r"^\s*(?:[✗✘❌×]|\[?FAIL\]?|ERROR)\s*:?\s*(.+)$", re.I)
_TEXT_PASS = re.compile(r"^\s*(?:[✓✔✅]|\[?PASS\]?|OK)\s*:?\s*(.+)$", re.I)
_TEXT_WARN = re.compile(r"^\s*(?:[⚠!]️?|\[?WARN(?:ING)?\]?)\s*:?\s*(.+)$", re.I)


def text_checks(text: str) -> Iterator[tuple[str, str]]:
    """Yield (status, line) from human-oriented CLI output using ✓/✗/⚠ markers."""
    for line in text.splitlines():
        if m := _TEXT_PASS.match(line):
            yield "pass", m.group(1).strip()
        elif m := _TEXT_FAIL.match(line):
            yield "fail", m.group(1).strip()
        elif m := _TEXT_WARN.match(line):
            yield "warn", m.group(1).strip()


def sev_from_status(status: str) -> str:
    return {"fail": "error", "warn": "warning"}.get(status, map_severity(status))
