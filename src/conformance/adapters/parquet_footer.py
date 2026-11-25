"""Parquet format version of a remote file, from its footer, with two small range reads.

A Parquet file ends with `<FileMetaData (thrift compact)><4-byte LE length>PAR1`. Field 1 of
FileMetaData is `version` (i32): 1 = Parquet format v1, 2 = Parquet format v2 (what pyarrow
reports as format_version "2.x"). Only the last 8 bytes and the first 16 bytes of the footer are
read, never the data. A v1 file gets a SHOULD-level finding (CNC-PQ-001): Parquet v2 is a
best practice, and each unmet best practice drops the asset's grade by one level (grading.py).
"""

from __future__ import annotations

import struct
from dataclasses import replace

from .. import repro
from .base import Adapter, Context


def footer_length(tail: bytes) -> int | None:
    """Footer length from the last 8 bytes (`<len:u32 LE>PAR1`)."""
    if len(tail) != 8 or tail[4:] != b"PAR1":
        return None
    return struct.unpack("<I", tail[:4])[0]


def metadata_version(footer_head: bytes) -> int | None:
    """FileMetaData.version: field 1, type i32, read from the start of the thrift-compact footer."""
    if not footer_head:
        return None
    b0, pos = footer_head[0], 1
    if b0 & 0x0F != 5:  # field type must be i32
        return None
    if b0 >> 4 == 0:  # long form: field id follows as zigzag varint
        fid, pos = _varint(footer_head, pos)
        if fid is None or _zigzag(fid) != 1:
            return None
    elif b0 >> 4 != 1:  # short form: delta from field 0 must be 1
        return None
    raw, _ = _varint(footer_head, pos)
    return None if raw is None else _zigzag(raw)


def _varint(b: bytes, pos: int) -> tuple[int | None, int]:
    shift = val = 0
    while pos < len(b):
        byte = b[pos]
        pos += 1
        val |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return val, pos
        shift += 7
    return None, pos


def _zigzag(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


class ParquetFooter(Adapter):
    name = "parquet-footer"
    key = "parquet_footer"
    binary = None
    layer = "GeoParquet"
    scope = "asset"
    formats = ("geoparquet",)
    verifies = False  # reads the version only; gpio/rashid validate the file

    def jobs(self, ctx: Context):
        # Two tiny range reads, so it also runs on assets above the size cap.
        return self.per_asset(ctx, self.formats, lambda a: self.findings(ctx, a), header_only=True)

    def findings(self, ctx: Context, asset):
        version, cid = self.check(ctx, asset)
        c = next(x for x in ctx.checks if x.id == cid)
        if version == 2:
            return []
        if version is None:
            f = self.finding(
                ctx,
                "CNC-PQ-002",
                "info",
                f"Parquet format version could not be confirmed ({c.evidence})",
                asset=asset,
                fmt="geoparquet",
            )
        else:
            f = self.finding(
                ctx,
                "CNC-PQ-001",
                "warning",
                f"Parquet format v{version}, not v2 (rewrite with format version 2.x and "
                "data page v2)",
                asset=asset,
                fmt="geoparquet",
            )
        f = replace(f, reproduce=c.command, check_id=c.id)
        c.findings = [f.fingerprint]
        return [f]

    def check(self, ctx: Context, asset) -> tuple[int | None, str]:
        """Return (format version or None, id of the logged check)."""
        href = asset.href
        cmd = repro.lines(
            "# Last 8 bytes: footer length (u32 little-endian) + 'PAR1':",
            repro.first_bytes(href, 8, offset=0).replace("-r 0-7", "-r -8")
            if href.startswith("http")
            else f"tail -c 8 {repro.q(href)} | xxd",
            "# Or let pyarrow read the footer (range requests only):",
            "uvx --with pyarrow --with fsspec --with aiohttp python -c "
            + repro.q(
                "import sys, fsspec, pyarrow.parquet as pq; "
                "m = pq.ParquetFile(fsspec.open(sys.argv[1]).open()).metadata; "
                'print("format_version", m.format_version, "| created_by", m.created_by)'
            )
            + f" {repro.q(href)}",
        )
        p = ctx.probes.get(href)
        size = p.size if p and p.size else ctx.fetcher.size(href)
        version, evidence = None, None
        if not size or size < 12:
            evidence = f"file size unknown ({size})"
        else:
            tail = ctx.fetcher.get_range(href, size - 8, size - 1)
            flen = footer_length(tail.body) if tail.status in (200, 206) else None
            if flen is None or flen + 8 > size:
                evidence = f"no valid Parquet footer (HTTP {tail.status or tail.error})"
            else:
                start = size - 8 - flen
                head = ctx.fetcher.get_range(href, start, start + 15)
                version = metadata_version(head.body if head.status in (200, 206) else b"")
                evidence = (
                    f"FileMetaData.version={version} (Parquet format v{version}); footer {flen} bytes"
                    if version is not None
                    else "could not decode FileMetaData.version"
                )
        outcome = "pass" if version == 2 else ("warn" if version is not None else "skipped")
        c = self.make_check(
            ctx,
            "Parquet format v2 (footer)",
            command=cmd,
            asset=asset,
            evidence=evidence,
            outcome=outcome,
        )
        ctx.checks.append(c)
        return version, c.id
