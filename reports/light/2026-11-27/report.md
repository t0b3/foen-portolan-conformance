# Portolan cloud-native conformance report

- **bafu-portolan**: BAFU Portolan <https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json> (9 collections, 0 items, 31 assets)

Run: 2026-11-27T13:09:55Z (light mode)

| | |
|---|---|
| Fully conformant assets | **0%** (0/15) |
| Assets without MUST failures | 33.3% (5/15) |
| Unverified assets (validator did not run) | 10 |
| MUST failures (errors) | **12** |
| SHOULD warnings | 133 |
| Coverage notes (skipped / tool issues) | 2 |

## Where to start: anti-patterns by severity

| # | Severity | Anti-pattern | Assets | Findings (MUST / SHOULD) | Rules |
|---:|---|---|---:|---|---|
| 1 | critical | **Data not in a cloud-native format** | 5 | 5 (0 / 5) | `CNC-FMT-001` ×5 |
| 2 | critical | **Invalid or broken files and metadata** | 0 | 9 (9 / 0) | `stac-validator:Exception` ×9 |
| 3 | high | **Portolan MUST requirements broken** | 0 | 3 (3 / 0) | `PTL-AST-009` ×2, `PTL-LIV-004` ×1 |
| 4 | medium | **Portolan recommendations (SHOULD) not followed** | 0 | 117 (0 / 117) | `PTL-AST-003` ×62, `PTL-AST-010` ×40, `PTL-FIL-005` ×15 |
| 5 | low | **STAC best practices not followed** | 0 | 10 (0 / 10) | `stac-check:best-practice` ×10 |
| 6 | low | **Missing documentation** | 0 | 1 (0 / 1) | `CNC-DOC-001` ×1 |

**1. Data not in a cloud-native format** (critical). Clients must download the whole file before reading anything; no partial or remote reads. *Fix:* Convert: vector to GeoParquet (`gpio convert`), raster to COG (`rio cogeo create`), tiles to PMTiles. Keep the old format only as an extra download.

**2. Invalid or broken files and metadata** (critical). Readers may reject the file or silently misread it. *Fix:* Fix the reported validation errors; re-run the tool command shown with each finding.

**3. Portolan MUST requirements broken** (high). The catalog does not meet the Portolan specification it declares. *Fix:* Follow the requirement text linked with each finding (rashid rule and PORTO- ID).

**4. Portolan recommendations (SHOULD) not followed** (medium). Not wrong, but harder to find, use or trust than the spec intends. *Fix:* Follow the requirement text linked with each finding.

**5. STAC best practices not followed** (low). Interoperability and discoverability suffer in generic STAC tools. *Fix:* Apply the stac-check suggestions shown with each finding.

**6. Missing documentation** (low). People and agents cannot tell what the data is or how to use it. *Fix:* Add README.md and AGENTS.md beside the catalog and each collection (and llms.txt at the root), linked from the STAC JSON.


## Spec version

- Latest spec: **0.3.0** (latest-release, commit `f758c6e5ec05`), requirements MUST 113, SHOULD 55, MAY 22
- Declared by the catalog: **0.1.2** (objects per version: {'0.1.2': 10})
- MUST failures against latest: 12; against declared: 12
- ⚠️ The catalog declares an older Portolan version than the latest (0.3.0).

## By format

| Format | Assets | Fully conformant | Unverified | Errors | Warnings |
|---|---:|---:|---:|---:|---:|
| GeoParquet | 9 | 0 (0%) | 9 | 0 | 0 |
| PMTiles | 1 | 0 (0%) | 1 | 0 | 0 |
| Other | 5 | 0 (0%) | 0 | 0 | 5 |

## Grades

Start at A; each best practice or recommendation not met (any MUST or SHOULD finding on the asset; for GeoParquet also Parquet v2 missing or unconfirmed) drops one level; floor F. Not a cloud-native format: F. No validator could read it: no grade. A only if every best practice is met.

5 graded, 10 not graded (unverified). A: 0, B: 0, C: 0, D: 0, E: 0, F: 5

| Format | A | B | C | D | E | F |
|---|---:|---:|---:|---:|---:|---:|
| Other | 0 | 0 | 0 | 0 | 0 | 5 |

| Grade | Asset | Format | Collection | Not met |
|:-:|---|---|---|---|
| **F** | ba.gpkg | geopackage | ba | `CNC-FMT-001` |
| **F** | ei.gpkg | geopackage | ei | `CNC-FMT-001` |
| **F** | ip.gpkg | geopackage | ip | `CNC-FMT-001` |
| **F** | nk.gpkg | geopackage | nk | `CNC-FMT-001` |
| **F** | UB.gpkg | geopackage | ub | `CNC-FMT-001` |

## By collection

| Collection | Scored assets | Fully conformant | Errors | Warnings |
|---|---:|---:|---:|---:|
| (catalog level) | 0 | 0 (n/a) | 0 | 2 |
| [ba](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json) | 2 | 0 (0%) | 1 | 17 |
| [ei](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json) | 2 | 0 (0%) | 1 | 17 |
| [hydro_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json) | 1 | 0 (0%) | 1 | 10 |
| [ip](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json) | 2 | 0 (0%) | 1 | 17 |
| [mfm-u_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json) | 1 | 0 (0%) | 1 | 9 |
| [naqua_regions](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json) | 2 | 0 (0%) | 4 | 18 |
| [nawa_trend_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json) | 1 | 0 (0%) | 1 | 9 |
| [nk](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json) | 2 | 0 (0%) | 1 | 17 |
| [ub](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json) | 2 | 0 (0%) | 1 | 17 |

## Changes since last run

0 new, 9 resolved.

**Resolved**

