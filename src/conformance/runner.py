"""Orchestrates one run: resolve spec -> crawl -> probe -> detect -> adapters -> findings."""

from __future__ import annotations

import datetime as dt
import platform
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import __version__
from .adapters import ALL_ADAPTERS, Adapter, Context, Probe
from .adapters.hosting import ORIGIN
from .config import Config
from .crawl import CrawlError, CrawlResult, crawl, declared_portolan_versions
from .formats import detect
from .http import Fetcher
from .normalize import Finding, sort_findings
from .spec import SpecInfo, compare_versions, load_requirements, resolve_spec
from .toolchain import version


@dataclass
class RunOutput:
    started: str
    finished: str | None = None
    mode: str = "full"
    spec: SpecInfo | None = None
    declared: dict = field(default_factory=dict)
    catalogs: list[dict] = field(default_factory=list)
    crawls: list[CrawlResult] = field(default_factory=list)
    contexts: list[Context] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    tool_versions: dict[str, str | None] = field(default_factory=dict)
    coverage: list[dict] = field(default_factory=list)
    infra_errors: list[str] = field(default_factory=list)


def _now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def execute(
    config: Config,
    fetcher: Fetcher,
    mode: str = "full",
    catalog_ids: list[str] | None = None,
    spec: SpecInfo | None = None,
    log=print,
) -> RunOutput:
    out = RunOutput(started=_now(), mode=mode)
    out.spec = spec or resolve_spec(
        fetcher,
        config.spec["repo"],
        config.spec["requirements_path"],
        config.spec.get("ref", "latest-release"),
    )
    log(f"spec: {out.spec.repo}@{out.spec.ref} ({out.spec.source}) {out.spec.counts}")
    adapters = [cls() for cls in ALL_ADAPTERS]
    out.tool_versions = _tool_versions(adapters)

    for cat in config.catalogs:
        if catalog_ids and cat.id not in catalog_ids:
            continue
        log(f"[{cat.id}] crawling {cat.url}")
        try:
            cr = crawl(cat, fetcher, int(config.limits["max_items_per_collection"]))
        except CrawlError as e:
            out.infra_errors.append(f"{cat.id}: {e}")
            out.catalogs.append({"id": cat.id, "url": cat.url, "error": str(e)})
            continue
        out.crawls.append(cr)
        ctx = Context(
            config=config,
            fetcher=fetcher,
            crawl=cr,
            mode=mode,
            workdir=tempfile.mkdtemp(prefix=f"conf-{cat.id}-"),
        )
        out.contexts.append(ctx)
        log(
            f"[{cat.id}] {len(cr.collections)} collections, {len(cr.items)} items, {len(cr.assets)} assets"
        )
        if mode == "full":
            _probe_assets(ctx, int(config.limits["concurrency"]))
        for a in cr.assets:
            p = ctx.probes.get(a.href)
            ctx.formats[a.href] = detect(a.href, a.media_type, p.first_bytes if p else None)
        findings = list(cr.findings)
        findings += _run_adapters(ctx, adapters, out, int(config.limits["concurrency"]), log)
        out.findings += findings
        out.catalogs.append(
            {
                "id": cat.id,
                "url": cat.url,
                "browser": cat.browser,
                "etag": cr.root_etag,
                "last_modified": cr.root_last_modified,
                "title": (cr.root or {}).get("title"),
                "collections": len(cr.collections),
                "items": len(cr.items),
                "assets": len(cr.assets),
                "skipped_collections": sorted(cr.skipped_collections),
            }
        )

    # Declared vs latest spec.
    declared: dict[str, list[str]] = {}
    for cr in out.crawls:
        for v, urls in declared_portolan_versions(cr.objects).items():
            declared.setdefault(v, []).extend(urls)
    primary = max(declared, key=lambda v: len(declared[v])) if declared else None
    declared_reqs = None
    if primary:
        declared_reqs = load_requirements(
            fetcher, out.spec.repo, f"v{primary}", config.spec["requirements_path"]
        )
    out.declared = {
        "versions": {v: len(u) for v, u in sorted(declared.items())},
        "primary": primary,
        "behind_latest": bool(
            primary and out.spec.version and compare_versions(primary, out.spec.version) < 0
        ),
        "requirements_available": declared_reqs is not None,
        "requirement_ids": sorted(declared_reqs) if declared_reqs else [],
        "requirement_counts": _counts(declared_reqs) if declared_reqs else None,
    }
    out.findings = sort_findings(out.findings)
    out.finished = _now()
    return out


