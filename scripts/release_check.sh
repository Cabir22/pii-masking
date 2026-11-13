#!/usr/bin/env bash
# Release check for a candidate model in one command: score it, judge every
# go/no-go rule, fill docs/go_no_go.md and write a one-page PDF.
#
#   scripts/release_check.sh <model> <revision> [--quick | --bug-check] [--multilingual [--v3-bench F --v3-shadow F]] [--name TAG] [--bench-report FILE] [--keep-shadow] [--skip-real] [--gpu0]
#
#   <model>          Hub id or local checkpoint directory
#   <revision>       Hub commit SHA / branch / tag, or "-" for a local directory
#   --name TAG       run name (default: rc_<first 7 of revision>)
#   --bench-report   use this benchmark report for the candidate instead of scoring the benchmark
#   --keep-shadow    do not delete ~/pii-eval-private/shadow/ after scoring it (D-5 says delete)
#   --skip-real      skip real text (E1-E3 are then "not scored")
#   --quick          the verdict first: only the sets of the blocking rules (probes, real text, the
#                    benchmark, shadow-dev); runb_test (D1-D3, report-only) then runs in the background
#                    and refreshes the report when it is done. About 75 min CPU for a new model
#                    (benchmark ~31, shadow-dev ~34, probes ~5, loading ~5); the background part ~2 h
#   --shadow-saved   use only saved shadow-dev reports (never score or delete the set); the
#                    background part of --quick runs with it
#   --bug-check      a mid-training checkpoint (D-44b, e.g. revision "epoch1"): probes and the benchmark
#                    only, against Run B; never shadow-dev or real text, no verdict, no go_no_go.md.
#                    Writes reports/scoreboard/bug_check/<TAG>/bug_check.{json,md}. ~40 min CPU
#                    (+ ~2 min: 400 documents of Run B's test split for the long-document check)
#   --gpu0           a single-GPU machine: GPU 0 may be used too (default: only GPUs other than GPU 0,
#                    which is reserved on the shared server); also ALLOW_GPU0=1
#   --multilingual   a multilingual candidate (D-46): also golden_en / lang_tr / lang_ru (translated) and
#                    every independent real-text set that exists (~/pii-eval-private/real_text_<lang>),
#                    against checkpoint 1: A7 blocks (D-46b). With --v3-bench / --v3-shadow (v3's benchmark
#                    and shadow-dev reports), A10 checks every Azerbaijani label against v3 (D-46a)
#
# Steps, all with the prediction cache, tracks R and M, checkpoint 1 as the baseline:
#   1. scripts/score_runb.sh: probes, runb_test, real text (private) for both models
#   2. the benchmark (first 5,000, D-6) for the candidate; checkpoint 1's is
#      reports/scoreboard/baseline_ckpt1_benchmark.json
#   3. shadow-dev, only if restored (~/pii-eval-private/shadow/shadow_dev.jsonl): both models, then
#      the folder is deleted (D-5). The private D-42 policy list is applied if present. Without a
#      restored set, the newest saved private shadow-dev reports for the same model and revision
#      are used, and the check says so; otherwise A1-A6 are "not scored".
#   4. eval/release_check.py: every rule, the verdict, reports/scoreboard/release_check/<TAG>/
#      release_check.{json,md,pdf}, and this candidate's automatic section in docs/go_no_go.md
#
# Environment: DECIDE_TRACK (R or M: the track that decides; D-64a: M from m1 on), PREV_BENCH and PREV_NAME (B3),
#   PYTHON (default ~/pii-eval/envs/score-tok022/bin/python if present), CACHE_DIR,
# PRIVATE_DIR (default ~/pii-eval-private), RUNB_TEST, LOG_DIR, as in score_runb.sh.
set -euo pipefail
now() { date +%Y-%m-%dT%H:%M:%S%z; }  # GNU date -Is does not exist on macOS
{  # read the whole script before running it: a git pull during a long background wait cannot break it

usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 2 ] || usage
MODEL=$1; REV=$2; shift 2
TAG=""; BENCH_REPORT=""; KEEP_SHADOW=0; SKIP_REAL=(); QUICK=0; SHADOW_SAVED=0; BUG_CHECK=0; MULTI=0; V3_BENCH=""; V3_SHADOW=""
while [ $# -gt 0 ]; do
  case $1 in
    --name) TAG=$2; shift 2 ;;
    --bench-report) BENCH_REPORT=$2; shift 2 ;;
    --keep-shadow) KEEP_SHADOW=1; shift ;;
    --skip-real) SKIP_REAL=(--skip-real); shift ;;
    --quick) QUICK=1; shift ;;
    --shadow-saved) SHADOW_SAVED=1; shift ;;
    --bug-check) BUG_CHECK=1; shift ;;
    --multilingual) MULTI=1; shift ;;
    --v3-bench) V3_BENCH=$2; shift 2 ;;
    --v3-shadow) V3_SHADOW=$2; shift 2 ;;
    --gpu0) export ALLOW_GPU0=1; shift ;;
    *) usage ;;
  esac
