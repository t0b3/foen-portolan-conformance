# Portolan cloud-native conformance report

- **bafu-portolan**: BAFU Portolan <https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json> (9 collections, 0 items, 31 assets)

Run: 2026-11-26T14:35:43Z (full mode)

| | |
|---|---|
| Fully conformant assets | **0%** (0/15) |
| Assets without MUST failures | 66.7% (10/15) |
| Unverified assets (validator did not run) | 0 |
| MUST failures (errors) | **35** |
| SHOULD warnings | 189 |
| Coverage notes (skipped / tool issues) | 2 |

## Where to start: anti-patterns by severity

| # | Severity | Anti-pattern | Assets | Findings (MUST / SHOULD) | Rules |
|---:|---|---|---:|---|---|
| 1 | critical | **Invalid or broken files and metadata** | 5 | 23 (23 / 0) | `stac-check:invalid` ×9, `stac-validator:Exception` ×9, `gpio:spec:geometry-types-match-data-geometry` ×4, `pmtiles:verify` ×1 |
| 2 | critical | **Data not in a cloud-native format** | 5 | 5 (0 / 5) | `CNC-FMT-001` ×5 |
| 3 | high | **Portolan MUST requirements broken** | 0 | 4 (4 / 0) | `PTL-AST-009` ×2, `PTL-DAT-007` ×1, `PTL-LIV-004` ×1 |
| 4 | medium | **Metadata does not match the data** | 14 | 14 (0 / 14) | `CNC-HOST-005` ×14 |
| 5 | medium | **No spatial index or ordering** | 9 | 24 (0 / 24) | `gpio:all:warning` ×9, `PTL-DAT-007` ×8, `PTL-DAT-006` ×4, `PTL-DAT-005` ×3 |
| 6 | medium | **Inefficient storage layout** | 9 | 9 (0 / 9) | `CNC-PQ-001` ×8, `gpio:all:warning` ×1 |
| 7 | medium | **Portolan recommendations (SHOULD) not followed** | 0 | 126 (0 / 126) | `PTL-AST-003` ×62, `PTL-AST-010` ×40, `PTL-FIL-005` ×15, `PTL-DAT-020` ×9 |
| 8 | low | **Other best practices not met** | 4 | 8 (8 / 0) | `gpio:all:1-failed-23-passed` ×4, `gpio:all:error` ×4 |
| 9 | low | **STAC best practices not followed** | 0 | 10 (0 / 10) | `stac-check:best-practice` ×10 |
| 10 | low | **Missing documentation** | 0 | 1 (0 / 1) | `CNC-DOC-001` ×1 |

**1. Invalid or broken files and metadata** (critical). Readers may reject the file or silently misread it. *Fix:* Fix the reported validation errors; re-run the tool command shown with each finding.

**2. Data not in a cloud-native format** (critical). Clients must download the whole file before reading anything; no partial or remote reads. *Fix:* Convert: vector to GeoParquet (`gpio convert`), raster to COG (`rio cogeo create`), tiles to PMTiles. Keep the old format only as an extra download.

**3. Portolan MUST requirements broken** (high). The catalog does not meet the Portolan specification it declares. *Fix:* Follow the requirement text linked with each finding (rashid rule and PORTO- ID).

**4. Metadata does not match the data** (medium). Catalog search and clients make wrong assumptions: wrong format, extent or licence. *Fix:* Set the STAC asset `type` to the registered media type, keep bboxes in sync with the data, declare the Portolan extension and a licence.

**5. No spatial index or ordering** (medium). A query for a small area still reads most of the file. *Fix:* GeoParquet: sort spatially (`gpio sort hilbert`) and add a bbox covering column (see `gpio add --help`). COG: internal tiling and overviews. PMTiles: write a clustered archive.

**6. Inefficient storage layout** (medium). More bytes and more requests than needed for every read. *Fix:* GeoParquet: Parquet format v2, ZSTD compression, row groups of roughly 64-256 MB (`gpio convert`). COG: DEFLATE/ZSTD/LERC compression. Zarr: consolidated metadata.

**7. Portolan recommendations (SHOULD) not followed** (medium). Not wrong, but harder to find, use or trust than the spec intends. *Fix:* Follow the requirement text linked with each finding.

