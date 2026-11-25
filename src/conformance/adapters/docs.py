"""Documentation and metadata hygiene: README.md / AGENTS.md / llms.txt, license, Portolan
extension declaration. rashid is authoritative for the spec's exact rules; these checks keep
the report readable when rashid is missing and explain gaps in plain terms."""

from __future__ import annotations

from urllib.parse import urljoin

from .base import Adapter, Context

REL_FOR = {"README.md": "describedby", "AGENTS.md": "agents", "llms.txt": "llms"}
OPEN_LICENSES_NEEDING_LINK = {"other", "proprietary", "various"}


class Docs(Adapter):
    name = "docs-check"
    key = "docs"
    binary = None
    layer = "Docs"
    light = True

    def jobs(self, ctx: Context):
        targets = [o for o in ctx.crawl.objects if o.kind in ("Catalog", "Collection")]
        return [(lambda o=o: self.check(ctx, o)) for o in targets]

    def check(self, ctx: Context, obj):
        cfg = ctx.config.checks.get("docs", {})
        sev = cfg.get("severity", "warning")
        is_root = obj.url == ctx.crawl.root_url
        wanted = cfg.get("root" if is_root else "collection", [])
        col = obj.collection if obj.kind == "Collection" else None
        out = []
        links = obj.data.get("links") or []
        for name in wanted:
            link = next(
                (
                    lk
                    for lk in links
                    if str(lk.get("href", "")).rstrip("/").endswith(name)
                    or lk.get("rel") == REL_FOR.get(name)
                ),
                None,
            )
            url = urljoin(obj.url, link["href"]) if link else urljoin(obj.url, name)
            r = ctx.fetcher.head(url)
            if not r.ok:
                r = ctx.fetcher.get_range(url, 0, 0)
            ok = r.status in (200, 206)
            if r.status == 0:
                out.append(
                    self.finding(
                        ctx,
                        "coverage-limit",
                        "info",
                        f"{name} could not be checked ({r.error})",
                        collection=col,
                        asset_href=url,
                    )
                )
                continue
            if not ok:
                msg = (
                    f"{name} is linked but not reachable (HTTP {r.status})"
                    if link
                    else f"{name} missing beside {obj.kind.lower()}"
                )
                out.append(
                    self.finding(
                        ctx,
                        "CNC-DOC-001" if not link else "CNC-DOC-002",
                        sev,
                        msg,
                        collection=col,
                        asset_href=url,
                    )
                )
            elif not link and name != "llms.txt":
                out.append(
                    self.finding(
                        ctx,
                        "CNC-DOC-003",
                        "info",
                        f"{name} exists but no link points to it",
                        collection=col,
                        asset_href=url,
                    )
                )
        if obj.kind == "Collection":
            lic = obj.data.get("license")
            if not lic:
                out.append(
                    self.finding(
                        ctx, "CNC-LIC-001", "error", "Collection has no license", collection=col
                    )
                )
            elif lic.lower() in OPEN_LICENSES_NEEDING_LINK and not any(
                lk.get("rel") == "license" for lk in links
            ):
                out.append(
                    self.finding(
                        ctx,
                        "CNC-LIC-002",
                        "warning",
                        f"license '{lic}' without a rel=license link",
                        collection=col,
                    )
                )
        exts = obj.data.get("stac_extensions") or []
        if not any("schemas.portolan-sdi.org/portolan/" in str(e) for e in exts):
            out.append(
                self.finding(
                    ctx,
                    "CNC-META-001",
                    "warning",
                    f"{obj.kind} does not declare the Portolan extension schema in stac_extensions",
                    collection=col,
                )
            )
        return out
