#!/usr/bin/env bash
# v4.1 training on a rented GPU, in one command (D-50: one seed, 42). Same recipe as run_v4.sh;
# only the data (runb-az-v4.1, D-52) and the names differ.
#
#   On the GPU, after `hf auth login` (a WRITE token of the account that owns the repos):
#     hf download your-hf-org/runb-az-v4.1 --repo-type dataset --local-dir v41
#     bash v41/run_v41.sh                    # starts everything in the background and returns
#     REPORT_TO=wandb bash v41/run_v41.sh    # the same, logging to W&B (after `wandb login`)
#     tail -f v41/train.log                 # watch it (Ctrl+C stops watching, not training)
#     cat v41/status.txt                    # one-line status
#
#   Second account (optional): every upload also goes to MIRROR_OWNER's repo of the same name,
#   with a write token of that account typed in, never shown:
#     read -s MIRROR_TOKEN && export MIRROR_TOKEN     # paste the token, press Enter
#     MIRROR_OWNER=your-hf-org REPORT_TO=wandb bash v41/run_v41.sh
#
# What it does: installs the libraries (tokenizers < 0.23, D-37), checks the data's SHA-256,
# trains with Run B's settings, uploads epoch 1 to the `epoch1` branch of the model repo as
# soon as it is saved (bug check, D-44b), and uploads the final model to `main`
# when training ends. Training keeps running if the connection drops. A failed upload to the
# second account is reported but never stops training.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SEED=${SEED:-42}
OWNER=${OWNER:-your-hf-org}
NAME=masking-az-runb-v4.1-seed$SEED
MODEL_REPO=$OWNER/$NAME
MIRROR_REPO=${MIRROR_OWNER:+$MIRROR_OWNER/$NAME}
OUT=$HERE/checkpoints/v41_seed$SEED
LOG=$HERE/train.log
STATUS=$HERE/status.txt

if [ "${1:-}" != "--inner" ]; then
  if [ -n "${MIRROR_REPO:-}" ] && [ -z "${MIRROR_TOKEN:-}" ]; then
    echo "MIRROR_OWNER is set but MIRROR_TOKEN is not: run  read -s MIRROR_TOKEN && export MIRROR_TOKEN  first"; exit 1
  fi
  nohup bash "$0" --inner > "$LOG" 2>&1 &
  echo "started in the background (pid $!). Watch: tail -f $LOG   Status: cat $STATUS"
  echo "uploads go to: $MODEL_REPO${MIRROR_REPO:+ and $MIRROR_REPO}"
  exit 0
fi

say() { echo "[$(date '+%H:%M:%S')] $*"; echo "[$(date '+%H:%M:%S')] $*" > "$STATUS"; }
trap 'say "FAILED (line $LINENO): see the end of $LOG"; kill 0' ERR

# hub.py: create the repos, upload a folder; the main account must work, the mirror may fail
cat > "$HERE/hub.py" <<'EOF'
import os, sys
from huggingface_hub import HfApi
action, primary, mirror = sys.argv[1], sys.argv[2], sys.argv[3]
targets = [(primary, None, True)] + ([(mirror, os.environ.get("MIRROR_TOKEN"), False)] if mirror else [])
for repo, token, required in targets:
    try:
        api = HfApi(token=token)
        if action == "create":
            api.create_repo(repo, private=True, exist_ok=True)
            api.create_branch(repo, branch="epoch1", exist_ok=True)
        else:
            folder, revision, message = sys.argv[4], sys.argv[5], sys.argv[6]
            path_in_repo = sys.argv[7] if len(sys.argv) > 7 else None
            api.upload_folder(repo_id=repo, folder_path=folder, revision=revision, commit_message=message,
                              path_in_repo=path_in_repo)
        print(f"{action} {repo}: ok")
    except Exception as e:
        print(f"{action} {repo}: FAILED: {type(e).__name__}: {e}")
        if required:
            sys.exit(1)
EOF

[ -f "$HERE/train.py" ] || { say "train.py missing next to run_v41.sh"; exit 1; }
say "installing libraries"
pip install -q "transformers>=4.44" "datasets>=2.20" "tokenizers>=0.19,<0.23" "accelerate>=0.30" "seqeval>=1.2.2" "huggingface_hub>=0.30"
python -c "import torch,tokenizers;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'gpu',torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-','tokenizers',tokenizers.__version__)"

