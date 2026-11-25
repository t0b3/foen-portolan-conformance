#!/usr/bin/env bash
# Install the newest release of every validator. Run on every CI run (and locally).
#   scripts/install-tools.sh            # Python tools + go-pmtiles
#   INSTALL_SYSTEM=1 scripts/install-tools.sh   # also apt: gdal-bin, pdal (needs sudo)
# Pin out a broken upstream release in constraints.txt (empty by default).
#
# REQUIRED_TOOLS (default: "stac-validator") must install AND pass a smoke test, otherwise the
# script exits 1 and the workflow fails. Other tools are best effort: a failed install is
# recorded in the report as "tool-missing".
set -euo pipefail
REQUIRED_TOOLS="${REQUIRED_TOOLS:-stac-validator}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Newest Python for which every validator's dependencies ship wheels. Not 3.15 yet: gpio pins
# duckdb<1.6 and duckdb 1.5.x has no 3.15 wheels (checked 2026-11-26). Override with PYTHON_VERSION.
PYTHON="${PYTHON_VERSION:-3.14}"
BIN="${TOOLS_BIN:-$HOME/.local/bin}"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"

# Only pass --constraints when constraints.txt actually pins something.
CONSTRAINTS=()
if grep -qvE '^\s*(#|$)' "$ROOT/constraints.txt" 2>/dev/null; then
  CONSTRAINTS=(--constraints "$ROOT/constraints.txt")
fi

uv_install() {  # package [extra uv args...]; retries once (PyPI hiccups)
  local pkg="$1"; shift
  for attempt in 1 2; do
    if uv tool install --upgrade --python "$PYTHON" ${CONSTRAINTS[@]+"${CONSTRAINTS[@]}"} "$pkg" "$@"; then
      return 0
    fi
    echo "install of $pkg failed (attempt $attempt)"; sleep 5
  done
  return 1
}

# PyPI package names. stac-validator was renamed to stac-valid (4.2.0+); the old name is now an
# alias without code, so `uv tool install stac-validator` fails ("no executables"). stac-valid
# still provides the `stac-validator` command.
PY_TOOLS=(stac-valid rashid portolan-cli stac-check geoparquet-io)
for t in "${PY_TOOLS[@]}"; do
  echo "::group::uv tool install --upgrade $t"
  uv_install "$t" || echo "::warning::could not install $t"
  echo "::endgroup::"
done

# `rio` is rasterio's entry point; rio-cogeo plugs into it.
echo "::group::uv tool install --upgrade rasterio --with rio-cogeo"
uv_install rasterio --with rio-cogeo || echo "::warning::could not install rio-cogeo"
echo "::endgroup::"

# Latest GitHub release binaries (gh is preinstalled on GitHub runners).
arch="$(uname -m)"; [ "$arch" = "aarch64" ] && arch=arm64
tmp="$(mktemp -d)"
install_release() {  # repo, asset glob, binary name
  local repo="$1" pattern="$2" name="$3"
  if gh release download --repo "$repo" --pattern "$pattern" --dir "$tmp/$name" --clobber 2>/dev/null; then
    local f; f="$(ls "$tmp/$name" | head -1)"
    case "$f" in
      *.tar.gz|*.tgz) tar -xzf "$tmp/$name/$f" -C "$tmp/$name" ;;
      *.zip) unzip -oq "$tmp/$name/$f" -d "$tmp/$name" ;;
    esac
    local b; b="$(find "$tmp/$name" -type f -name "$name" | head -1)"
    if [ -n "$b" ]; then install -m 0755 "$b" "$BIN/$name"; echo "installed $name from $repo"; return; fi
  fi
  echo "::warning::could not install $name from $repo (pattern $pattern)"
}
install_release protomaps/go-pmtiles "*Linux_${arch/amd64/x86_64}.tar.gz" pmtiles

if [ "${INSTALL_SYSTEM:-0}" = "1" ]; then
  sudo apt-get update -qq
  # One package per call: a package missing from the runner's repos (pdal is not in Ubuntu
  # 24.04's default archive) must not stop the others from installing.
  for pkg in gdal-bin pdal; do
    sudo apt-get install -y -qq "$pkg" || echo "::warning::apt package $pkg not available; checks that need it are reported as tool-missing"
  done
fi

# Required tools: must be on PATH and pass a smoke test against the bundled mini catalog.
smoke() {
  case "$1" in
    stac-validator)
      # Validates a local Collection; stac-validator fetches the official JSON schemas over HTTPS.
      # 4.x validates with `stac-validator validate <path>`; 3.x took the path directly.
      local sv=(stac-validator)
      if stac-validator --help 2>/dev/null | grep -qE '^[[:space:]]*validate\b'; then sv+=(validate); fi
      echo "smoke test: ${sv[*]} tests/fixtures/smoke/collection.json"
      "${sv[@]}" "$ROOT/tests/fixtures/smoke/collection.json" | tee /tmp/stac-validator-smoke.json
      grep -Eq '"valid_stac":[[:space:]]*true' /tmp/stac-validator-smoke.json ;;
    *) command -v "$1" >/dev/null ;;
  esac
}
failed=0
for t in $REQUIRED_TOOLS; do
  if ! command -v "$t" >/dev/null; then
    echo "::error::required tool $t is not installed (see the install log above)"; failed=1; continue
  fi
  if ! smoke "$t"; then
    echo "::error::required tool $t is installed but its smoke test failed"; failed=1
  else
    echo "required tool $t: OK ($(command -v "$t"))"
  fi
done

# Version of a command: --version, then `version`, then the uv tool that provides it
# (stac-validator 4.x has no version flag).
tool_version() {
  local b="$1" v=""
  command -v "$b" >/dev/null || { echo "not installed"; return; }
  v="$("$b" --version 2>/dev/null | head -1)" || true
  [ -n "$v" ] || v="$("$b" version 2>/dev/null | head -1)" || true
  [ -n "$v" ] || v="$(uv tool list 2>/dev/null | awk -v exe="- $b" '/^[^ -]/ {pkg=$0} $0 == exe {print pkg}' | head -1)" || true
  echo "${v:-installed (version unknown)}"
}
echo "== tool versions =="
for b in rashid portolan stac-validator stac-check gpio rio pmtiles pdal gdalinfo; do
  printf '%-16s %s\n' "$b" "$(tool_version "$b")"
done

[ "$failed" = 0 ] || exit 1