done

ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -z "${PYTHON:-}" ]; then
  if [ -x "$HOME/pii-eval/envs/score-tok022/bin/python" ]; then PYTHON=$HOME/pii-eval/envs/score-tok022/bin/python; else PYTHON=python3; fi
fi
if [ -z "${CACHE_DIR:-}" ]; then
  if [ -d "$HOME/pii-eval/cache/pii-scoreboard-tok022" ]; then CACHE_DIR=$HOME/pii-eval/cache/pii-scoreboard-tok022
  else CACHE_DIR=$HOME/.cache/pii-scoreboard; fi
fi
PRIVATE_DIR=${PRIVATE_DIR:-$HOME/pii-eval-private}
export PYTHON CACHE_DIR PRIVATE_DIR
BASE_MODEL=${BASE_MODEL:-your-hf-org/masking-multilingual}   # or your-hf-org/masking-multilingual @ 2519392a (same weights, D-52a)
BASE_REV=${BASE_REV:-3a0a6e5df228bdc89dd01312a728e10a78b3e3fb}
[ -n "$TAG" ] || [ $BUG_CHECK = 0 ] || TAG=bc_$(basename "$MODEL")_${REV:0:12}
[ -n "$TAG" ] || { if [ "$REV" = "-" ]; then TAG=rc_$(basename "$MODEL"); else TAG=rc_${REV:0:7}; fi; }
PUB=$ROOT/reports/scoreboard/score_runb/$TAG
OUT=$ROOT/reports/scoreboard/release_check/$TAG
PRIV_REAL=$PRIVATE_DIR/real_text/reports/score_runb/$TAG
PRIV_SH=$PRIVATE_DIR/reports/release_check/$TAG
if [ -z "${LOG_DIR:-}" ]; then
  if [ -d "$HOME/pii-eval/logs" ]; then LOG_DIR=$HOME/pii-eval/logs; else LOG_DIR=$ROOT/logs; fi
fi
export LOG_DIR
mkdir -p "$LOG_DIR"

# One scoring run at a time (CPU: 8 threads). A quick run leaves a marker while it waits or runs, so
# the background runb_test of an earlier --quick never starts in front of the next seed's verdict.
prune_markers() {  # drop markers of quick runs that no longer exist (e.g. killed with SIGKILL)
  for m in "$LOG_DIR"/release_check.quick.*; do
    [ -e "$m" ] && ! ps -p "${m##*.}" >/dev/null 2>&1 && rm -f "$m"
  done
  return 0
}
prune_markers
# macOS has no flock: there the lock is skipped (run one release check at a time yourself)
if command -v flock >/dev/null 2>&1; then lock() { flock "$@" 9; }; else
  echo "flock not found (macOS?): no lock; run one release check at a time"; lock() { return 0; }; fi
