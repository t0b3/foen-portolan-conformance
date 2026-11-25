"""Hosting probe: range support, CORS for browser clients, content type, ETag.

Uses the shared probe (one HEAD + one 1 KiB ranged GET with an Origin header per asset).
"""

from __future__ import annotations

from ..formats import from_media_type
from ..http import OFFLINE
from .base import Adapter, Context, Probe

ORIGIN = "https://browser.portolan-sdi.org"
EXPOSE_WANTED = ("content-range", "content-length", "etag")


class Hosting(Adapter):
    name = "hosting-probe"
    key = "hosting"
    binary = None
    layer = "Hosting"

    def jobs(self, ctx: Context):
        if not ctx.crawl.root_url.startswith(("http://", "https://")):
            return []  # a local directory has no HTTP hosting to probe
        return [lambda: self.check_root(ctx)] + [
            (lambda a=a: self.check(ctx, a)) for a in ctx.crawl.assets
        ]

    def check_root(self, ctx: Context):
        r = ctx.fetcher.get(ctx.crawl.root_url, {"Origin": ORIGIN})
        out = []
        if ctx.fetcher.transport is not None:
            return [
                self.finding(
                    ctx,
                    "coverage-limit",
                    "info",
                    "Root CORS not probed: " + OFFLINE,
                    asset_href=ctx.crawl.root_url,
                )
            ]
        if not r.header("Access-Control-Allow-Origin"):
            out.append(
                self.finding(
                    ctx,
                    "CNC-HOST-010",
                    "warning",
                    "Root catalog has no CORS header (Access-Control-Allow-Origin): "
                    "browser clients such as the Portolan browser cannot read it",
                    asset_href=ctx.crawl.root_url,
                )
            )
        ct = (r.header("Content-Type") or "").lower()
        if r.ok and "json" not in ct:
            out.append(
                self.finding(
                    ctx,
                    "CNC-HOST-011",
                    "warning",
                    f"Root catalog served as '{ct or 'no content-type'}', expected JSON",
                    asset_href=ctx.crawl.root_url,
                )
            )
        return out

    def check(self, ctx: Context, asset):
        p: Probe | None = ctx.probes.get(asset.href)
        if p is None:
            return []
        f = lambda rule, sev, msg, **d: self.finding(ctx, rule, sev, msg, asset=asset, **d)
        out = []
        rng, head = p.range, p.head
        if rng is not None and rng.error == OFFLINE:
            return [f("coverage-limit", "info", "Hosting not probed: " + OFFLINE)]
        if rng is None or (
            rng.status in (0, 403, 404, 410) or (rng.status >= 400 and not (head and head.ok))
        ):
            status = (
                rng.error if rng is not None and rng.error else f"HTTP {rng.status if rng else '?'}"
            )
            return [f("CNC-HOST-000", "error", f"Asset not reachable anonymously ({status})")]
        scored = not ctx.is_ancillary(asset)
        if rng.status != 206:
            # Range support matters for cloud-native data, much less for a thumbnail.
            out.append(
                f(
                    "CNC-HOST-001",
                    "error" if scored else "info",
                    f"HTTP range request not honoured (got {rng.status}, expected 206)",
                )
            )
        if head is not None and head.ok and (head.header("Accept-Ranges") or "").lower() != "bytes":
            out.append(
                f(
                    "CNC-HOST-002",
                    "warning" if scored else "info",
                    "HEAD response lacks 'Accept-Ranges: bytes'",
                )
            )
        acao = rng.header("Access-Control-Allow-Origin")
        if not acao:
            out.append(
                f(
                    "CNC-HOST-003",
                    "warning",
                    "No Access-Control-Allow-Origin for a cross-origin request: browser "
                    "clients cannot read this asset",
                )
            )
        elif scored:
            exposed = {
                h.strip().lower()
                for h in (rng.header("Access-Control-Expose-Headers") or "").split(",")
            }
            missing = [h for h in EXPOSE_WANTED if h not in exposed and "*" not in exposed]
            if missing:
                out.append(
                    f(
                        "CNC-HOST-004",
                        "warning",
                        "Access-Control-Expose-Headers does not expose "
                        + ", ".join(missing)
                        + " (browser range readers need them)",
                        missing=missing,
                    )
                )
        served = (rng.header("Content-Type") or "").split(";")[0].strip().lower()
        declared = (asset.media_type or "").split(";")[0].strip().lower()
        if (
            declared
            and served
            and served != declared
            and from_media_type(served) != from_media_type(declared)
        ):
            out.append(
                f(
                    "CNC-HOST-005",
                    "warning" if scored else "info",
                    f"Served Content-Type '{served}' differs from the STAC asset type '{declared}'",
                )
            )
        if scored and not (rng.header("ETag") or (head and head.header("ETag"))):
            out.append(
                f(
                    "CNC-HOST-006",
                    "info",
                    "No ETag header (clients cannot detect changes between range reads)",
                )
            )
        return out
