#!/usr/bin/env bash
# Make the history copy for the repository move: this repository without the Git LFS data
# (every data/**/*.jsonl, now in your-hf-org/pii-masking-data). Every commit, message, author and
# branch is kept; only those files leave the history. Nothing here is pushed anywhere.
#
#   bash scripts/hf/make_clean_repo.sh <out dir>      # e.g. ~/pii-clean.git (a bare mirror)
#   cd <out dir> && git push --mirror <new repo URL>  # on move day, after checking
#
# Needs git-filter-repo (brew install git-filter-repo). About a minute; 17 GB -> about 80 MB.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?usage: make_clean_repo.sh <out dir>}
[ -e "$OUT" ] && { echo "$OUT exists: remove it or choose another"; exit 1; }
command -v git-filter-repo >/dev/null || { echo "git-filter-repo not found: brew install git-filter-repo"; exit 1; }
git -C "$ROOT" fetch -q origin
GIT_LFS_SKIP_SMUDGE=1 git clone -q --mirror --no-local "$ROOT" "$OUT"
cd "$OUT"
git filter-repo --force --prune-empty never --prune-degenerate never --path-glob 'data/*.jsonl' --invert-paths
git remote remove origin 2>/dev/null || true
git reflog expire --expire=now --all && git gc -q --prune=now --aggressive
echo "commits: $(git rev-list --all | wc -l | tr -d ' '); refs: $(git for-each-ref | wc -l | tr -d ' '); size: $(du -sh . | cut -f1)"
echo "data .jsonl left in main: $(git ls-tree -r main --name-only | grep -c '^data/.*\.jsonl$' || true)"
