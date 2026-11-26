# Portolan cloud-native conformance report

- **bafu-portolan**: BAFU Portolan <https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json> (9 collections, 0 items, 31 assets)

Run: 2026-11-26T13:13:33Z (light mode)

| | |
|---|---|
| Fully conformant assets | **0%** (0/15) |
| Assets without MUST failures | 33.3% (5/15) |
| Unverified assets (validator did not run) | 10 |
| MUST failures (errors) | **21** |
| SHOULD warnings | 133 |
| Coverage notes (skipped / tool issues) | 2 |

## Spec version

- Latest spec: **0.3.0** (latest-release, commit `f758c6e5ec05`), requirements MUST 113, SHOULD 55, MAY 22
- Declared by the catalog: **0.1.2** (objects per version: {'0.1.2': 10})
- MUST failures against latest: 21; against declared: 21
- ⚠️ The catalog declares an older Portolan version than the latest (0.3.0).

## By format

| Format | Assets | Fully conformant | Unverified | Errors | Warnings |
|---|---:|---:|---:|---:|---:|
| GeoParquet | 9 | 0 (0%) | 9 | 0 | 0 |
| PMTiles | 1 | 0 (0%) | 1 | 0 | 0 |
| Other | 5 | 0 (0%) | 0 | 0 | 5 |

## GeoParquet soft rating

0 of 9 GeoParquet assets rated. Grades: A 0, B 0, C 0, D 0, E 0. Not rated (gpio did not run): 9.

Method: pass=1, warn=0.5, fail=0; spec checks weigh 2, best-practice checks 1; A>=90, B>=75, C>=60, D>=40, else E; A only if every gpio recommendation is met and the file is Parquet v2, otherwise at best B. The rating does not change conformance.


## By collection

| Collection | Scored assets | Fully conformant | Errors | Warnings |
|---|---:|---:|---:|---:|
| (catalog level) | 0 | 0 (n/a) | 0 | 2 |
| [ba](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json) | 2 | 0 (0%) | 2 | 17 |
| [ei](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json) | 2 | 0 (0%) | 2 | 17 |
| [hydro_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json) | 1 | 0 (0%) | 2 | 10 |
| [ip](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json) | 2 | 0 (0%) | 2 | 17 |
| [mfm-u_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json) | 1 | 0 (0%) | 2 | 9 |
| [naqua_regions](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json) | 2 | 0 (0%) | 5 | 18 |
| [nawa_trend_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json) | 1 | 0 (0%) | 2 | 9 |
| [nk](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json) | 2 | 0 (0%) | 2 | 17 |
| [ub](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json) | 2 | 0 (0%) | 2 | 17 |

## Changes since last run

First run: this report is the baseline.

## MUST failures (21)

Each entry ends with the command that reproduces it.

- **ba** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ba** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ei** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json
  ```

- **ei** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json
  ```

- **hydro_stations** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json
  ```

- **hydro_stations** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json
  ```

- **ip** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json
  ```

- **ip** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json
  ```

- **mfm-u_stations** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json
  ```

- **mfm-u_stations** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json
  ```

- **naqua_regions** · - · rashid 0.5.0 `PTL-AST-009`: PMTiles asset 'pmtiles' has no GeoParquet reference in its collection

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.0 `PTL-AST-009`: PMTiles asset 'pmtiles' has no visual role

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.0 `PTL-LIV-004`: host 'ron-portolan.s3.eu-central-1.amazonaws.com': Access-Control-Expose-Headers omits Accept-Ranges

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-LIV-004")'
  ```

- **naqua_regions** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json
  ```

- **naqua_regions** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json
  ```

- **nawa_trend_stations** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json
  ```

- **nawa_trend_stations** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json
  ```

- **nk** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json
  ```

- **nk** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json
  ```

- **ub** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json
  ```

- **ub** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json
  ```


## SHOULD warnings (133)

Each entry ends with the command that reproduces it.

- **(catalog)** · - · stac-check 1.15.1 `stac-check:best-practice`: Additional Information:

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json
  ```

- **(catalog)** · llms.txt · docs-check native-0.1.0 `CNC-DOC-001`: llms.txt missing beside catalog

  ```sh
  curl -sS https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json | jq '.links[] | select(.rel == "llms")'
  curl -sSI https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/llms.txt
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'ba' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'ba' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'thumbnail' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'thumbnail' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'ba' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'ba' has no title

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'geopackage' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'style' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'thumbnail' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-FIL-005`: README.md does not appear to mention the data's provenance

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-FIL-005`: README.md does not appear to mention the license

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
  ```

- **ba** · - · stac-check 1.15.1 `stac-check:best-practice`: Additional Information:

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ba** · ba.gpkg · cloud-native-classifier native-0.1.0 `CNC-FMT-001`: non-cloud-native asset: GeoPackage (application/geopackage+sqlite3)

  ```sh
  # STAC asset entry (type, roles):
  curl -sS https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json | jq '.assets["geopackage"]'
  # first bytes on the wire (magic number):
  curl -sS -r 0-15 https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.gpkg | xxd
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'ei' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'ei' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ei** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --no-data | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- … and 108 more (see findings.csv, column `reproduce`)

## Checks

169 checks: 70 pass, 21 fail, 16 warn, 20 info, 42 skipped, 0 tool error. Every check, with what was observed and its command, is in `checks.csv` and in the HTML report.

## Reproduce this run

```sh
# Validators at the versions used in this run:
uv tool install --force rashid==0.5.0
uv tool install --force portolan-cli==0.9.0
uv tool install --force stac-valid==4.6.4
uv tool install --force stac-check==1.15.1
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
| gdal | 3.8.4 |
| gpio | 1.8.0 |
| hosting-probe | native-0.1.0 |
| pmtiles | 1.31.2 |
| portolan-cli | 0.9.0 |
| python | 3.12.3 |
| rashid | 0.5.0 |
| rio-cogeo | 7.0.4 |
| stac-check | 1.15.1 |
| stac-validator | 4.6.4 |
| uv | 0.13.10 |
| zarr-probe | native-0.1.0 |
