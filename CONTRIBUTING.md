# Contributing

Thanks for helping. Issues and pull requests are welcome in English, German, French or Italian.

## Set up

```bash
uv venv && uv pip install -e ".[parquet,dev]"
.venv/bin/pre-commit install
scripts/install-tools.sh          # optional: the real validators, for `pytest -m tools`
```

## Before you open a PR

- `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- `.venv/bin/pytest -q`
- New adapter or parser change? Add the tool's real output as a test case (see `AGENTS.md`).
- Keep findings deterministic and never invent `PORTO-…` requirement IDs.

Every PR runs the conformance checks against the configured catalogs and posts the summary as a comment.
Reports are only published from `main`.

## Reporting a wrong finding

Open an issue with the finding's `fingerprint`, `tool`, `tool_version` and `rule_id` from `report.json`,
and say why you think it is wrong. If the tool is wrong, please also report it upstream.
