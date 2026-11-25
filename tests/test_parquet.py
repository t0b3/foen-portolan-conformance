"""findings.parquet / checks.parquet: Parquet format 2.6 with V2 data pages, typed columns.

Skipped locally when pyarrow is missing; mandatory in CI (where `CI=true`), since pyarrow is a
core dependency there.
"""

from __future__ import annotations

import json
import os

import pytest

from conformance.report import build_report, write_outputs
from conformance.runner import execute

if os.environ.get("CI"):
    import pyarrow.parquet as pq
else:
    pq = pytest.importorskip("pyarrow.parquet")

DATA_PAGE_V2 = b"\x15\x06"  # thrift compact: field 1 (type, i32) = 3 (DATA_PAGE_V2), zigzag 6


def _report(config, fetcher, spec, tmp_path):
    rep = build_report(execute(config, fetcher, spec=spec, log=lambda *_: None))
    write_outputs(rep, tmp_path)
    return rep, tmp_path / "latest"


def test_findings_parquet_v2(config, recorded_fetcher, spec, tmp_path):
    rep, latest = _report(config, recorded_fetcher, spec, tmp_path)
    assert rep["run"]["findings_parquet"] is True
    assert rep["run"]["parquet"] == {
        "format_version": "2.6",
        "data_page_version": "2.0",
        "compression": "zstd",
    }
    for name, rows, key in (
        ("findings.parquet", rep["findings"], "fingerprint"),
        ("checks.parquet", rep["checks"], "id"),
    ):
        path = latest / name
        f = pq.ParquetFile(path)
        assert f.metadata.format_version == "2.6"
        assert f.metadata.num_rows == len(rows) > 0
        t = f.read()
        assert t.column(key).to_pylist() == [r[key] for r in rows]  # same order as report.json
        meta = json.loads(t.schema.metadata[b"foen-portolan-conformance"])
        assert meta["run_started"] == rep["run"]["started"]
        # Every column chunk starts with a V2 data page (read the page header bytes).
        raw = path.read_bytes()
        rg = f.metadata.row_group(0)
        for i in range(rg.num_columns):
            col = rg.column(i)
            assert col.compression == "ZSTD"
            off = col.data_page_offset
            assert raw[off : off + 2] == DATA_PAGE_V2, (name, col.path_in_schema)
    fs = pq.read_table(latest / "findings.parquet")
    assert str(fs.schema.field("is_coverage").type) == "bool"
    assert fs.column("reproduce").null_count == 0
    ck = pq.read_table(latest / "checks.parquet")
    assert str(ck.schema.field("findings").type) == "list<element: string>"
