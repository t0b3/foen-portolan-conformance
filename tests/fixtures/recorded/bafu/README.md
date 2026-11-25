# Recorded responses: BAFU Portolan catalog

Metadata of `https://ron-portolan.s3.eu-central-1.amazonaws.com/portolan/catalog.json` and its
ten collections, captured on 2026-11-26. Used by the crawler tests and by the offline sample
report. Only the fields that the crawler and the native checks read were kept: links, assets,
`stac_extensions`, license and spatial extent. Long descriptions and `table:columns` were
dropped. Asset bytes and response headers are **not** recorded, so hosting and data checks
show up as "not recorded (offline)" coverage notes when this index is replayed.

Also recorded: the GitHub `releases/latest` response of `portolan-sdi/portolan-spec` (v0.3.0).
