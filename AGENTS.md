# AGENTS.md - maintaining foen-portolan-conformance

Instructions for coding agents (and humans) changing this repo.

## Layout

```
config.yaml                 catalogs, spec source, limits, which checks run
constraints.txt             pins for broken upstream tool releases (empty by default)
scripts/install-tools.sh    installs the newest release of every validator
src/conformance/
  cli.py                    `conformance run | regression | versions`
  runner.py                 spec -> crawl -> probe -> detect -> adapters -> findings
  crawl.py                  anonymous STAC crawl (JSON only, never asset bytes)
  http.py                   Fetcher (retries, range reads), RecordedTransport (offline replay)
  formats.py                detection (type > extension > magic) + PMTiles header parser
  spec.py                   latest-release resolution, requirements.yaml parsing
  toolchain.py              which / --version / --help introspection / subprocess with timeout
  normalize.py              Finding model, fingerprints, deterministic sort
  adapters/<tool>.py        one adapter per tool
  report/                   summary, markdown, html, build (json/csv/parquet/badge)
  regression.py             open/update/close logic for the regression issue
tests/                      pytest; `-m tools` needs the real validators
tests/fixtures/             mini catalog, recorded BAFU responses, binary fixture generator
```

## Rules

1. **Never write to the catalog.** No `--fix`, no `push`, no uploads. `portolan_cli.py` asserts this.
2. **Never download whole assets.** Use range reads (`Fetcher.get_range`) or tools that read remotely.
   Respect `ctx.too_big(asset)` (use `Adapter.per_asset`, which handles the size cap).
3. **One tool failing must not fail the run.** Return a `tool-error` finding (`Adapter.tool_error`);
   the runner also catches exceptions. The job fails only on infrastructure errors (exit 2).
4. **Check the current CLI before using a flag.** Use `toolchain.supports(binary, "--flag", *subcommand)`.
   Upstream tools change; do not hard-code flags that might disappear.
5. **Do not invent requirement IDs.** `spec_requirement_id` is set only from tool output (or a `PORTO-…`
   string found in it). Own checks use `CNC-…`, `PMT-…`, `ZARR-…`, `COPC-…`.
6. **Keep output deterministic.** Sort everything; keep timestamps and versions out of `Finding.fingerprint`.
   `tests/test_report.py::test_rerun_is_deterministic` must pass.
7. **Assets nobody validated are "unverified", never conformant.** Format adapters mark success through
   `per_asset` (return `None` from a check that could not look at the asset).

## Adding an adapter

1. Create `src/conformance/adapters/<tool>.py` with a subclass of `Adapter`: set `name`, `key` (config
   toggle), `binary`, `layer`, `light` (runs in the daily lightweight mode?), implement `jobs(ctx)`.
2. Put the output parsing in its own method and test it in `tests/test_adapters.py` with recorded output.
3. Register it in `adapters/__init__.py` (`ALL_ADAPTERS`), add the toggle to `config.yaml`,
   add the install line to `scripts/install-tools.sh`, and a real-tool test to `tests/test_tools.py`.
4. Document it in the README table.

## When a tool release breaks things

- The tool canary goes red with `tool-error` findings. Reproduce with `pytest -m tools -v`.
- Quick fix: add a pin to `constraints.txt` (e.g. `geoparquet-io<1.9`), commit, re-run.
- Proper fix: update the adapter's parser, add the new output as a test case, remove the pin.

## Commands

```bash
uv venv && uv pip install -e ".[parquet,dev]"
.venv/bin/pytest -q                 # unit tests, tools tests skip if tools are missing
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/conformance run --offline tests/fixtures/recorded/bafu/index.json --out /tmp/r
```
