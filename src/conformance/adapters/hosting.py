"""Hosting probe: range support, CORS for browser clients, content type, ETag.

Uses the shared probe (one HEAD + one 1 KiB ranged GET with an Origin header per asset).
Every sub-check is logged with the header value that was observed, and the curl command
that shows the same headers.
"""

from __future__ import annotations

from .. import repro
from ..formats import from_media_type
from ..http import OFFLINE
from .base import Adapter, Context, Probe, worst

ORIGIN = repro.ORIGIN
EXPOSE_WANTED = ("content-range", "content-length", "etag")


class Hosting(Adapter):
    name = "hosting-probe"
    key = "hosting"
    binary = None
    layer = "Hosting"
    scope = "asset"

    def example_cmd(self, url):
        return [
            "curl",
            "-sS",
            "-D",
            "-",
            "-o",
            "/dev/null",
            "-H",
            f"Origin: {ORIGIN}",
            "-H",
            "Range: bytes=0-1023",
            url,
        ]

    def jobs(self, ctx: Context):
        if not ctx.crawl.root_url.startswith(("http://", "https://")):
            return []  # a local directory has no HTTP hosting to probe
        return [lambda: self.check_root(ctx)] + [
            (lambda a=a: self.check(ctx, a)) for a in ctx.crawl.assets
        ]

    def check_root(self, ctx: Context):
        url = ctx.crawl.root_url
        cmd = repro.lines(
            f"curl -sS -D - -o /dev/null -H {repro.q('Origin: ' + ORIGIN)} {repro.q(url)}"
        )
        if ctx.fetcher.transport is not None:
            return self.record(
                ctx,
                "root catalog CORS",
                [
                    self.finding(
                        ctx,
                        "coverage-limit",
                        "info",
                        "Root CORS not probed: " + OFFLINE,
                        asset_href=url,
                    )
                ],
                command=cmd,
                target=url,
                outcome="skipped",
            )
        r = ctx.fetcher.get(url, {"Origin": ORIGIN})
        out = []
        acao = r.header("Access-Control-Allow-Origin")
        out += self.record(
            ctx,
            "root catalog CORS",
            []
            if acao
            else [
                self.finding(
                    ctx,
                    "CNC-HOST-010",
                    "warning",
                    "Root catalog has no CORS header (Access-Control-Allow-Origin): browser clients such as the "
                    "Portolan browser cannot read it",
                    asset_href=url,
                )
            ],
            command=cmd,
            target=url,
            evidence=f"Access-Control-Allow-Origin: {acao or '(absent)'}",
        )
        ct = (r.header("Content-Type") or "").lower()
        bad = r.ok and "json" not in ct
        out += self.record(
            ctx,
            "root catalog served as JSON",
            [
                self.finding(
                    ctx,
                    "CNC-HOST-011",
                    "warning",
                    f"Root catalog served as '{ct or 'no content-type'}', expected JSON",
                    asset_href=url,
                )
            ]
            if bad
            else [],
            command=cmd,
            target=url,
            evidence=f"Content-Type: {ct or '(absent)'}",
        )
        return out

    def check(self, ctx: Context, asset):
        p: Probe | None = ctx.probes.get(asset.href)
        if p is None:
            return []
        rcmd = repro.range_get(asset.href)
        hcmd = repro.head(asset.href)
        both = repro.lines(
            "# ranged GET with an Origin header (what a browser does):", rcmd, "# HEAD:", hcmd
        )
        parent = self.make_check(ctx, "hosting", command=both, asset=asset).id
        f = lambda rule, sev, msg, **d: self.finding(ctx, rule, sev, msg, asset=asset, **d)
        out = []

        def sub(name, findings, evidence, command=rcmd, outcome=None):
            return self.record(
                ctx,
                name,
                findings,
                command=command,
                asset=asset,
                parent=parent,
                evidence=evidence,
                outcome=outcome,
            )

        rng, head = p.range, p.head
        if rng is not None and rng.error == OFFLINE:
            out += sub(
                "reachable anonymously",
                [f("coverage-limit", "info", "Hosting not probed: " + OFFLINE)],
                OFFLINE,
                outcome="skipped",
            )
        elif (
            rng is None
            or rng.status in (0, 403, 404, 410)
            or (rng.status >= 400 and not (head and head.ok))
        ):
            status = (
                rng.error if rng is not None and rng.error else f"HTTP {rng.status if rng else '?'}"
            )
            out += sub(
                "reachable anonymously",
                [f("CNC-HOST-000", "error", f"Asset not reachable anonymously ({status})")],
                status,
            )
        else:
            out += self._checks(ctx, asset, rng, head, sub, f, hcmd)
        self.record(
            ctx,
            "hosting",
            [],
            command=both,
            asset=asset,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
            evidence=f"GET Range -> HTTP {rng.status if rng else '?'}",
        )
        return out

    def _checks(self, ctx, asset, rng, head, sub, f, hcmd):
        out = sub("reachable anonymously", [], f"HTTP {rng.status}")
        scored = not ctx.is_ancillary(asset)
        # Range support matters for cloud-native data, much less for a thumbnail.
        out += sub(
            "range request returns 206",
            []
            if rng.status == 206
            else [
                f(
                    "CNC-HOST-001",
                    "error" if scored else "info",
                    f"HTTP range request not honoured (got {rng.status}, expected 206)",
                )
            ],
            f"HTTP {rng.status}; Content-Range: {rng.header('Content-Range') or '(absent)'}",
        )
        if head is not None and head.ok:
            ar = head.header("Accept-Ranges")
            out += sub(
                "Accept-Ranges: bytes",
                []
                if (ar or "").lower() == "bytes"
                else [
                    f(
                        "CNC-HOST-002",
                        "warning" if scored else "info",
                        "HEAD response lacks 'Accept-Ranges: bytes'",
                    )
                ],
                f"Accept-Ranges: {ar or '(absent)'}",
                command=hcmd,
            )
        acao = rng.header("Access-Control-Allow-Origin")
        out += sub(
            "CORS Access-Control-Allow-Origin",
            []
            if acao
            else [
                f(
                    "CNC-HOST-003",
                    "warning",
                    "No Access-Control-Allow-Origin for a cross-origin request: browser "
                    "clients cannot read this asset",
                )
            ],
            f"Access-Control-Allow-Origin: {acao or '(absent)'}",
        )
        if acao and scored:
            raw = rng.header("Access-Control-Expose-Headers") or ""
            exposed = {h.strip().lower() for h in raw.split(",")}
            missing = [h for h in EXPOSE_WANTED if h not in exposed and "*" not in exposed]
            out += sub(
                "CORS exposes Content-Range, Content-Length, ETag",
                [
                    f(
                        "CNC-HOST-004",
                        "warning",
                        "Access-Control-Expose-Headers does not expose "
                        + ", ".join(missing)
                        + " (browser range readers need them)",
                        missing=missing,
                    )
                ]
                if missing
                else [],
                f"Access-Control-Expose-Headers: {raw or '(absent)'}",
            )
        served = (rng.header("Content-Type") or "").split(";")[0].strip().lower()
        declared = (asset.media_type or "").split(";")[0].strip().lower()
        if declared and served:
            differs = served != declared and from_media_type(served) != from_media_type(declared)
            out += sub(
                "Content-Type matches STAC type",
                [
                    f(
                        "CNC-HOST-005",
                        "warning" if scored else "info",
                        f"Served Content-Type '{served}' differs from the STAC asset type '{declared}'",
                    )
                ]
                if differs
                else [],
                f"served {served}; STAC {declared}",
            )
        if scored:
            etag = rng.header("ETag") or (head and head.header("ETag"))
            out += sub(
                "ETag present",
                []
                if etag
                else [
                    f(
                        "CNC-HOST-006",
                        "info",
                        "No ETag header (clients cannot detect changes between range reads)",
                    )
                ],
                f"ETag: {etag or '(absent)'}",
            )
        return out