**8. Other best practices not met** (low). Reported by a validator but not matched to a general pattern above. *Fix:* See the tool message and the reproduce command with each finding.

**9. STAC best practices not followed** (low). Interoperability and discoverability suffer in generic STAC tools. *Fix:* Apply the stac-check suggestions shown with each finding.

**10. Missing documentation** (low). People and agents cannot tell what the data is or how to use it. *Fix:* Add README.md and AGENTS.md beside the catalog and each collection (and llms.txt at the root), linked from the STAC JSON.


## Spec version

- Latest spec: **0.3.0** (latest-release, commit `f758c6e5ec05`), requirements MUST 113, SHOULD 55, MAY 22
- Declared by the catalog: **0.1.2** (objects per version: {'0.1.2': 10})
- MUST failures against latest: 35; against declared: 35
- ⚠️ The catalog declares an older Portolan version than the latest (0.3.0).

## By format

| Format | Assets | Fully conformant | Unverified | Errors | Warnings |
|---|---:|---:|---:|---:|---:|
| GeoParquet | 9 | 0 (0%) | 0 | 12 | 27 |
| PMTiles | 1 | 0 (0%) | 0 | 1 | 0 |
| Other | 5 | 0 (0%) | 0 | 0 | 10 |

## Grades

Start at A; each best practice or recommendation not met (any MUST or SHOULD finding on the asset; for GeoParquet also Parquet v2 missing or unconfirmed) drops one level; floor F. Not a cloud-native format: F. No validator could read it: no grade. A only if every best practice is met.

15 graded, 0 not graded (unverified). A: 0, B: 1, C: 0, D: 5, E: 0, F: 9

| Format | A | B | C | D | E | F |
|---|---:|---:|---:|---:|---:|---:|
| GeoParquet | 0 | 0 | 0 | 5 | 0 | 4 |
| PMTiles | 0 | 1 | 0 | 0 | 0 | 0 |
| Other | 0 | 0 | 0 | 0 | 0 | 5 |

| Grade | Asset | Format | Collection | Not met |
|:-:|---|---|---|---|
| **B** | naqua_regions.pmtiles | pmtiles | naqua_regions | `pmtiles:verify` |
| **D** | hydro_stations.parquet | geoparquet | hydro_stations | `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **D** | mfm-u_stations.parquet | geoparquet | mfm-u_stations | `CNC-HOST-005`; `gpio:all:warning`; `gpio:all:warning` |
| **D** | naqua_regions.parquet | geoparquet | naqua_regions | `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **D** | nawa_trend_stations.parquet | geoparquet | nawa_trend_stations | `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **D** | UB.parquet | geoparquet | ub | `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **F** | ba.gpkg | geopackage | ba | `CNC-FMT-001` |
| **F** | ba.parquet | geoparquet | ba | `gpio:all:1-failed-23-passed`; `gpio:all:error`; `gpio:spec:geometry-types-match-data-geometry`; `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **F** | ei.gpkg | geopackage | ei | `CNC-FMT-001` |
| **F** | ei.parquet | geoparquet | ei | `gpio:all:1-failed-23-passed`; `gpio:all:error`; `gpio:spec:geometry-types-match-data-geometry`; `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **F** | ip.gpkg | geopackage | ip | `CNC-FMT-001` |
| **F** | ip.parquet | geoparquet | ip | `gpio:all:1-failed-23-passed`; `gpio:all:error`; `gpio:spec:geometry-types-match-data-geometry`; `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **F** | nk.gpkg | geopackage | nk | `CNC-FMT-001` |
| **F** | nk.parquet | geoparquet | nk | `gpio:all:1-failed-23-passed`; `gpio:all:error`; `gpio:spec:geometry-types-match-data-geometry`; `CNC-HOST-005`; `CNC-PQ-001`; `gpio:all:warning` |
| **F** | UB.gpkg | geopackage | ub | `CNC-FMT-001` |

## By collection

| Collection | Scored assets | Fully conformant | Errors | Warnings |
|---|---:|---:|---:|---:|
| (catalog level) | 0 | 0 (n/a) | 0 | 2 |
| [ba](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json) | 2 | 0 (0%) | 5 | 23 |
| [ei](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json) | 2 | 0 (0%) | 5 | 25 |
| [hydro_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/hydro_stations/collection.json) | 1 | 0 (0%) | 2 | 16 |
| [ip](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/collection.json) | 2 | 0 (0%) | 5 | 25 |
| [mfm-u_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/mfm-u_stations/collection.json) | 1 | 0 (0%) | 3 | 13 |
| [naqua_regions](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json) | 2 | 0 (0%) | 6 | 23 |
| [nawa_trend_stations](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nawa_trend_stations/collection.json) | 1 | 0 (0%) | 2 | 14 |
| [nk](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/nk/collection.json) | 2 | 0 (0%) | 5 | 24 |
| [ub](https://browser.portolan-sdi.org/#/external/ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ub/collection.json) | 2 | 0 (0%) | 2 | 24 |

## Changes since last run

8 new, 0 resolved.

**New**

- `warning` ba · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` ei · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` hydro_stations · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` ip · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` naqua_regions · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` nawa_trend_stations · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` nk · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)
- `warning` ub · parquet-footer `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)