say "checking the data (SHA-256)"
python - "$HERE" <<'EOF'
import hashlib, sys
d = sys.argv[1]
# runb-az-v4.1 at 75b71ab: the Windows build and the Mac build identical (window files compared LF)
want = {"train.jsonl": "313b0e4ceaf2faa76021aaefb0939ff8d6e8e01b2753d41a13b860aacc6f6860",
        "val.jsonl": "35d98f812789fca3196b394e3bddec27c50a1a18e9b884e1d332e12432301785",
        "test.jsonl": "484b78cff968949f10d6a287a0a90b4e5f725bba16fea48afc25067e29fdb578"}
if any(w == "TO_FILL_AFTER_VERIFY" for w in want.values()):
    sys.exit("run_v4.sh has no verified checksums yet: the team fills them after the second build")
for f, w in want.items():
    h = hashlib.sha256()
    with open(f"{d}/{f}", "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    got = h.hexdigest()
    print(f, got[:12], "OK" if got == w else "MISMATCH")
    if got != w:
        sys.exit("data does not match the verified v4.1 build (D-49): not training")
EOF

say "creating the model repo(s), private, with an epoch1 branch"
python "$HERE/hub.py" create "$MODEL_REPO" "${MIRROR_REPO:-}"

# Upload epoch 1 as soon as its checkpoint is saved (the trainer saves at each epoch's end).
(
  while :; do
    CK=$(python - "$OUT" <<'EOF'
import json, sys
from pathlib import Path
for ck in sorted(Path(sys.argv[1]).glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1])):
    st = ck / "trainer_state.json"
    if st.exists() and (ck / "model.safetensors").exists():
        if json.loads(st.read_text()).get("epoch", 0) >= 0.999:
            print(ck); break
EOF
)
    if [ -n "$CK" ]; then
      sleep 60   # let the save finish
      say "epoch 1 saved ($CK); uploading while epoch 2 trains"
      UP=$HERE/upload_epoch1_seed$SEED
      rm -rf "$UP"; mkdir -p "$UP"
      cp "$CK"/config.json "$CK"/model.safetensors "$CK"/trainer_state.json "$UP"/
      cp "$HERE"/labels.json "$UP"/
      # the tokenizer the model was trained with (D-51a: punctuation pre-tokenizer), as train.py saves it
      python - "$HERE" "$UP" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from transformers import AutoTokenizer
from train import _add_punctuation_boundary
tok = AutoTokenizer.from_pretrained("FacebookAI/xlm-roberta-large")
assert _add_punctuation_boundary(tok), "punctuation pre-tokenizer not applied"
tok.save_pretrained(sys.argv[2])
PYEOF
      python "$HERE/hub.py" upload "$MODEL_REPO" "${MIRROR_REPO:-}" "$UP" epoch1 "v4.1 seed $SEED, epoch 1 (bug check only, D-44b)"
      say "EPOCH 1 UPLOADED to $MODEL_REPO${MIRROR_REPO:+ and $MIRROR_REPO} (branch epoch1): tell the team. Epoch 2 is training."
      break
    fi
    sleep 120
  done
) &

say "training seed $SEED (Run B's settings, 2 epochs)"
python "$HERE"/train.py --data-dir "$HERE" --epochs 2 --seed "$SEED" \
  --batch-size 16 --grad-accum 2 --lr 2e-5 --lr-scheduler-type cosine --warmup-ratio 0.1 \
  --precision bf16 --output-dir "$OUT" \
  --report-to "${REPORT_TO:-none}" --run-name "v41_seed$SEED"

wait   # make sure the epoch-1 upload has finished
say "training done; uploading the final model"
python "$HERE/hub.py" upload "$MODEL_REPO" "${MIRROR_REPO:-}" "$OUT/final" main "v4.1 seed $SEED, final (2 epochs, D-50)"
# the test report and the log go to evaluation/ (the trainer writes the report next to final/)
EV=$HERE/upload_eval_seed$SEED
rm -rf "$EV"; mkdir -p "$EV"
cp "$OUT"/test_classification_report.* "$EV"/ 2>/dev/null || true
cp "$LOG" "$EV/train_seed$SEED.log"
python "$HERE/hub.py" upload "$MODEL_REPO" "${MIRROR_REPO:-}" "$EV" main "v4.1 seed $SEED: test report and training log" evaluation
BEST=$(grep -h "Loading best model" "$LOG" | tail -1 || true)
echo "best epoch: ${BEST:-not reported}"
say "ALL DONE: final model uploaded to $MODEL_REPO${MIRROR_REPO:+ and $MIRROR_REPO}. Check the upload lines above, then stop the GPU (or start the next seed)."
