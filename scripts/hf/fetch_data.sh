#!/usr/bin/env bash
# Download the project's data from Hugging Face (D-73). A thin wrapper around fetch_data.py, which
# works on Windows, macOS and Linux and needs no `hf` command:
#
#   bash scripts/hf/fetch_data.sh                 # all of data/ (about 12 GB)
#   bash scripts/hf/fetch_data.sh data/benchmark_v3 data/golden    # only these folders
#   bash scripts/hf/fetch_data.sh --builds        # also the training mixes runb-az-v3 / -v4
#
# Or directly: python scripts/hf/fetch_data.py [same arguments]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-}
if [ -z "$PY" ]; then for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { PY=$c; break; }; done; fi
[ -n "$PY" ] || { echo "no python found: set PYTHON=/path/to/python"; exit 1; }
exec "$PY" "$HERE/fetch_data.py" "$@"
