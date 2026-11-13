#!/bin/bash
# P2-5 batch 5: clean + date relabel for batch 5, and batches 1-4 re-cleaned from raw
# under the batch-5 gates (folded/misspelt invented streets; homograph given names before a
# surname), then relabelled.
set -u
export PYTHONIOENCODING=utf-8
PY=${PY:-python}
R=reports/llm_batch5
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
gates () {   # $1 = file, $2 = report prefix
  $PY scripts/validate_corpus.py "$1" --skip-dedup --json $R/$2_validate.json > $R/$2_validate.txt 2>&1
  $PY eval/leakage_guard.py "$1" --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/$2_leakage_guard.txt
  $PY scripts/piigen/audit_llm_batch.py "$1" --json $R/$2_audit.json > $R/$2_audit.txt 2>&1
}
for b in 5 1 2 3 4; do
  $PY scripts/clean_llm_batch.py data/raw/sprint1_llm_b$b.jsonl --drop-unplanned-pii > $R/b${b}_clean_run.txt 2>&1
  $PY scripts/relabel_standalone_dates.py --batch data/raw/sprint1_llm_b$b.clean.jsonl --in-place --report $R/b${b}_relabel.json > $R/b${b}_relabel.txt 2>&1
  gates data/raw/sprint1_llm_b$b.clean.jsonl b${b}_after
done