- `error` ba · stac-check `stac-check:invalid`: 
- `error` ei · stac-check `stac-check:invalid`: 
- `error` hydro_stations · stac-check `stac-check:invalid`: 
- `error` ip · stac-check `stac-check:invalid`: 
- `error` mfm-u_stations · stac-check `stac-check:invalid`: 
- `error` naqua_regions · stac-check `stac-check:invalid`: 
- `error` nawa_trend_stations · stac-check `stac-check:invalid`: 
- `error` nk · stac-check `stac-check:invalid`: 
- `error` ub · stac-check `stac-check:invalid`: 

## MUST failures (12)

Each entry ends with the command that reproduces it.

- **ba** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ei** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json
  ```

- **hydro_stations** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json
  ```

- **ip** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json
  ```

- **mfm-u_stations** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json
  ```

- **naqua_regions** · - · rashid 0.5.1 `PTL-AST-009`: PMTiles asset 'pmtiles' has no GeoParquet reference in its collection

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.1 `PTL-AST-009`: PMTiles asset 'pmtiles' has no visual role

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.1 `PTL-LIV-004`: host 'ron-portolan.s3.eu-central-1.amazonaws.com': Access-Control-Expose-Headers omits Accept-Ranges

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-LIV-004")'
  ```

- **naqua_regions** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json
  ```

- **nawa_trend_stations** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json
  ```

- **nk** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json
  ```

- **ub** · - · stac-validator 4.7.0 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.7.0 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json
  ```


## SHOULD warnings (133)

Each entry ends with the command that reproduces it.

- **(catalog)** · - · stac-check 2.0.0 `stac-check:best-practice`: Additional Information:

  ```sh
  uvx --from stac-check==2.0.0 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json
  ```

- **(catalog)** · llms.txt · docs-check native-0.1.0 `CNC-DOC-001`: llms.txt missing beside catalog

  ```sh
  curl -sS https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json | jq '.links[] | select(.rel == "llms")'
  curl -sSI https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/llms.txt
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'ba' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'ba' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'geopackage' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'geopackage' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'style' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'style' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'thumbnail' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-003`: asset 'thumbnail' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-010`: asset 'ba' has no description

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-010`: asset 'ba' has no title

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-010`: asset 'geopackage' has no description

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-010`: asset 'style' has no description

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-AST-010`: asset 'thumbnail' has no description

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-FIL-005`: README.md does not appear to mention the data's provenance

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
  ```

- **ba** · - · rashid 0.5.1 `PTL-FIL-005`: README.md does not appear to mention the license

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
  ```

- **ba** · - · stac-check 2.0.0 `stac-check:best-practice`: Additional Information:

  ```sh
  uvx --from stac-check==2.0.0 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ba** · ba.gpkg · cloud-native-classifier native-0.1.0 `CNC-FMT-001`: non-cloud-native asset: GeoPackage (application/geopackage+sqlite3)

  ```sh
  # STAC asset entry (type, roles):
  curl -sS https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json | jq '.assets["geopackage"]'
  # first bytes on the wire (magic number):
  curl -sS -r 0-15 https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.gpkg | xxd
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'ei' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'ei' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'geopackage' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'geopackage' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'style' has no file:checksum

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.1 `PTL-AST-003`: asset 'style' has no file:size

  ```sh
  uvx --from rashid==0.5.1 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- … and 108 more (see findings.csv, column `reproduce`)

## Checks

178 checks: 70 pass, 12 fail, 25 warn, 20 info, 51 skipped, 0 tool error. Every check, with what was observed and its command, is in `checks.csv` and in the HTML report.

## Reproduce this run

```sh
# Validators at the versions used in this run:
uv tool install --force rashid==0.5.1
uv tool install --force portolan-cli==0.9.0
uv tool install --force stac-valid==4.7.0
uv tool install --force stac-check==2.0.0
uv tool install --force geoparquet-io==1.8.0
uv tool install --force rasterio --with rio-cogeo==7.0.4
# pmtiles 1.31.2: https://github.com/protomaps/go-pmtiles/releases/tag/v1.31.2
# This repository at the same commit, then:
conformance run --config config.yaml --out reports/ --mode light --catalog bafu-portolan --max-asset-size-gb 2
# Spec: portolan-sdi/portolan-spec@v0.3.0 (f758c6e5ec05e411a19a276251bbbe3b8ba53916)
```

## Coverage

- copc: lightweight run (metadata and STAC only)
- gpio: lightweight run (metadata and STAC only)
- hosting-probe: lightweight run (metadata and STAC only)
- parquet-footer: lightweight run (metadata and STAC only)
- pmtiles: lightweight run (metadata and STAC only)
- portolan-cli: portolan-cli left out: `portolan check` only validates a local directory; it cannot check a remote catalog without a local copy. rashid covers the same requirements.
- rashid: Remote crawl: rashid reads only linked documents, so checks that need a directory listing (e.g. PTL-LNK-002 orphan objects, PTL-COL-005) did not run. (PTL-GEN-002)
- rio-cogeo: lightweight run (metadata and STAC only)
- zarr-probe: lightweight run (metadata and STAC only)

## Tool versions

| Tool | Version |
|---|---|
| cloud-native-classifier | native-0.1.0 |
| copc | native-0.1.0 |
| docs-check | native-0.1.0 |
| foen-portolan-conformance | 0.1.0 |
| gdal | 3.12.2 |
| gpio | 1.8.0 |
| hosting-probe | native-0.1.0 |
| parquet-footer | native-0.1.0 |
| pmtiles | 1.31.2 |
| portolan-cli | 0.9.0 |
| python | 3.14.4 |
| rashid | 0.5.1 |
| rio-cogeo | 7.0.4 |
| stac-check | 2.0.0 |
| stac-validator | 4.7.0 |
| uv | 0.13.10 |
| zarr-probe | native-0.1.0 |
