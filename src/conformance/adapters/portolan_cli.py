"""portolan-cli (`portolan check`): optional read-only second opinion.

Included only when `portolan check --help` shows it can take a remote catalog URL. As of
portolan-cli 0.9.0 its PATH argument is a local directory and remote hosts appear only via
`--url` for `--live`, so this adapter records a coverage note instead of running. It never
passes --fix, --remove-legacy or calls `push`.
"""

from __future__ import annotations

import re

from ..toolchain import help_text, run, supports
from .base import Adapter, Context, parse_json_loose, sev_from_status, walk_checks, worst

FORBIDDEN = {"--fix", "--remove-legacy", "push", "--dry-run"}


class PortolanCli(Adapter):
    name = "portolan-cli"
    key = "portolan_cli"
    binary = "portolan"
    layer = "Portolan catalog (second opinion)"
    light = True
    install = "uv tool install portolan-cli"

    def example_cmd(self, url):
        return ["portolan", "check", "<local-copy-of-catalog>", "--json"]

    def accepts_remote(self) -> bool:
        h = help_text(self.binary, "check")
        # Look for an explicit statement that the target may be a URL.
        return bool(
            re.search(
                r"\[(PATH|TARGET)\|URL\]|\bURL of (a|the) (published )?catalog\b|"
                r"remote catalog|--remote\b",
                h,
                re.I,
            )
        )

    def jobs(self, ctx: Context):
        return [lambda: self.check(ctx)]

    def check(self, ctx: Context):
        if not self.accepts_remote():
            return self.record(
                ctx,
                "portolan check",
                [
                    self.finding(
                        ctx,
                        "coverage-limit",
                        "info",
                        "portolan-cli left out: `portolan check` only validates a local directory; it cannot "
                        "check a remote catalog without a local copy. rashid covers the same requirements.",
                    )
                ],
                command="portolan check --help   # PATH must be a local directory",
                target=ctx.crawl.root_url,
                outcome="skipped",
            )
        cmd = [self.binary, "check", ctx.crawl.root_url]
        if supports(self.binary, "--json", "check"):
            cmd.append("--json")
        if ctx.mode == "light" and supports(self.binary, "--no-data", "check"):
            cmd.append("--no-data")
        assert not FORBIDDEN & set(cmd), "portolan-cli must run read-only"
        r = run(cmd, timeout=float(ctx.config.limits["tool_timeout_s"]))
        command = self.tool_cmd(cmd)
        if r.returncode not in (0, 1):
            return self.record(
                ctx,
                "portolan check",
                [self.tool_error(ctx, r, ctx.crawl.root_url)],
                command=command,
                target=ctx.crawl.root_url,
                evidence=f"exit code {r.returncode}",
            )
        doc = parse_json_loose(r.stdout)
        parent = self.make_check(
            ctx, "portolan check", command=command, target=ctx.crawl.root_url
        ).id
        out = []
        for name, status, msg in walk_checks(doc or {}):
            fs = (
                [self.finding(ctx, f"portolan-cli:{name}", sev_from_status(status), msg or name)]
                if status in ("fail", "warn")
                else []
            )
            out += self.record(
                ctx,
                name,
                fs,
                command=command,
                target=ctx.crawl.root_url,
                parent=parent,
                evidence=msg or status,
                outcome={"pass": "pass"}.get(status),
            )
        self.record(
            ctx,
            "portolan check",
            [],
            command=command,
            target=ctx.crawl.root_url,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
            evidence=f"exit code {r.returncode}",
        )
        return out
