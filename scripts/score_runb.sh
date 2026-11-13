#!/usr/bin/env bash
# Score a Run B checkpoint against checkpoint 1 in one command.
#
#   scripts/score_runb.sh <model> <revision> [--sample N] [--name TAG] [--tracks R,M] [--skip-real] [--skip-runb]
#
#   <model>     Hub id or local checkpoint directory
#   <revision>  Hub commit SHA / branch / tag, or "-" for a local directory
#   --sample N  score only a seeded sample of N runb_test documents (a smoke test;
#               the probes and real text are always scored whole)
#   --name TAG  run name (default: runb_<first 7 of revision> or the directory name)
#   --skip-runb skip runb_test (report-only in the go/no-go; release_check.sh --quick)
#
# Runs, for checkpoint 1 (your-hf-org/masking-multilingual @ 3a0a6e5, from the
# prediction cache) and for <model>, on tracks R and M:
#   probes     eval/probes/ (48 families, targets)
#   runb_test  Run B v2's test split (D-28; old/new and old-corpus/new-data splits
#              from eval/runb_v2_test_parts.tsv.gz)
#   real_text  ~/pii-eval-private/real_text/ (results stay in that folder)
# then writes the comparison with eval/compare_runs.py:
#   public   reports/scoreboard/score_runb/<TAG>/compare.md  (+ the per-run reports)
#   private  ~/pii-eval-private/real_text/reports/score_runb/<TAG>/compare_real_text.md
#
# Compute: the first GPU other than GPU 0 (any GPU with ALLOW_GPU0=1, release_check.sh --gpu0)
# with >= 8 GB free; otherwise CPU with
# nice -n 19 and 8 threads. Other people's processes are never touched.
#
# Environment: PYTHON (default python3, needs torch + transformers), RUNB_TEST
# (path to v2's test.docs.jsonl), CACHE_DIR, PRIVATE_DIR (default ~/pii-eval-private),
# LOG_DIR (default ~/pii-eval/logs, else ./logs), ALLOW_OTHER_TEST=1 to score a test
# file whose SHA-256 is not D-28's.
set -euo pipefail
now() { date +%Y-%m-%dT%H:%M:%S%z; }  # GNU date -Is does not exist on macOS

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 2 ] || usage
MODEL=$1; REV=$2; shift 2
SAMPLE=""; TAG=""; TRACKS="R,M"; SKIP_REAL=0; SKIP_RUNB=0
while [ $# -gt 0 ]; do
  case $1 in
    --sample) SAMPLE=$2; shift 2 ;;
    --name) TAG=$2; shift 2 ;;
    --tracks) TRACKS=$2; shift 2 ;;
    --skip-real) SKIP_REAL=1; shift ;;
    --skip-runb) SKIP_RUNB=1; shift ;;
    *) usage ;;
  esac
done

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
BASE_MODEL=${BASE_MODEL:-your-hf-org/masking-multilingual}   # or your-hf-org/masking-multilingual @ 2519392a (same weights, D-52a)
BASE_REV=${BASE_REV:-3a0a6e5df228bdc89dd01312a728e10a78b3e3fb}
D28_TEST_SHA=3254d8ad51cd41e06cb6cf92093d725beafaec2b6e106691feca7ed719c45bd1
PRIVATE_DIR=${PRIVATE_DIR:-$HOME/pii-eval-private}
if [ -z "${CACHE_DIR:-}" ]; then
  # never the old ~/pii-eval/cache/pii-scoreboard: its predictions came from tokenizers 0.23.2 (D-37)
  if [ -d "$HOME/pii-eval/cache/pii-scoreboard-tok022" ]; then CACHE_DIR=$HOME/pii-eval/cache/pii-scoreboard-tok022
  else CACHE_DIR=$HOME/.cache/pii-scoreboard; fi
fi
if [ -z "${LOG_DIR:-}" ]; then
  if [ -d "$HOME/pii-eval/logs" ]; then LOG_DIR=$HOME/pii-eval/logs; else LOG_DIR=$ROOT/logs; fi
fi
if [ -z "${RUNB_TEST:-}" ]; then
  for p in "$ROOT/data/processed/runb/test.docs.jsonl" "$HOME/pii-eval/wt-runb-v2/data/processed/runb/test.docs.jsonl"; do
    [ -f "$p" ] && { RUNB_TEST=$p; break; }
  done
fi
[ -n "${RUNB_TEST:-}" ] && [ -f "$RUNB_TEST" ] || { echo "Run B test file not found: set RUNB_TEST"; exit 1; }
sha=$( { command -v sha256sum >/dev/null 2>&1 && sha256sum "$RUNB_TEST" || shasum -a 256 "$RUNB_TEST"; } | cut -d' ' -f1)  # macOS: shasum
if [ "$sha" != "$D28_TEST_SHA" ] && [ "${ALLOW_OTHER_TEST:-0}" != 1 ]; then
  echo "$RUNB_TEST has SHA-256 $sha, not D-28's $D28_TEST_SHA (set ALLOW_OTHER_TEST=1 to score it anyway)"; exit 1
