"""Anonymous crawl: catalog -> sub-catalogs -> collections -> items -> assets.

Only JSON documents are fetched in full. Asset bytes are never downloaded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from .config import CatalogConfig
from .http import Fetcher, FetchError
from .normalize import Finding

FOLLOW_RELS = {"child", "item"}


@dataclass
class StacObject:
    kind: str  # Catalog | Collection | Feature
    id: str
    url: str
    data: dict
    collection: str | None = None  # owning collection id (for items) or own id
    depth: int = 0


@dataclass
class Asset:
    catalog_id: str
    key: str
    href: str
    media_type: str | None
    roles: list[str]
    collection: str | None
    item: str | None
    owner_url: str
    title: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class CrawlResult:
    catalog: CatalogConfig
    root_url: str
    root: dict | None = None
    root_etag: str | None = None
    root_last_modified: str | None = None
    objects: list[StacObject] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    skipped_collections: list[str] = field(default_factory=list)

    @property
    def collections(self) -> list[StacObject]:
        return [o for o in self.objects if o.kind == "Collection"]

    @property
    def items(self) -> list[StacObject]:
        return [o for o in self.objects if o.kind == "Feature"]

    def owner_of(self, url: str) -> StacObject | None:
        for o in self.objects:
            if o.url == url:
                return o
        return None


def crawl(
    cat: CatalogConfig, fetcher: Fetcher, max_items_per_collection: int = 5000
) -> CrawlResult:
    res = CrawlResult(catalog=cat, root_url=cat.url)
    head = fetcher.head(cat.url)
    res.root_etag = head.header("ETag")
    res.root_last_modified = head.header("Last-Modified")
    try:
        root = fetcher.get_json(cat.url)
    except FetchError as e:
        # Infrastructure problem: the caller decides whether to fail the job.
        raise CrawlError(str(e)) from e
    res.root = root

    seen: set[str] = set()
    items_per_col: dict[str, int] = {}
    stack: list[tuple[str, dict | None, str | None, int]] = [(cat.url, root, None, 0)]
    while stack:
        url, data, parent_col, depth = stack.pop()
        if url in seen:
            continue
        seen.add(url)
        if data is None:
            try:
                data = fetcher.get_json(url)
            except FetchError as e:
                res.findings.append(
                    Finding(
                        catalog_id=cat.id,
                        tool="crawler",
                        rule_id="CRAWL-001",
                        severity="error",
                        message=f"Linked STAC document could not be read: {e}",
                        collection=parent_col,
                        asset_href=url,
                    )
                )
                continue
        kind = data.get("type") or "Catalog"
        oid = str(data.get("id") or url)
        if kind == "Collection":
            if not cat.wants(oid):
                res.skipped_collections.append(oid)
                continue
            col = oid
        else:
            col = parent_col
        if kind == "Feature" and col is not None:
            items_per_col[col] = items_per_col.get(col, 0) + 1
            if items_per_col[col] > max_items_per_collection:
                continue
        obj = StacObject(kind=kind, id=oid, url=url, data=data, collection=col, depth=depth)
        res.objects.append(obj)

        for key, a in sorted((data.get("assets") or {}).items()):
            href = a.get("href")
            if not href:
                continue
            res.assets.append(
                Asset(
                    catalog_id=cat.id,
                    key=key,
                    href=urljoin(url, href),
                    media_type=a.get("type"),
                    roles=list(a.get("roles") or []),
                    collection=col,
                    item=oid if kind == "Feature" else None,
                    owner_url=url,
                    title=a.get("title"),
                    extra={
                        k: v for k, v in a.items() if k not in {"href", "type", "roles", "title"}
                    },
                )
            )
        # Sorted, reversed push => deterministic depth-first order.
        links = [
            lk for lk in data.get("links") or [] if lk.get("rel") in FOLLOW_RELS and lk.get("href")
        ]
        for lk in sorted(links, key=lambda x: x["href"], reverse=True):
            stack.append((urljoin(url, lk["href"]), None, col, depth + 1))

    over = {
        c: n - max_items_per_collection
        for c, n in items_per_col.items()
        if n > max_items_per_collection
    }
    for c, n in sorted(over.items()):
        res.findings.append(
            Finding(
                catalog_id=cat.id,
                tool="crawler",
                rule_id="coverage-limit",
                severity="info",
                message=f"{n} items beyond max_items_per_collection were not crawled",
                collection=c,
            )
        )
    res.objects.sort(key=lambda o: (o.depth > 0, o.collection or "", o.kind != "Collection", o.url))
    res.assets.sort(key=lambda a: (a.collection or "", a.item or "", a.key))
    return res


class CrawlError(RuntimeError):
    pass


def declared_portolan_versions(objects: list[StacObject]) -> dict[str, list[str]]:
    """Map Portolan schema version -> object URLs that declare it."""
    import re

    pat = re.compile(r"schemas\.portolan-sdi\.org/portolan/v(\d+\.\d+\.\d+[\w.-]*)/schema\.json")
    out: dict[str, list[str]] = {}
    for o in objects:
        for ext in o.data.get("stac_extensions") or []:
            m = pat.search(str(ext))
            if m:
                out.setdefault(m.group(1), []).append(o.url)
    return out
