"""Find external validators, read their versions and --help, and run them safely."""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
from dataclasses import dataclass

VERSION_RE = re.compile(r"\bv?(\d+\.\d+(?:\.\d+)?(?:[-.+]?[\w.]+)?)")


@dataclass
class RunResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run(cmd: list[str], timeout: float, cwd: str | None = None) -> RunResult:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
            env=None,
            errors="replace",
        )
        return RunResult(cmd, p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired as e:
        return RunResult(cmd, -1, _s(e.stdout), _s(e.stderr), timed_out=True)
    except OSError as e:
        return RunResult(cmd, -2, "", str(e))


def _s(x) -> str:
    if x is None:
        return ""
    return x.decode(errors="replace") if isinstance(x, bytes) else x


@functools.cache
def version(binary: str, *args: str) -> str | None:
    """Best-effort version string; tries `--version` then `version`."""
    if not which(binary):
        return None
    for probe in ([*args, "--version"], [*args, "version"]):
        r = run([binary, *probe], timeout=60)
        text = (r.stdout + " " + r.stderr).strip()
        if r.returncode == 0 and text:
            m = VERSION_RE.search(text)
            if m:
                return m.group(1)
    return "unknown"


@functools.cache
def help_text(binary: str, *subcommand: str) -> str:
    if not which(binary):
        return ""
    r = run([binary, *subcommand, "--help"], timeout=60)
    return r.stdout + r.stderr


def supports(binary: str, flag: str, *subcommand: str) -> bool:
    """True if `flag` appears in the tool's current --help. Lets adapters follow upstream CLIs."""
    return (
        re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", help_text(binary, *subcommand))
        is not None
    )
