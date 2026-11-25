"""PMTiles: native v3 header checks (always) plus `pmtiles verify` / `pmtiles show` (go-pmtiles)."""

from __future__ import annotations

from ..formats import parse_pmtiles_header
from ..toolchain import run, supports, which
from .base import Adapter, Context, parse_json_loose


class Pmtiles(Adapter):
    name = "pmtiles"
    key = "pmtiles"
    binary = "pmtiles"
    layer = "PMTiles"

    def available(self) -> bool:
        return True  # native header checks need no binary

    def version(self):
        from .. import __version__
        from ..toolchain import version

        return version(self.binary) if which(self.binary) else f"native-{__version__}"

    def jobs(self, ctx: Context):
        jobs = self.per_asset(
            ctx, ("pmtiles",), lambda a: self.header_checks(ctx, a), header_only=True
        )
        if which(self.binary):
            jobs += self.per_asset(ctx, ("pmtiles",), lambda a: self.tool_checks(ctx, a))
        elif jobs and ctx.mode == "full":
            jobs.append(
                lambda: [
                    self.finding(
                        ctx,
                        "tool-missing",
                        "info",
                        "go-pmtiles not installed: native header checks ran, `pmtiles verify` did not",
                    )
                ]
            )
        return jobs

    def _bbox(self, ctx: Context, asset) -> list[float] | None:
        owner = ctx.crawl.owner_of(asset.owner_url)
        if owner is None:
            return None
        if owner.kind == "Feature":
            return owner.data.get("bbox")
        bb = ((owner.data.get("extent") or {}).get("spatial") or {}).get("bbox") or [None]
        b = bb[0] if bb and isinstance(bb[0], list) else bb
        return b if b and len(b) >= 4 else None

    def header_checks(self, ctx: Context, asset):
        probe = ctx.probes.get(asset.href)
        head = probe.first_bytes if probe else b""
        if not head:
            return None  # not looked at; unreachable assets are reported by the hosting probe
        h = parse_pmtiles_header(head)
        f = lambda rule, sev, msg, **d: self.finding(
            ctx, rule, sev, msg, asset=asset, fmt="pmtiles", **d
        )
        if h is None:
            return [f("PMT-001", "error", "Not a PMTiles archive (bad magic bytes)")]
        out = []
        if h["spec_version"] != 3:
            out.append(
                f("PMT-002", "error", f"PMTiles spec version {h['spec_version']} (expected 3)")
            )
        if not h["clustered"]:
            out.append(
                f(
                    "PMT-003",
                    "warning",
                    "Archive is not clustered (tiles not in Hilbert order); "
                    "range reads are less efficient",
                )
            )
        if h["min_zoom"] > h["max_zoom"]:
            out.append(
                f("PMT-004", "error", f"min_zoom {h['min_zoom']} > max_zoom {h['max_zoom']}")
            )
        if h["tile_type"] == "unknown":
            out.append(f("PMT-005", "warning", "Tile type is 'unknown'"))
        stac = self._bbox(ctx, asset)
        if stac:
            out += self._compare_bounds(f, h["bounds"], stac)
        return out

    @staticmethod
    def _compare_bounds(f, pm: list[float], stac: list[float]):
        sx0, sy0, sx1, sy1 = (stac[0], stac[1], stac[3], stac[4]) if len(stac) == 6 else stac[:4]
        px0, py0, px1, py1 = pm
        if px1 < sx0 or px0 > sx1 or py1 < sy0 or py0 > sy1:
            return [
                f("PMT-010", "error", f"PMTiles bounds {pm} do not intersect the STAC bbox {stac}")
            ]
        tol = max(0.05, 0.05 * max(sx1 - sx0, sy1 - sy0))
        off = max(abs(px0 - sx0), abs(py0 - sy0), abs(px1 - sx1), abs(py1 - sy1))
        if off > tol:
            return [
                f(
                    "PMT-011",
                    "warning",
                    f"PMTiles bounds {[round(x, 5) for x in pm]} differ from the STAC bbox "
                    f"{[round(x, 5) for x in stac]} by up to {off:.3f}°",
                    tolerance=tol,
                )
            ]
        return []

    def tool_checks(self, ctx: Context, asset):
        out = []
        t = float(ctx.config.limits["tool_timeout_s"])
        r = run([self.binary, "verify", asset.href], timeout=t)
        if r.timed_out or r.returncode < 0:
            out.append(self.tool_error(ctx, r, asset.href, asset=asset))
        elif r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            out.append(
                self.finding(
                    ctx,
                    "pmtiles:verify",
                    "error",
                    "pmtiles verify failed: " + (msg[-1] if msg else ""),
                    asset=asset,
                    fmt="pmtiles",
                )
            )
        if supports(self.binary, "--header-json", "show"):
            r = run([self.binary, "show", asset.href, "--header-json"], timeout=t)
            hdr = parse_json_loose(r.stdout)
            if r.returncode != 0 or not isinstance(hdr, dict):
                out.append(self.tool_error(ctx, r, asset.href, asset=asset))
        return out
