#!/usr/bin/env bash
# Install the newest release of every validator. Run on every CI run (and locally).
#   scripts/install-tools.sh            # Python tools + go-pmtiles + gpq
#   INSTALL_SYSTEM=1 scripts/install-tools.sh   # also apt: gdal-bin, pdal (needs sudo)
# Pin out a broken upstream release in constraints.txt (empty by default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${TOOLS_BIN:-$HOME/.local/bin}"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"

PY_TOOLS=(rashid portolan-cli stac-validator stac-check geoparquet-io)
for t in "${PY_TOOLS[@]}"; do
  echo "::group::uv tool install --upgrade $t"
  # A failed install must not abort the run: the report records "tool-missing" instead.
  uv tool install --upgrade --python 3.12 --constraints "$ROOT/constraints.txt" "$t" \
    || echo "::warning::could not install $t"
  echo "::endgroup::"
done

# `rio` is rasterio's entry point; rio-cogeo plugs into it.
echo "::group::uv tool install --upgrade rasterio --with rio-cogeo"
uv tool install --upgrade --python 3.12 --constraints "$ROOT/constraints.txt" rasterio --with rio-cogeo \
  || echo "::warning::could not install rio-cogeo"
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
install_release planetlabs/gpq "*linux*${arch/x86_64/amd64}*" gpq

if [ "${INSTALL_SYSTEM:-0}" = "1" ]; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq gdal-bin pdal || echo "::warning::apt install of gdal-bin/pdal failed"
fi

echo "== tool versions =="
for b in rashid portolan stac-validator stac-check gpio rio pmtiles gpq pdal gdalinfo; do
  printf '%-16s %s\n' "$b" "$(command -v "$b" >/dev/null && ($b --version 2>/dev/null || $b version 2>/dev/null) | head -1 || echo 'not installed')"
done