def _counts(reqs: dict) -> dict:
    c = {"MUST": 0, "SHOULD": 0, "MAY": 0}
    for r in reqs.values():
        c[r["severity"]] = c.get(r["severity"], 0) + 1
    return c


def _probe_assets(ctx: Context, workers: int) -> None:
    def probe(href: str) -> tuple[str, Probe]:
        head = ctx.fetcher.head(href)
        rng = ctx.fetcher.get_range(href, 0, 1023, {"Origin": ORIGIN})
        size = None
        cl = head.header("Content-Length") if head.ok else None
        if cl and cl.isdigit():
            size = int(cl)
        else:
            cr = rng.header("Content-Range") or ""
            if "/" in cr and cr.rsplit("/", 1)[1].isdigit():
                size = int(cr.rsplit("/", 1)[1])
        return href, Probe(head=head, range=rng, size=size)

    hrefs = sorted({a.href for a in ctx.crawl.assets})
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for href, p in ex.map(probe, hrefs):
            ctx.probes[href] = p


def _run_adapters(
    ctx: Context, adapters: list[Adapter], out: RunOutput, workers: int, log
) -> list[Finding]:
    jobs: list[tuple[Adapter, object]] = []
    for ad in adapters:
        if not ctx.config.tool_enabled(ad.key):
            out.coverage.append(
                {"catalog_id": ctx.catalog_id, "tool": ad.name, "reason": "disabled in config.yaml"}
            )
            continue
        if ctx.mode == "light" and not ad.light:
            out.coverage.append(
                {
                    "catalog_id": ctx.catalog_id,
                    "tool": ad.name,
                    "reason": "lightweight run (metadata and STAC only)",
                }
            )
            continue
        try:
            ad_jobs = ad.jobs(ctx)
        except Exception as e:  # an adapter bug must not kill the run
            jobs.append((ad, _raise(e)))
            continue
        if not ad_jobs:
            continue
        if not ad.available():
            jobs.append(
                (
                    ad,
                    lambda ad=ad, n=len(ad_jobs): [
                        ad.finding(
                            ctx,
                            "tool-missing",
                            "info",
                            f"{ad.name} is not installed; {n} check(s) not run",
                        )
                    ],
                )
            )
            continue
        jobs += [(ad, j) for j in ad_jobs]

    log(f"[{ctx.catalog_id}] {len(jobs)} adapter jobs")

    def go(pair):
        ad, job = pair
        try:
            return job()
        except Exception as e:
            tb = traceback.format_exception_only(type(e), e)[-1].strip()
            return [ad.finding(ctx, "tool-error", "info", f"{ad.name} adapter crashed: {tb}")]

    results: list[Finding] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for fs in ex.map(go, jobs):
            results += fs
    return results


def _raise(e: Exception):
    def f():
        raise e

    return f


def _tool_versions(adapters: list[Adapter]) -> dict[str, str | None]:
    v: dict[str, str | None] = {
        "foen-portolan-conformance": __version__,
        "python": platform.python_version(),
    }
    for ad in adapters:
        try:
            v[ad.name] = ad.version() if ad.available() else None
        except Exception:
            v[ad.name] = None
    v["uv"] = version("uv")
    v["gdal"] = version("gdalinfo")
    return dict(sorted(v.items()))
