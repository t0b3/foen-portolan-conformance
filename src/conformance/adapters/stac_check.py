"""stac-check: STAC best-practice lint (warnings) on every STAC object."""

from __future__ import annotations

import re

from ..toolchain import run, supports
from .base import Adapter, Context, parse_json_loose

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class StacCheck(Adapter):
    name = "stac-check"
    key = "stac_check"
    binary = "stac-check"
    layer = "STAC"
    light = True

    def jobs(self, ctx: Context):
        return [(lambda o=o: self.check(ctx, o)) for o in ctx.crawl.objects]

    def check(self, ctx: Context, obj):
        cmd = [self.binary, obj.url]
        use_json = supports(self.binary, "--json")
        if use_json:
            cmd.append("--json")
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        if r.returncode not in (0, 1) and not r.stdout:
            return [self.tool_error(ctx, r, obj.url, collection=obj.collection)]
        doc = parse_json_loose(r.stdout) if use_json else None
        if doc is not None:
            return self.parse_json(ctx, obj, doc)
        return self.parse_text(ctx, obj, r.stdout)

    def _f(self, ctx, obj, rule, sev, msg):
        return self.finding(
            ctx,
            rule,
            sev,
            msg,
            collection=obj.collection,
            item=obj.id if obj.kind == "Feature" else None,
            object_url=obj.url,
        )

    def parse_json(self, ctx: Context, obj, doc):
        out = []
        d = doc[0] if isinstance(doc, list) and doc else doc
        if isinstance(d, dict):
            if d.get("valid_stac") is False:
                out.append(
                    self._f(
                        ctx,
                        obj,
                        "stac-check:invalid",
                        "error",
                        str(d.get("error_msg") or d.get("error_message") or "invalid STAC"),
                    )
                )
            for msg in d.get("best_practices") or d.get("best_practices_msg") or []:
                if isinstance(msg, str) and msg.strip():
                    out.append(self._f(ctx, obj, "stac-check:best-practice", "warning", msg))
        return out

    def parse_text(self, ctx: Context, obj, text: str):
        out, section = [], None
        for raw in ANSI.sub("", text).splitlines():
            line = raw.strip()
            if not line:
                continue
            low = line.lower()
            if m := re.match(r"valid\s+\w+:\s*(true|false)", low):
                if m.group(1) == "false":
                    out.append(
                        self._f(ctx, obj, "stac-check:invalid", "error", "STAC object is not valid")
                    )
                section = None
                continue
            if low.startswith("validation error message:"):
                out.append(
                    self._f(ctx, obj, "stac-check:invalid", "error", line.split(":", 1)[1].strip())
                )
                continue
            if low.startswith("stac best practices"):
                section = "bp"
                continue
            if raw[:1] not in (" ", "\t") and line.endswith(":"):
                section = None
                continue
            if section == "bp" and raw[:1] in (" ", "\t") and not low.startswith("object id"):
                out.append(self._f(ctx, obj, "stac-check:best-practice", "warning", line))
        return out
