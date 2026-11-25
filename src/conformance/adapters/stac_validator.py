"""stac-validator: JSON-schema validation of every STAC object, including extension schemas."""

from __future__ import annotations

from ..toolchain import run
from .base import Adapter, Context, parse_json_loose


class StacValidator(Adapter):
    name = "stac-validator"
    key = "stac_validator"
    binary = "stac-validator"
    layer = "STAC"
    light = True

    def jobs(self, ctx: Context):
        # One call per object (root, every collection, every item). Our crawler does the
        # recursion, so a broken link shows up once (as CRAWL-001) rather than per tool.
        return [(lambda o=o: self.check(ctx, o)) for o in ctx.crawl.objects]

    def check(self, ctx: Context, obj):
        r = run([self.binary, obj.url], timeout=float(ctx.config.limits["tool_timeout_s"]))
        doc = parse_json_loose(r.stdout)
        if doc is None:
            return [
                self.tool_error(
                    ctx,
                    r,
                    obj.url,
                    collection=obj.collection,
                    item=obj.id if obj.kind == "Feature" else None,
                )
            ]
        return self.parse(ctx, obj, doc)

    def parse(self, ctx: Context, obj, doc):
        entries = doc if isinstance(doc, list) else [doc]
        out = []
        item = obj.id if obj.kind == "Feature" else None
        for e in entries:
            if not isinstance(e, dict) or e.get("valid_stac", True):
                continue
            etype = e.get("error_type") or "ValidationError"
            msg = e.get("error_message") or "STAC object failed schema validation"
            schema = e.get("failed_schema") or ", ".join(e.get("schema") or [])
            out.append(
                self.finding(
                    ctx,
                    f"stac-validator:{etype}",
                    "error",
                    msg,
                    collection=obj.collection,
                    item=item,
                    schema=schema or None,
                    object_url=obj.url,
                )
            )
        return out
