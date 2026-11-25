"""PMTiles: native v3 header checks (always) plus `pmtiles verify` / `pmtiles show` (go-pmtiles).

Each header test is logged as its own check with the observed value, so a reader can see
what passed as well as what failed. Reproduce the header with `pmtiles show <url>` or by
reading the first 127 bytes.
"""

from __future__ import annotations

from .. import repro
from ..formats import parse_pmtiles_header
from ..toolchain import run, supports, which
from .base import Adapter, Context, parse_json_loose, worst


class Pmtiles(Adapter):
    name = "pmtiles"
    key = "pmtiles"
    binary = "pmtiles"
    layer = "PMTiles"
    scope = "asset"
    formats = ("pmtiles",)

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
            for a in ctx.assets_of("pmtiles"):
                jobs.append(
                    lambda a=a: self.record(
                        ctx,
                        "pmtiles verify",
                        [
                            self.finding(
                                ctx,
                                "tool-missing",
                                "info",
                                "go-pmtiles not installed: native header checks ran, `pmtiles verify` did not",
                                asset=a,
                            )
                        ],
                        command="# install: https://github.com/protomaps/go-pmtiles/releases\n"
                        + repro.tool(["pmtiles", "verify", a.href], None),
                        asset=a,
                    )
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
        cmd = repro.lines(
            repro.tool(["pmtiles", "show", asset.href], None),
            "# or the raw 127-byte header:",
            repro.first_bytes(asset.href, 127),
        )
        parent = self.make_check(ctx, "PMTiles header", command=cmd, asset=asset).id
        f = lambda rule, sev, msg, **d: self.finding(
            ctx, rule, sev, msg, asset=asset, fmt="pmtiles", **d
        )

        def sub(name, findings, evidence):
            return self.record(
                ctx, name, findings, command=cmd, asset=asset, parent=parent, evidence=evidence
            )

        h = parse_pmtiles_header(head)
        out = []
        if h is None:
            out += sub(
                "magic bytes 'PMTiles'",
                [f("PMT-001", "error", "Not a PMTiles archive (bad magic bytes)")],
                f"first bytes: {head[:7]!r}",
            )
        else:
            out += sub("magic bytes 'PMTiles'", [], "PMTiles")
            out += sub(
                "spec version is 3",
                [f("PMT-002", "error", f"PMTiles spec version {h['spec_version']} (expected 3)")]
                if h["spec_version"] != 3
                else [],
                f"spec_version={h['spec_version']}",
            )
            out += sub(
                "clustered (Hilbert order)",
                []
                if h["clustered"]
                else [
                    f(
                        "PMT-003",
                        "warning",
                        "Archive is not clustered (tiles not in Hilbert order); "
                        "range reads are less efficient",
                    )
                ],
                f"clustered={str(h['clustered']).lower()}",
            )
            out += sub(
                "min_zoom <= max_zoom",
                [f("PMT-004", "error", f"min_zoom {h['min_zoom']} > max_zoom {h['max_zoom']}")]
                if h["min_zoom"] > h["max_zoom"]
                else [],
                f"min_zoom={h['min_zoom']}, max_zoom={h['max_zoom']}",
            )
            out += sub(
                "tile type known",
                [f("PMT-005", "warning", "Tile type is 'unknown'")]
                if h["tile_type"] == "unknown"
                else [],
                f"tile_type={h['tile_type']}",
            )
            stac = self._bbox(ctx, asset)
            if stac:
                bcmd = repro.lines(
                    cmd,
                    "# STAC bbox of the owning collection/item:",
                    repro.json_query(asset.owner_url, ".extent.spatial.bbox[0] // .bbox"),
                )
                out += self.record(
                    ctx,
                    "bounds match STAC bbox",
                    self._compare_bounds(f, h["bounds"], stac),
                    command=bcmd,
                    asset=asset,
                    parent=parent,
                    evidence=f"pmtiles={[round(x, 5) for x in h['bounds']]} stac={stac}",
                )
        self.record(
            ctx,
            "PMTiles header",
            [],
            command=cmd,
            asset=asset,
            outcome=worst([c.outcome for c in ctx.checks if c.parent == parent]),
            evidence=None
            if h is None
            else f"{h['tile_type']} z{h['min_zoom']}-{h['max_zoom']}, clustered={str(h['clustered']).lower()}",
        )
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
        cmd = [self.binary, "verify", asset.href]
        r = run(cmd, timeout=t)
        fs = []
        if r.timed_out or r.returncode < 0:
            fs.append(self.tool_error(ctx, r, asset.href, asset=asset))
        elif r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            fs.append(
                self.finding(
                    ctx,
                    "pmtiles:verify",
                    "error",
                    "pmtiles verify failed: " + (msg[-1] if msg else ""),
                    asset=asset,
                    fmt="pmtiles",
                )
            )
        out += self.record(
            ctx,
            "pmtiles verify",
            fs,
            command=self.tool_cmd(cmd),
            asset=asset,
            evidence=f"exit code {r.returncode}",
        )
        if supports(self.binary, "--header-json", "show"):
            cmd = [self.binary, "show", asset.href, "--header-json"]
            r = run(cmd, timeout=t)
            hdr = parse_json_loose(r.stdout)
            fs = (
                [self.tool_error(ctx, r, asset.href, asset=asset)]
                if r.returncode != 0 or not isinstance(hdr, dict)
                else []
            )
            out += self.record(
                ctx,
                "pmtiles show --header-json",
                fs,
                command=self.tool_cmd(cmd),
                asset=asset,
                evidence=f"exit code {r.returncode}",
            )
        return out