exec 9>"$LOG_DIR/release_check.lock"
if [ "${RC_BACKGROUND:-0}" = 1 ]; then
  echo "background: waiting until no quick run waits or runs $(now)"
  while :; do
    prune_markers
    if compgen -G "$LOG_DIR/release_check.quick.*" >/dev/null; then sleep 60; continue; fi
    lock -n && break
    sleep 60
  done
else
  if [ $QUICK = 1 ] || [ $BUG_CHECK = 1 ]; then MARK=$LOG_DIR/release_check.quick.$$; touch "$MARK"; trap 'rm -f "$MARK"' EXIT; fi
  lock -n || { echo "another release check is scoring; waiting for it $(now)"; lock; }
fi
echo "release_check: $MODEL @ $REV; tag $TAG; python $PYTHON; cache $CACHE_DIR;${QUICK:+ quick=$QUICK;} $(now)"

# compute, as in score_runb.sh: a GPU other than GPU 0 (any GPU with --gpu0) with >= 8 GB free, else CPU, nice 19, 8 threads
GPU=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
      | awk -F', *' -v g0="${ALLOW_GPU0:-0}" '($1 != 0 || g0 == 1) && $2 >= 8192 {print $1; exit}' || true)
if [ -n "$GPU" ]; then export CUDA_VISIBLE_DEVICES=$GPU; NICE=""
else export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=8 MKL_NUM_THREADS=8; NICE="nice -n 19"; fi
export TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
score() {  # score <model> <rev> <set> <name> <out dir> [extra...]
  local model=$1 rev=$2 set=$3 name=$4 out=$5; shift 5
  local revarg=(); [ "$rev" != "-" ] && revarg=(--revision "$rev")
  mkdir -p "$out"
  echo "--- $name"
  $NICE "$PYTHON" "$ROOT/eval/scoreboard.py" --model "$model" ${revarg[@]+"${revarg[@]}"} --sets "$set" --tracks R,M \
    --name "$name" --out-dir "$out" --cache-dir "$CACHE_DIR" "$@" 2>&1 | grep --line-buffered -v -E "ETA|Loading weights" || true
  [ -f "$out/$name.json" ] || { echo "FAILED: $name"; exit 1; }
}

