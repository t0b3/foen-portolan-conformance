# foen-portolan-conformance

[![Portolan conformance](https://img.shields.io/endpoint?url=https://OWNER.github.io/foen-portolan-conformance/badge.json)](https://OWNER.github.io/foen-portolan-conformance/latest/)
[![conformance](https://github.com/OWNER/foen-portolan-conformance/actions/workflows/conformance.yml/badge.svg)](https://github.com/OWNER/foen-portolan-conformance/actions/workflows/conformance.yml)

A weekly conformance report for every asset in the FOEN (BAFU) [Portolan](https://github.com/portolan-sdi/portolan-spec)
catalog. It uses the **latest Portolan specification** and the **latest cloud-native geo validators**,
resolved again on every run.

- Default catalog: <https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json>
  ([browser view](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json))
- Report: <https://OWNER.github.io/foen-portolan-conformance/latest/> (replace `OWNER` after you fork or create the repo)

## What is checked

| Layer | Tool | Notes |
|---|---|---|
| Portolan catalog | [`rashid`](https://github.com/portolan-sdi/rashid) | `rashid check <url> --json --all --schema --live`; rule IDs `PTL-…` and requirement IDs `PORTO-…` are kept on every finding. `PTL-GEN-002` is shown as a coverage limit, not a failure. |
| Portolan CLI | `portolan-cli` | Read-only second opinion, **only if** `portolan check --help` shows it accepts a remote URL. As of 0.9.0 it needs a local directory, so it is left out and the report says so. Never `--fix`, never `push`. |
| STAC | `stac-validator`, `stac-check` | Root, every collection and every item. |
| GeoParquet | `gpio check spec` + `gpio check all` (geoparquet-io); Parquet v2 from the file footer | Feeds the grade. |
| COG | `rio cogeo validate --strict` | GDAL reads over HTTP range requests. |
| PMTiles | native v3 header parser + `pmtiles verify` / `pmtiles show` | Clustered flag, tile type, zooms, bounds against the STAC bbox. |
| Zarr / COPC | native metadata/header probe (+ `pdal info`) | Marked "incubating in spec". |
| Other formats | classifier | GeoPackage, Shapefile, plain GeoTIFF, GeoJSON, CSV… → "non-cloud-native asset". |
| Hosting | own probe | Range requests (206), `Accept-Ranges`, CORS incl. `Access-Control-Expose-Headers`, content type, ETag. |
| Docs | own check | README.md / AGENTS.md / llms.txt, license per collection, Portolan extension declared. |

Format detection uses the STAC asset `type` first, then the file extension, then magic bytes.
Asset bytes are never downloaded in full: probes use a 1 KiB range read, the validators use range
reads, and assets above `max_asset_size_gb` (default 2 GB) get header checks only (`skipped: size`).

## Run locally

```bash
uv venv && uv pip install -e ".[dev]"
scripts/install-tools.sh            # latest rashid, gpio, stac-valid (stac-validator), stac-check, rio-cogeo, pmtiles
.venv/bin/conformance run --config config.yaml --out reports/
open reports/latest/index.html
```

Useful options:

| Option | Meaning |
|---|---|
| `--catalog ID` | only this catalog (repeatable) |
| `--mode light` | metadata + STAC only, no asset byte reads (the daily run) |
| `--max-asset-size-gb N` | change the size cap |
| `--strict` | exit 3 when any MUST requirement fails (red CI on non-conformance) |
| `--fail-on-tool-error` | exit 4 when a tool crashed, timed out or is missing |
| `--require BINARY` | exit 4 before running if this tool is not on PATH (the workflows pass `--require stac-validator`) |
| `--offline tests/fixtures/recorded/bafu/index.json` | replay recorded HTTP responses (no network) |
| `--spec-file requirements.yaml --spec-version 0.3.0` | use a local requirements manifest |

Exit codes: `0` report written (whatever the catalog's state), `2` infrastructure error (catalog unreachable),
`3` `--strict` and MUST failures, `4` `--fail-on-tool-error` and a tool problem.

## Add a catalog

Add an entry to `config.yaml`:

```yaml
catalogs:
  - id: bafu-official
    url: https://data.example.admin.ch/portolan/catalog.json
    include: ["*"]          # glob on collection id
    exclude: ["test_*"]
```

A local directory path works too (that is how the tool canary checks the reference catalogs).

## How "latest" is resolved

- **Spec**: the latest GitHub release of `portolan-sdi/portolan-spec` (API `releases/latest`), then
  `specs/portolan/requirements.yaml` at that tag. With no release, `main` is used and the report says so.
  The report records the version, commit SHA and MUST / SHOULD / MAY counts.
- **Declared version**: read from the Portolan schema URI in each object's `stac_extensions`
  (`https://schemas.portolan-sdi.org/portolan/vX.Y.Z/schema.json`). The report shows MUST failures against
  the latest spec and against the declared one, and flags a catalog that is behind.
  "Against declared" drops findings whose `PORTO-…` requirement does not exist in the declared version's manifest.
- **Tools**: every run installs the newest release (`uv tool install --upgrade …`, latest GitHub release
  binaries) and writes a `tool_versions` block into the report. `constraints.txt` is empty; add a line such as
  `rashid!=0.5.1` to pin out a broken release. The validator cache is keyed by ISO week.

## Reproducing any result by hand

Nothing in the report has to be taken on trust:

- **Every finding** has a `reproduce` command: the exact tool call, pinned to the version that ran
  (`uvx --from geoparquet-io==1.8.0 gpio check all <url>`), or for this repo's own checks the `curl`/`jq`/`xxd`
  commands that show the same evidence (headers, magic bytes, STAC fields).
- **Every check is logged, passes included** (`checks.csv`, `report.json → checks`): tool, version, target, the
  value that was observed (e.g. `Access-Control-Allow-Origin: (absent)`, `clustered=true`), outcome, command,
  and the findings it produced. Tool runs are parent checks; the individual tests they report are children.
- **Every dataset** (asset and collection) lists the commands to inspect it yourself: its STAC entry, the headers of
  a ranged cross-origin GET, its size, its first bytes, and its format validator.
- **The whole run** has a reproduce block: install commands with the same tool versions, then the `conformance run` call.

In `index.html`, **every number is a link**. It opens the exact list it counts (assets, findings, checks or spec
requirements). From there each item expands to its checks, their sub-checks, the observed evidence and a
**copy** button for the command. The test suite asserts that every number equals the length of its list.

## Reading the report

`reports/latest/` (and a dated snapshot `reports/YYYY-MM-DD/`) holds:

- `index.html`: self-contained page (no CDN). Headline score, per-format and per-collection tables with
  drill-down to assets and findings, links to the Portolan browser and to the spec requirement text,
  changes since the last run, trend charts, coverage, tool versions.
- `report.json`: every normalized finding plus run metadata.
- `report.md`: the summary (also posted on PRs and in the job summary).
- `findings.parquet`, `checks.parquet`: Parquet format **2.6 with V2 data pages** ("Parquet v2"), ZSTD,
  typed columns (`is_coverage` bool, `findings` list of fingerprints). Run metadata (spec and tool versions)
  sits in the file's key-value metadata under `foen-portolan-conformance`.
  `duckdb -c "select severity, count(*) from 'findings.parquet' group by 1"`
- `findings.csv`, `checks.csv`: the same rows as CSV (with `reproduce` and `check_id` columns).
- `badge.json`: shields.io endpoint.

Each finding is `{catalog_id, collection, item, asset_href, format, tool, tool_version, rule_id, severity, message, spec_requirement_id}`.

| Term | Meaning |
|---|---|
| **MUST failure** | `severity: error` |
| **SHOULD warning** | `severity: warning` |
| **Fully conformant asset** | a scored asset with no error, no warning, and validated by at least one format validator |
| **Unverified** | a cloud-native asset that no validator could read (tool missing, size cap, light mode) - never counted as conformant |
| **Scored assets** | data and tiles; thumbnails, styles and documents are ancillary (hosting-probed, not scored) |
| **Coverage** | what did not run and why (tool missing / error, size cap, remote-crawl limits). Not a failure. |

### Grades (A to F)

Every scored asset gets a grade, with the same rule for every cloud-native format (GeoParquet, COG,
PMTiles, COPC, Zarr):

- start at **A**; each best practice or recommendation that is not met drops the grade **one level**.
  That is every MUST failure and SHOULD warning on the asset, from any tool: gpio, rio-cogeo, the
  PMTiles/COPC/Zarr checks, the hosting probe (range requests, CORS) and rashid
- GeoParquet: not being **Parquet v2** is one of them (`CNC-PQ-001`), so a file whose only gap is Parquet v1 is a
  **B**. A version that could not be confirmed (`CNC-PQ-002`) counts too
- **A only if every best practice is met** (and confirmed); floor is **F**
- a data asset in a format that is not cloud-native (GeoPackage, Shapefile, plain GeoTIFF, …) is **F**
- an asset no format validator could read gets no grade: an unchecked file must not look like an A
- the same problem reported twice by one tool counts once; info notes (missing ETag, media type spelling) don't count

Each grade links to the exact findings that cost it a level, each with its reproduce command. The rule lives in
`src/conformance/grading.py`. The Parquet version is read from the file footer with two small range requests
(`curl -sS -r -8 <url> | xxd`).

### Where to start: anti-patterns

At the top of the report, every MUST and SHOULD finding is sorted into one **general anti-pattern** and the
groups are ranked by **severity** (critical → high → medium → low), then by how many assets they hit. Each group
says why it matters and how to fix it, and drills down to the affected assets, findings and rules:

| Severity | Anti-pattern |
|---|---|
| critical | Data not in a cloud-native format · Not readable with HTTP range requests · Invalid or broken files and metadata |
| high | Portolan MUST requirements broken · Blocked for browser clients (CORS) |
| medium | No spatial index or ordering · Inefficient storage layout (incl. Parquet v1, compression, row groups) · Metadata does not match the data · Portolan SHOULD not followed |
| low | Missing documentation · STAC best practices · Other |

The classification table is `src/conformance/antipatterns.py`.

Rule IDs: `PTL-…` come from rashid, `gpio:…`, `stac-check:…` etc. from those tools, `CNC-…`, `PMT-…`,
`ZARR-…`, `COPC-…` from this repo's own checks (they carry no `PORTO-…` ID unless a tool supplied one).

## Automation

- `.github/workflows/conformance.yml`: weekly full run (Monday 05:17 UTC), daily lightweight run, on push to
  `main`, and `workflow_dispatch` (`catalog_id`, `full_data_checks`, `max_asset_size_gb`). Snapshots are
  committed to the `reports` branch and deployed to GitHub Pages. PRs run the checks and comment the summary,
  without publishing. A rise in MUST failures opens (or updates) one issue labelled `conformance-regression`;
  it closes itself when the listed findings are gone.
- `.github/workflows/tool-canary.yml`: weekly, latest tools against the reference catalogs in the spec repo.
  If the canary is red, a tool changed, not the FOEN catalog.
- `.github/workflows/ci.yml`: ruff + unit tests.

**stac-validator is required.** It is installed from the PyPI package **`stac-valid`**: the project was renamed at
4.2.0 and `stac-validator` on PyPI is now an alias with no code, so `uv tool install stac-validator` fails. The command
is still called `stac-validator`; since 4.x it validates with `stac-validator validate <path>` and has no `--version`
(the report takes the version from `uv tool list`). The adapter reads `--help` and also handles the 3.x form. `scripts/install-tools.sh` installs it first, retries once, and runs it against
`tests/fixtures/smoke/collection.json`; if it is missing or the smoke test fails, the script exits 1 and the workflow
fails. The run step also passes `--require stac-validator`. `ci.yml` runs the stac-validator adapter test against the
real tool on every PR. Other validators are best effort: a failed install shows up in the report as "tool-missing".
Set `REQUIRED_TOOLS="stac-validator rashid"` (space-separated, command names) to make more tools mandatory.

`INSTALL_SYSTEM=1` also installs `gdal-bin` and `pdal` from apt, one at a time. `pdal` is not in Ubuntu 24.04's default
archive, so on GitHub runners it is skipped with a warning; it is only needed for COPC assets, which the FOEN catalog
does not have.

Workflows run on the **`ubuntu-26.04`** runner (pinned rather than `ubuntu-latest`, so an OS move is a deliberate
change) with **Python 3.14**, set in `.python-version`, the workflows and `install-tools.sh` (`PYTHON_VERSION`).
3.14 is the newest Python for which every validator installs from wheels: Python 3.15 is out, but gpio pins
`duckdb<1.6`, and duckdb 1.5.x ships no 3.15 wheels (checked 2026-11-26). Move to 3.15 once gpio allows duckdb 2.x or
duckdb publishes 1.5.x wheels for 3.15. Action versions are kept current by Dependabot.

One-time setup: *Settings → Pages → Source: GitHub Actions*.

## Known limitations

- Remote crawl: rashid reads only linked documents (`PTL-GEN-002`), so orphan objects (`PTL-LNK-002`) and
  files beside collections (`PTL-COL-005`) are not checked. Syncing the bucket to disk would fix this.
- `portolan-cli` cannot check a remote catalog today and is left out (reported under Coverage).
- Some tools' JSON layouts are not pinned upstream. Adapters read each tool's current `--help` before choosing flags
  and parse output tolerantly; a format change shows up in the tool canary as a `tool-error`.
- The own checks (`CNC-…`) are heuristics that make the report readable; rashid is authoritative for Portolan requirements.
- "Conformance to the declared version" is approximate: it filters findings by requirement ID, while the tools
  themselves validate against their own bundled spec version.
- The sample report in `reports/` was produced offline from recorded catalog metadata, without validators or network;
  the first CI run replaces it.

## License

MIT, see [LICENSE](LICENSE).