## MUST failures (35)

Each entry ends with the command that reproduces it.

- **ba** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ba** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/collection.json
  ```

- **ba** · ba.parquet · gpio 1.8.0 `gpio:all:1-failed-23-passed`: 1 failed, 23 passed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet
  ```

- **ba** · ba.parquet · gpio 1.8.0 `gpio:all:error`: ERROR: ba.parquet - Spec validation: 1 checks failed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet
  ```

- **ba** · ba.parquet · gpio 1.8.0 `gpio:spec:geometry-types-match-data-geometry`: found undeclared geometry types: {'MultiPolygon Z'} (162 checked)

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check spec https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet --json
  ```

- **ei** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json
  ```

- **ei** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/collection.json
  ```

- **ei** · ei.parquet · gpio 1.8.0 `gpio:all:1-failed-23-passed`: 1 failed, 23 passed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/ei.parquet
  ```

- **ei** · ei.parquet · gpio 1.8.0 `gpio:all:error`: ERROR: ei.parquet - Spec validation: 1 checks failed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/ei.parquet
  ```

- **ei** · ei.parquet · gpio 1.8.0 `gpio:spec:geometry-types-match-data-geometry`: found undeclared geometry types: {'MultiLineString Z'} (483 checked)

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check spec https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ei/ei.parquet --json
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

- **ip** · ip.parquet · gpio 1.8.0 `gpio:all:1-failed-23-passed`: 1 failed, 23 passed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/ip.parquet
  ```

- **ip** · ip.parquet · gpio 1.8.0 `gpio:all:error`: ERROR: ip.parquet - Spec validation: 1 checks failed

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/ip.parquet
  ```

- **ip** · ip.parquet · gpio 1.8.0 `gpio:spec:geometry-types-match-data-geometry`: found undeclared geometry types: {'Point Z'} (314 checked)

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check spec https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ip/ip.parquet --json
  ```

- **mfm-u_stations** · - · rashid 0.5.0 `PTL-DAT-007`: asset 'mfm-u_stations' provides no per-row-group spatial statistics (no bbox covering column with min/max stats, nor native GeospatialStatistics)

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-DAT-007")'
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
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.0 `PTL-AST-009`: PMTiles asset 'pmtiles' has no visual role

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-009")'
  ```

