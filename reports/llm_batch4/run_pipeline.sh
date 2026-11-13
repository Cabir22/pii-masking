#!/bin/bash
# P2-5 batch 4: clean + date relabel for batch 4, and batches 1-3 re-cleaned from raw
# under the batch-4 gates (non-ASCII invented emails, corrupt text), then relabelled.
set -u
export PYTHONIOENCODING=utf-8
R=reports/llm_batch4
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
gates () {   # $1 = file, $2 = report prefix
  python scripts/validate_corpus.py "$1" --skip-dedup --json $R/$2_validate.json > $R/$2_validate.txt 2>&1
  python eval/leakage_guard.py "$1" --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/$2_leakage_guard.txt
  python scripts/piigen/audit_llm_batch.py "$1" --json $R/$2_audit.json > $R/$2_audit.txt 2>&1
}
for b in 4 1 2 3; do
  python scripts/clean_llm_batch.py data/raw/sprint1_llm_b$b.jsonl --drop-unplanned-pii > $R/b${b}_clean_run.txt 2>&1
  python scripts/relabel_standalone_dates.py --batch data/raw/sprint1_llm_b$b.clean.jsonl --in-place --report $R/b${b}_relabel.json > $R/b${b}_relabel.txt 2>&1
  gates data/raw/sprint1_llm_b$b.clean.jsonl b${b}_after
done
