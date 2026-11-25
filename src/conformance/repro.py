"""Copy-paste shell commands that let a human reproduce each check.

Commands use only curl, jq, xxd and the validators themselves (pinned to the version that ran,
via `uvx --from pkg==version` for Python tools). Local catalog paths get the file equivalents.
"""

from __future__ import annotations

import shlex

ORIGIN = "https://browser.portolan-sdi.org"

# PyPI package that provides each CLI, for `uvx --from <pkg>==<version>`.
PACKAGES = {
    "rashid": "rashid",
    "portolan": "portolan-cli",
    "stac-validator": "stac-valid",  # renamed on PyPI; the command is still stac-validator
    "stac-check": "stac-check",
    "gpio": "geoparquet-io",
}


def package(binary: str, version: str | None) -> str:
    """PyPI package providing `binary` at `version` (stac-validator moved to stac-valid at 4.2.0)."""
    if binary == "stac-validator" and version and _older(version, (4, 2)):
        return "stac-validator"
    return PACKAGES.get(binary, binary)


def _older(version: str, than: tuple[int, ...]) -> bool:
    parts = []
    for p in version.split(".")[: len(than)]:
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) < than


def _remote(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def q(s: str) -> str:
    return shlex.quote(s)


def tool(cmd: list[str], version: str | None) -> str:
    """The exact tool invocation, pinned to the version that produced the finding."""
    binary, args = cmd[0], cmd[1:]
    known = version and version not in ("unknown",) and not version.startswith("native")
    if binary in PACKAGES and known:
        return shlex.join(
            ["uvx", "--from", f"{package(binary, version)}=={version}", binary, *args]
        )
    if binary == "rio":
        pin = f"rio-cogeo=={version}" if known else "rio-cogeo"
        return shlex.join(["uvx", "--from", "rasterio", "--with", pin, "rio", *args])
    line = shlex.join(cmd)
    if binary in ("pmtiles", "pdal") and known:
        line += f"   # {binary} {version}"
    return line


def head(url: str) -> str:
    return f"curl -sSI {q(url)}" if _remote(url) else f"ls -l {q(url)}"


def range_get(url: str, start: int = 0, end: int = 1023, origin: bool = True) -> str:
    """Show the response headers of a ranged GET (status, Content-Range, CORS, type, ETag)."""
    if not _remote(url):
        return f"xxd -s {start} -l {end - start + 1} {q(url)} | head"
    o = f"-H {q('Origin: ' + ORIGIN)} " if origin else ""
    return f"curl -sS -D - -o /dev/null {o}-H {q(f'Range: bytes={start}-{end}')} {q(url)}"


def first_bytes(url: str, n: int = 16, offset: int = 0) -> str:
    if not _remote(url):
        return f"xxd -s {offset} -l {n} {q(url)}"
    return f"curl -sS -r {offset}-{offset + n - 1} {q(url)} | xxd"


def json_query(url: str, jq: str) -> str:
    src = f"curl -sS {q(url)}" if _remote(url) else f"cat {q(url)}"
    return f"{src} | jq {q(jq)}"


def stac_asset(owner_url: str, key: str) -> str:
    return json_query(owner_url, f'.assets["{key}"]')


def lines(*cmds: str | None) -> str:
    return "\n".join(c for c in cmds if c)