- **naqua_regions** · - · rashid 0.5.0 `PTL-LIV-004`: host 'ron-portolan.s3.eu-central-1.amazonaws.com': Access-Control-Expose-Headers omits Accept-Ranges

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-LIV-004")'
  ```

- **naqua_regions** · - · stac-check 1.15.1 `stac-check:invalid`: 

  ```sh
  uvx --from stac-check==1.15.1 stac-check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json
  ```

- **naqua_regions** · - · stac-validator 4.6.4 `stac-validator:Exception`: 'list' object has no attribute 'get' [Schema: https://schemas.portolan-sdi.org/portolan/v0.1.2/schema.json]. Error in Extensions.

  ```sh
  uvx --from stac-valid==4.6.4 stac-validator validate https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/naqua_regions/collection.json
  ```

- … and 10 more (see findings.csv, column `reproduce`)

## SHOULD warnings (189)

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
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'ba' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'geopackage' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'style' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'thumbnail' has no file:checksum

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-003`: asset 'thumbnail' has no file:size

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-003")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'ba' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'ba' has no title

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'geopackage' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'style' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-AST-010`: asset 'thumbnail' has no description

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-AST-010")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-DAT-007`: asset 'ba' relies on native GeospatialStatistics without a bbox covering column; a covering column remains recommended for page-level pruning

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-DAT-007")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-DAT-020`: asset 'ba': 14 of 14 table:columns entries carry no description (BA_ID, BA_Name, BA_Alt_min, BA_Alt_moy, BA_Alt_max, and 9 more). If the dataset is a mirror and the source has no descriptions, note this in the collection README.

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-DAT-020")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-FIL-005`: README.md does not appear to mention the data's provenance

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
  ```

- **ba** · - · rashid 0.5.0 `PTL-FIL-005`: README.md does not appear to mention the license

  ```sh
  uvx --from rashid==0.5.0 rashid check https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json --json --all --schema --live | jq '.findings[] | select(.rule_id == "PTL-FIL-005")'
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

- **ba** · ba.gpkg · hosting-probe native-0.1.0 `CNC-HOST-005`: Served Content-Type 'binary/octet-stream' differs from the STAC asset type 'application/geopackage+sqlite3'

  ```sh
  curl -sS -D - -o /dev/null -H 'Origin: https://browser.portolan-sdi.org' -H 'Range: bytes=0-1023' https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.gpkg
  ```

- **ba** · ba.parquet · gpio 1.8.0 `gpio:all:warning`: WARNING: ba.parquet - No bbox column found

  ```sh
  uvx --from geoparquet-io==1.8.0 gpio check all https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet
  ```

- **ba** · ba.parquet · hosting-probe native-0.1.0 `CNC-HOST-005`: Served Content-Type 'binary/octet-stream' differs from the STAC asset type 'application/x-parquet'

  ```sh
  curl -sS -D - -o /dev/null -H 'Origin: https://browser.portolan-sdi.org' -H 'Range: bytes=0-1023' https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet
  ```

- **ba** · ba.parquet · parquet-footer native-0.1.0 `CNC-PQ-001`: Parquet format v1, not v2 (rewrite with format version 2.x and data page v2)

  ```sh
  # Last 8 bytes: footer length (u32 little-endian) + 'PAR1':
  curl -sS -r -8 https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet | xxd
  # Or let pyarrow read the footer (range requests only):
  uvx --with pyarrow --with fsspec --with aiohttp python -c 'import sys, fsspec, pyarrow.parquet as pq; m = pq.ParquetFile(fsspec.open(sys.argv[1]).open()).metadata; print("format_version", m.format_version, "| created_by", m.created_by)' https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/ba/ba.parquet
  ```

- … and 164 more (see findings.csv, column `reproduce`)

## Checks

675 checks: 487 pass, 43 fail, 69 warn, 75 info, 1 skipped, 0 tool error. Every check, with what was observed and its command, is in `checks.csv` and in the HTML report.

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
conformance run --config config.yaml --out reports/ --mode full --catalog bafu-portolan --max-asset-size-gb 2
# Spec: portolan-sdi/portolan-spec@v0.3.0 (f758c6e5ec05e411a19a276251bbbe3b8ba53916)
```

## Coverage

- portolan-cli: portolan-cli left out: `portolan check` only validates a local directory; it cannot check a remote catalog without a local copy. rashid covers the same requirements.
- rashid: Remote crawl: rashid reads only linked documents, so checks that need a directory listing (e.g. PTL-LNK-002 orphan objects, PTL-COL-005) did not run. (PTL-GEN-002)

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
| rashid | 0.5.0 |
| rio-cogeo | 7.0.4 |
| stac-check | 1.15.1 |
| stac-validator | 4.6.4 |
| uv | 0.13.10 |
| zarr-probe | native-0.1.0 |