fi

if [ -z "$TAG" ]; then
  if [ "$REV" = "-" ]; then TAG=runb_$(basename "$MODEL"); else TAG=runb_${REV:0:7}; fi
  [ -n "$SAMPLE" ] && TAG=${TAG}_sample$SAMPLE
fi
PUB=$ROOT/reports/scoreboard/score_runb/$TAG
PRIV=$PRIVATE_DIR/real_text/reports/score_runb/$TAG
mkdir -p "$PUB" "$LOG_DIR"
LOG=$LOG_DIR/score_runb_${TAG}_$(date +%Y%m%d_%H%M%S).log
exec > >(tee -a "$LOG") 2>&1
echo "score_runb: $MODEL @ $REV vs checkpoint 1; tag $TAG; log $LOG; $(now)"
echo "runb_test: $RUNB_TEST (SHA-256 $sha)${SAMPLE:+, sample $SAMPLE}"

# --- compute ---------------------------------------------------------------------
GPU=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
      | awk -F', *' -v g0="${ALLOW_GPU0:-0}" '($1 != 0 || g0 == 1) && $2 >= 8192 {print $1; exit}' || true)
if [ -n "$GPU" ]; then
  export CUDA_VISIBLE_DEVICES=$GPU; NICE=""
  echo "compute: GPU $GPU (>= 8 GB free)"
else
  export CUDA_VISIBLE_DEVICES=""; NICE="nice -n 19"
  export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
  echo "compute: CPU, nice -n 19, 8 threads (no usable GPU with 8 GB free; GPU 0 only with ALLOW_GPU0=1)"
fi
export TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1

run() {  # run <who> <model> <rev> <set> <out dir> [extra args...]
  local who=$1 model=$2 rev=$3 set=$4 out=$5; shift 5
  local revarg=(); [ "$rev" != "-" ] && revarg=(--revision "$rev")
  echo "--- $who / $set"
  rm -f "$out/${who}_${set}.json" "$out/${who}_${set}.md"
  $NICE "$PYTHON" "$ROOT/eval/scoreboard.py" --model "$model" ${revarg[@]+"${revarg[@]}"} --sets "$set" --tracks "$TRACKS" \
    --name "${who}_${set}" --out-dir "$out" --cache-dir "$CACHE_DIR" "$@" 2>&1 \
    | grep -v -E "ETA|Loading weights" || true
  [ -f "$out/${who}_${set}.json" ] || { echo "FAILED: $who / $set"; exit 1; }
}

NOPRIV=$ROOT/.no-private-sets  # never exists: the public runs read no private folder
SAMPLE_ARGS=(); [ -n "$SAMPLE" ] && SAMPLE_ARGS=(--sample "$SAMPLE")
for who in ckpt1 new; do
  if [ $who = ckpt1 ]; then m=$BASE_MODEL; r=$BASE_REV; else m=$MODEL; r=$REV; fi
  run $who "$m" "$r" probes "$PUB" --private-dir "$NOPRIV"
  [ $SKIP_RUNB = 1 ] || run $who "$m" "$r" runb_test "$PUB" --private-dir "$NOPRIV" --runb-test "$RUNB_TEST" ${SAMPLE_ARGS[@]+"${SAMPLE_ARGS[@]}"}
  if [ $SKIP_REAL = 0 ] && [ -d "$PRIVATE_DIR/real_text" ]; then
    mkdir -p "$PRIV"
    run $who "$m" "$r" real_text "$PRIV" --private-dir "$PRIVATE_DIR"
  fi
done

# --- comparison --------------------------------------------------------------------
REAL_ARGS=()
if [ -f "$PRIV/ckpt1_real_text.json" ] && [ -f "$PRIV/new_real_text.json" ]; then
  REAL_ARGS=(--base-real "$PRIV/ckpt1_real_text.json" --new-real "$PRIV/new_real_text.json" --real-out "$PRIV/compare_real_text.md")
else
  echo "real_text: skipped (no $PRIVATE_DIR/real_text or --skip-real)"
fi
RUNB_ARGS=()
[ $SKIP_RUNB = 1 ] || RUNB_ARGS=(--base-runb "$PUB/ckpt1_runb_test.json" --new-runb "$PUB/new_runb_test.json")
"$PYTHON" "$ROOT/eval/compare_runs.py" --base-probes "$PUB/ckpt1_probes.json" --new-probes "$PUB/new_probes.json" \
  ${RUNB_ARGS[@]+"${RUNB_ARGS[@]}"} --out "$PUB/compare.md" ${REAL_ARGS[@]+"${REAL_ARGS[@]}"}
echo "DONE $(now): $PUB/compare.md${REAL_ARGS:+ and $PRIV/compare_real_text.md (private)}"
