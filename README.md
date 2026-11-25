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
| GeoParquet | `gpio check spec` + `gpio check all`; `gpq validate` as cross-check | |
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
uv venv && uv pip install -e ".[parquet,dev]"
scripts/install-tools.sh            # latest rashid, gpio, stac-validator, stac-check, rio-cogeo, pmtiles, gpq
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

## Reading the report

`reports/latest/` (and a dated snapshot `reports/YYYY-MM-DD/`) holds:

- `index.html`: self-contained page (no CDN). Headline score, per-format and per-collection tables with
  drill-down to assets and findings, links to the Portolan browser and to the spec requirement text,
  changes since the last run, trend charts, coverage, tool versions.
- `report.json`: every normalized finding plus run metadata.
- `report.md`: the summary (also posted on PRs and in the job summary).
- `findings.csv`, `findings.parquet`: for analysis.
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
