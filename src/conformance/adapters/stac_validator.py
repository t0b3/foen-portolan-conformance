"""stac-validator: JSON-schema validation of every STAC object, including extension schemas.

stac-validator 4.x (PyPI package `stac-valid`) moved validation under a subcommand:
`stac-validator validate <path>`; older releases took the path directly. The form is chosen
from the installed tool's `--help`, so either works.
"""

from __future__ import annotations

import re

from ..toolchain import help_text, run, which
from .base import Adapter, Context, parse_json_loose


class StacValidator(Adapter):
    name = "stac-validator"
    key = "stac_validator"
    binary = "stac-validator"
    layer = "STAC"
    light = True
    scope = "object"
    install = "uv tool install stac-valid  # provides the stac-validator command"

    def example_cmd(self, url):
        return self.cmd(url)

    def cmd(self, url: str) -> list[str]:
        return [self.binary, *validate_subcommand(self.binary), url]

    def jobs(self, ctx: Context):
        # One call per object (root, every collection, every item). Our crawler does the
        # recursion, so a broken link shows up once (as CRAWL-001) rather than per tool.
        return [
            (lambda o=o: self.record_object(ctx, o, self.check(ctx, o), self.cmd(o.url)))
            for o in ctx.crawl.objects
        ]

    def check(self, ctx: Context, obj):
        r = run(self.cmd(obj.url), timeout=float(ctx.config.limits["tool_timeout_s"]))
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


def validate_subcommand(binary: str = "stac-validator") -> list[str]:
    """["validate"] when the installed CLI lists a `validate` command (4.x), else [] (3.x).

    With no binary installed (e.g. writing a "not run" hint) the current 4.x form is used.
    """
    if not which(binary):
        return ["validate"]
    h = help_text(binary)
    return ["validate"] if re.search(r"^\s*validate\b", h, re.M) else []
