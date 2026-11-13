#!/usr/bin/env bash
# Stage the verified v4 build for upload to your-hf-org/runb-az-v4 (D-49, D-50).
#
#   bash scripts/gpu/stage_v4_upload.sh data/processed/<verified build> <staging dir>
#
# Puts in <staging dir>: the three window files and the three document files, labels.json,
# DATA_CARD.md, and what the GPU needs beside them (model/train.py, scripts/gpu/run_v4.sh).
# Files are hard-linked, not copied (no extra disk space). Refuses when run_v4.sh's checksums
# are not filled in or do not match the build, so what is uploaded is what the GPU will accept.
# Prints the upload command; it uploads nothing itself.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BUILD=${1:?usage: stage_v4_upload.sh <build dir> <staging dir>}
STAGE=${2:?usage: stage_v4_upload.sh <build dir> <staging dir>}
RUN=${RUN:-$ROOT/scripts/gpu/run_v4.sh}   # RUN=scripts/gpu/run_v41.sh for v4.1
DATASET=${DATASET:-your-hf-org/runb-az-v4}

for f in train val test; do
  want=$(grep -o "\"$f.jsonl\": \"[^\"]*\"" "$RUN" | cut -d'"' -f4)
  got=$(shasum -a 256 "$BUILD/$f.jsonl" | cut -d' ' -f1)
  if [ "$want" != "$got" ]; then
    echo "$f.jsonl: run_v4.sh has '$want', the build has '$got': fill run_v4.sh with the verified checksums first"
    exit 1
  fi
  echo "$f.jsonl ${got:0:12} matches $(basename "$RUN")"
done

mkdir -p "$STAGE"
for f in train.jsonl val.jsonl test.jsonl train.docs.jsonl val.docs.jsonl test.docs.jsonl labels.json DATA_CARD.md; do
  ln -f "$BUILD/$f" "$STAGE/$f"
done
cp "$ROOT/model/train.py" "$RUN" "$STAGE/"
ls -la "$STAGE"
echo
echo "upload (needs a write token for your-hf-org):"
echo "  hf upload $DATASET $STAGE . --repo-type dataset --private --commit-message \"${DATASET#*/} (verified build)\""