if [ $BUG_CHECK = 1 ]; then  # D-44b: probes + benchmark only, against Run B; no shadow-dev, no real text
  REF_MODEL=your-hf-org/masking-az-runb-v2-seed42-2ep; REF_REV=937f29d008f9f99d498e7686aa5e5dddf11ace14
  BC=$ROOT/reports/scoreboard/bug_check/$TAG
  NOPRIV=$ROOT/.no-private-sets  # never exists
  score "$MODEL" "$REV" probes new_probes "$BC" --private-dir "$NOPRIV"
  score "$MODEL" "$REV" benchmark new_benchmark "$BC" --private-dir "$NOPRIV"
  score "$REF_MODEL" "$REF_REV" probes runb_probes "$BC" --private-dir "$NOPRIV"
  score "$REF_MODEL" "$REF_REV" benchmark runb_benchmark "$BC" --private-dir "$NOPRIV"
  # long documents: the benchmark has none past one 512-token window, so a fixed sample of Run B's test split
  # (400 documents, seed 7, track R; generator data, never shadow-dev or real text) checks truncation
  WIN=()
  for f in "${RUNB_TEST:-}" "$ROOT/data/processed/runb/test.docs.jsonl" "$HOME/pii-eval/wt-runb-v2/data/processed/runb/test.docs.jsonl"; do
    if [ -n "$f" ] && [ -f "$f" ]; then
      score "$MODEL" "$REV" runb_test new_runb_sample "$BC" --private-dir "$NOPRIV" --runb-test "$f" --sample 400 --tracks R
      WIN=(--runb-test "$f"); break
    fi
  done
  [ ${#WIN[@]} -gt 0 ] || echo "long-document check skipped: Run B's test file not found (set RUNB_TEST)"
  "$PYTHON" "$ROOT/eval/bug_check.py" --name "$TAG" --probes-new "$BC/new_probes.json" --bench-new "$BC/new_benchmark.json" \
    --probes-ref "$BC/runb_probes.json" --bench-ref "$BC/runb_benchmark.json" --ref-model "$REF_MODEL" --ref-revision "$REF_REV" \
    --cache-dir "$CACHE_DIR" --out-dir "$BC" ${WIN[@]+"${WIN[@]}"}
  echo "BUG CHECK DONE $(now): $BC/bug_check.md"
  exit 0
fi

# 1. probes, runb_test, real text ---------------------------------------------------------------
RUNB_SKIP=(); [ $QUICK = 1 ] && RUNB_SKIP=(--skip-runb)
"$ROOT/scripts/score_runb.sh" "$MODEL" "$REV" --name "$TAG" ${SKIP_REAL[@]+"${SKIP_REAL[@]}"} ${RUNB_SKIP[@]+"${RUNB_SKIP[@]}"}

# 2. benchmark ---------------------------------------------------------------------------------
if [ -z "$BENCH_REPORT" ]; then
  score "$MODEL" "$REV" benchmark new_benchmark "$PUB" --private-dir "$ROOT/.no-private-sets"
  BENCH_REPORT=$PUB/new_benchmark.json
fi

# 3. shadow-dev --------------------------------------------------------------------------------
NEW_SHA=$("$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['meta']['revision_sha'])" "$PUB/new_probes.json")
SH_NEW=""; SH_BASE=""; SH_SOURCE="not scored (shadow-dev not restored, no saved report)"
if [ $SHADOW_SAVED = 0 ] && [ -f "$PRIVATE_DIR/shadow/shadow_dev.jsonl" ]; then
  ( umask 077; mkdir -p "$PRIV_SH" )
  score "$BASE_MODEL" "$BASE_REV" shadow_dev ckpt1_shadow_dev "$PRIV_SH" --private-dir "$PRIVATE_DIR/shadow"
  score "$MODEL" "$REV" shadow_dev new_shadow_dev "$PRIV_SH" --private-dir "$PRIVATE_DIR/shadow"
  SH_NEW=$PRIV_SH/new_shadow_dev.json; SH_BASE=$PRIV_SH/ckpt1_shadow_dev.json
  SH_SOURCE="scored $(date -u +%Y-%m-%d)"
  if [ $KEEP_SHADOW = 0 ]; then rm -rf "$PRIVATE_DIR/shadow"; echo "deleted $PRIVATE_DIR/shadow (D-5) $(now)"; fi
else
  read -r SH_NEW SH_BASE SH_DATE < <("$PYTHON" - "$PRIVATE_DIR/reports" "$MODEL" "$NEW_SHA" "$BASE_MODEL" "$BASE_REV" <<'EOF'
import json, sys
from pathlib import Path
root, model, sha, bmodel, bsha = sys.argv[1:]
def newest(m, s):
    best = None
    for p in Path(root).rglob("*shadow_dev.json"):
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))["meta"]
        except Exception:
            continue
        if meta.get("model") == m and meta.get("revision_sha") == s and (best is None or meta["date_utc"] > best[1]):
            best = (str(p), meta["date_utc"])
    return best
n, b = newest(model, sha), newest(bmodel, bsha)
print(n[0] if n else "-", b[0] if b else "-", n[1][:10] if n else "-")
EOF
)
  if [ "$SH_NEW" != "-" ] && [ "$SH_BASE" != "-" ]; then SH_SOURCE="saved report $SH_DATE (not restored)"; else SH_NEW=""; SH_BASE=""; fi
fi
echo "shadow-dev: $SH_SOURCE"

