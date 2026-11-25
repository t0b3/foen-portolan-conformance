"""Documentation and metadata hygiene: README.md / AGENTS.md / llms.txt, license, Portolan
extension declaration. rashid is authoritative for the spec's exact rules; these checks keep
the report readable when rashid is missing and explain gaps in plain terms."""

from __future__ import annotations

from urllib.parse import urljoin

from .. import repro
from .base import Adapter, Context, worst

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
        parent = self.make_check(
            ctx,
            f"docs and metadata of {obj.kind.lower()}",
            command=None,
            target=obj.url,
            collection=col,
        ).id
        out = []

        def sub(name, findings, cmd, evidence, outcome=None):
            return self.record(
                ctx,
                name,
                findings,
                command=cmd,
                target=obj.url,
                collection=col,
                parent=parent,
                evidence=evidence,
                outcome=outcome,
            )

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
            cmd = repro.lines(
                repro.json_query(obj.url, f'.links[] | select(.rel == "{REL_FOR.get(name, "")}")'),
                repro.head(url),
            )
            r = ctx.fetcher.head(url)
            if not r.ok:
                r = ctx.fetcher.get_range(url, 0, 0)
            ev = f"link: {link['href'] if link else '(none)'}; HTTP {r.status or r.error}"
            if r.status == 0:
                out += sub(
                    f"{name} present",
                    [
                        self.finding(
                            ctx,
                            "coverage-limit",
                            "info",
                            f"{name} could not be checked ({r.error})",
                            collection=col,
                            asset_href=url,
                        )
                    ],
                    cmd,
                    ev,
                    "skipped",
                )
                continue
            fs = []
            if r.status not in (200, 206):
                msg = (
                    f"{name} is linked but not reachable (HTTP {r.status})"
                    if link
                    else f"{name} missing beside {obj.kind.lower()}"
                )
                fs.append(
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
                fs.append(
                    self.finding(
                        ctx,
                        "CNC-DOC-003",
                        "info",
                        f"{name} exists but no link points to it",
                        collection=col,
                        asset_href=url,
                    )
                )
            out += sub(f"{name} present", fs, cmd, ev)
        if obj.kind == "Collection":
            lic = obj.data.get("license")
            cmd = repro.json_query(
                obj.url, '{license, license_links: [.links[] | select(.rel == "license")]}'
            )
            fs = []
            if not lic:
                fs.append(
                    self.finding(
                        ctx, "CNC-LIC-001", "error", "Collection has no license", collection=col
                    )
                )
            elif lic.lower() in OPEN_LICENSES_NEEDING_LINK and not any(
                lk.get("rel") == "license" for lk in links
            ):
                fs.append(
                    self.finding(
                        ctx,
                        "CNC-LIC-002",
                        "warning",
                        f"license '{lic}' without a rel=license link",
                        collection=col,
                    )
                )
            out += sub("license declared", fs, cmd, f"license: {lic or '(absent)'}")
        exts = obj.data.get("stac_extensions") or []
        has = [e for e in exts if "schemas.portolan-sdi.org/portolan/" in str(e)]
        out += sub(
            "Portolan extension declared",
            []
            if has
            else [
                self.finding(
                    ctx,
                    "CNC-META-001",
                    "warning",
                    f"{obj.kind} does not declare the Portolan extension schema in stac_extensions",
                    collection=col,
                )
            ],
            repro.json_query(obj.url, ".stac_extensions"),
            f"stac_extensions: {', '.join(exts) or '(none)'}",
        )
        self.record(
            ctx,
            f"docs and metadata of {obj.kind.lower()}",
            [],
            command=repro.json_query(obj.url, "."),
            target=obj.url,
            collection=col,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
        )
        return out
