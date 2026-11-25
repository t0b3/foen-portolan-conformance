"""geoparquet-io (`gpio`): GeoParquet spec validity and best practices.

`gpio check spec <url>`  - spec validity (1.0 / 1.1 / 2.0 auto-detected)
`gpio check all <url>`   - bbox covering, spatial ordering, ZSTD, row groups, ...
Exit codes: 0 pass, 1 failed check, 2 warnings only (older releases; current docs say warnings
exit 0). JSON is used when the subcommand advertises --json, otherwise ✓/✗/⚠ text is parsed.
Every individual check gpio reports (passes included) is logged as a child check.
"""

from __future__ import annotations

import re

from ..toolchain import help_text, run, supports
from .base import (
    Adapter,
    Context,
    parse_json_loose,
    sev_from_status,
    text_checks,
    walk_checks,
    worst,
)

OUTCOME = {"pass": "pass", "fail": "fail", "warn": "warn", "info": "info"}


class Gpio(Adapter):
    name = "gpio"
    key = "gpio"
    binary = "gpio"
    layer = "GeoParquet"
    scope = "asset"
    formats = ("geoparquet",)
    install = "uv tool install geoparquet-io"

    def example_cmd(self, url):
        return ["gpio", "check", "all", url]

    def jobs(self, ctx: Context):
        return self.per_asset(ctx, ("geoparquet",), lambda a: self.check(ctx, a))

    def cmd(self, sub: str, href: str) -> list[str]:
        cmd = [self.binary, "check", sub, href]
        if supports(self.binary, "--json", "check", sub):
            cmd.append("--json")
        return cmd

    def check(self, ctx: Context, asset):
        out = []
        for sub in ("spec", "all"):
            cmd = self.cmd(sub, asset.href)
            r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
            if r.returncode not in (0, 1, 2):
                out += self.record(
                    ctx,
                    f"gpio check {sub}",
                    [self.tool_error(ctx, r, asset.href, asset=asset)],
                    command=self.tool_cmd(cmd),
                    asset=asset,
                    evidence=f"exit code {r.returncode}",
                )
                continue
            out += self.parse(ctx, asset, sub, r.stdout, r.returncode, "--json" in cmd, cmd)
        self.optimization(ctx, asset)  # logged as an info check, not graded
        return out

    def optimization(self, ctx: Context, asset) -> float | None:
        """`gpio check optimization` prints a combined spatial-query score, if this gpio has it."""
        if "optimization" not in help_text(self.binary, "check"):
            return None
        cmd = self.cmd("optimization", asset.href)
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        score = parse_score(r.stdout + "\n" + r.stderr)
        self.record(
            ctx,
            "gpio check optimization",
            [],
            command=self.tool_cmd(cmd),
            asset=asset,
            outcome="info" if score is not None else "error",
            evidence=f"score {score:g}/100"
            if score is not None
            else f"exit code {r.returncode}, no score found",
        )
        return score

    def parse(self, ctx: Context, asset, sub: str, stdout: str, rc: int, use_json: bool, cmd=None):
        cmd = cmd or [self.binary, "check", sub, asset.href]
        command = self.tool_cmd(cmd)
        parent = self.make_check(ctx, f"gpio check {sub}", command=command, asset=asset).id
        doc = parse_json_loose(stdout) if use_json else None
        if doc is not None:
            items = list(walk_checks(doc))
        else:
            items = [(line.split(":")[0][:60], s, line) for s, line in text_checks(stdout)]
        out = []
        for name, status, msg in items:
            fs = []
            if status in ("fail", "warn"):
                fs = [
                    self.finding(
                        ctx,
                        f"gpio:{sub}:{_slug(name)}",
                        sev_from_status(status),
                        msg or name,
                        asset=asset,
                        fmt="geoparquet",
                    )
                ]
            out += self.record(
                ctx,
                name,
                fs,
                command=command,
                asset=asset,
                parent=parent,
                outcome=OUTCOME.get(status, "info"),
                evidence=msg or status,
            )
        if rc == 1 and not any(f.severity == "error" for f in out):
            out += self.record(
                ctx,
                "exit code",
                [
                    self.finding(
                        ctx,
                        f"gpio:{sub}:failed",
                        "error",
                        f"gpio check {sub} failed (exit 1)",
                        asset=asset,
                        fmt="geoparquet",
                    )
                ],
                command=f"{command}; echo exit=$?",
                asset=asset,
                parent=parent,
            )
        if rc == 2 and not out:
            out += self.record(
                ctx,
                "exit code",
                [
                    self.finding(
                        ctx,
                        f"gpio:{sub}:warnings",
                        "warning",
                        f"gpio check {sub} reported warnings (exit 2)",
                        asset=asset,
                        fmt="geoparquet",
                    )
                ],
                command=f"{command}; echo exit=$?",
                asset=asset,
                parent=parent,
            )
        children = [c.outcome for c in ctx.checks if c.parent == parent]
        self.record(
            ctx,
            f"gpio check {sub}",
            [],
            command=command,
            asset=asset,
            outcome=worst(children),
            evidence=f"exit code {rc}; {len(items)} check(s) reported",
        )
        return out


def parse_score(text: str) -> float | None:
    """Find a 0-100 score in gpio's output: JSON {"score": n} or text like '82/100' / 'Score: 82'."""
    doc = parse_json_loose(text)
    if isinstance(doc, dict):
        for k in ("score", "optimization_score", "total_score"):
            v = doc.get(k)
            if isinstance(v, int | float):
                return float(v)
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*100\b", text) or re.search(
        r"score\D{0,12}(\d+(?:\.\d+)?)", text, re.I
    )
    if m and 0 <= float(m.group(1)) <= 100:
        return float(m.group(1))
    return None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "check"