# 3b. multilingual (D-46) -------------------------------------------------------------------------
MULTI_ARGS=()
if [ $MULTI = 1 ]; then
  score "$MODEL" "$REV" golden_en,lang_tr,lang_ru new_langs "$PUB" --private-dir "$ROOT/.no-private-sets"
  MULTI_ARGS=(--multilingual --lang-new "$PUB/new_langs.json")
  RT_SETS=$(for l in en tr ru; do if compgen -G "$PRIVATE_DIR/real_text_$l/*.jsonl" >/dev/null; then printf "real_text_%s," $l; fi; done)
  if [ -n "$RT_SETS" ]; then  # checkpoint 1 from the cache: its A7 baseline on the independent sets
    ( umask 077; mkdir -p "$PRIV_REAL" )
    score "$BASE_MODEL" "$BASE_REV" "${RT_SETS%,}" ckpt1_real_langs "$PRIV_REAL" --private-dir "$PRIVATE_DIR"
    score "$MODEL" "$REV" "${RT_SETS%,}" new_real_langs "$PRIV_REAL" --private-dir "$PRIVATE_DIR"
    MULTI_ARGS+=(--real-lang-new "$PRIV_REAL/new_real_langs.json" --real-lang-base "$PRIV_REAL/ckpt1_real_langs.json")
  fi
  [ -n "$V3_BENCH" ] && MULTI_ARGS+=(--v3-bench "$V3_BENCH")
  [ -n "$V3_SHADOW" ] && MULTI_ARGS+=(--v3-shadow "$V3_SHADOW")
fi

# 4. judge -------------------------------------------------------------------------------------
REAL=(); [ -f "$PRIV_REAL/new_real_text.json" ] && REAL=(--real-new "$PRIV_REAL/new_real_text.json" --real-base "$PRIV_REAL/ckpt1_real_text.json")
SHADOW=(); [ -n "$SH_NEW" ] && SHADOW=(--shadow-new "$SH_NEW" --shadow-base "$SH_BASE")
RUNB=(); [ $QUICK = 0 ] && [ -f "$PUB/new_runb_test.json" ] && RUNB=(--runb-new "$PUB/new_runb_test.json" --runb-base "$PUB/ckpt1_runb_test.json")
"$PYTHON" "$ROOT/eval/release_check.py" --name "$TAG" \
  --probes-new "$PUB/new_probes.json" --probes-base "$PUB/ckpt1_probes.json" \
  ${RUNB[@]+"${RUNB[@]}"} --bench-new "$BENCH_REPORT" ${REAL[@]+"${REAL[@]}"} ${SHADOW[@]+"${SHADOW[@]}"} --shadow-source "$SH_SOURCE" \
  ${MULTI_ARGS[@]+"${MULTI_ARGS[@]}"} ${PREV_BENCH:+--prev-bench "$PREV_BENCH" --prev-name "${PREV_NAME:-the previous model}"} ${DECIDE_TRACK:+--track "$DECIDE_TRACK"} --cache-dir "$CACHE_DIR" --out-dir "$OUT" --go-no-go "$ROOT/docs/go_no_go.md"
echo "RELEASE CHECK DONE $(now): $OUT/release_check.pdf"

if [ $QUICK = 1 ]; then  # D1-D3: runb_test in the background, then the same report again with them
  BG_LOG=$LOG_DIR/release_check_${TAG}_runb_test_$(date +%Y%m%d_%H%M%S).log
  REVARG=$REV; [ "$REV" = "-" ] && REVARG=-
  SETSID=$(command -v setsid || true)  # not on macOS
  RC_BACKGROUND=1 nohup $SETSID "$ROOT/scripts/release_check.sh" "$MODEL" "$REVARG" --name "$TAG" --bench-report "$BENCH_REPORT" --shadow-saved \
    ${SKIP_REAL[@]+"${SKIP_REAL[@]}"} $( [ $MULTI = 1 ] && echo --multilingual ) ${V3_BENCH:+--v3-bench "$V3_BENCH"} ${V3_SHADOW:+--v3-shadow "$V3_SHADOW"} \
    > "$BG_LOG" 2>&1 < /dev/null 9>&- &
  echo "runb_test (D1-D3, report-only) continues in the background, after any other quick run: $BG_LOG"
fi
exit 0
}
