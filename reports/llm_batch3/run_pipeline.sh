#!/bin/bash
# Batch 3 audit/clean/relabel and batches 1-2 re-relabel (P2-5 batch 3, D-17/D-18d).
set -u
export PYTHONIOENCODING=utf-8
R=reports/llm_batch3
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
gates () {   # $1 = file, $2 = report prefix
  python scripts/validate_corpus.py "$1" --skip-dedup --json $R/$2_validate.json > $R/$2_validate.txt 2>&1
  python eval/leakage_guard.py "$1" --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/$2_leakage_guard.txt
  python scripts/piigen/audit_llm_batch.py "$1" --json $R/$2_audit.json > $R/$2_audit.txt 2>&1
}
for b in 1 2; do
  python scripts/relabel_standalone_dates.py --batch data/raw/sprint1_llm_b$b.clean.jsonl --in-place --report $R/b${b}_relabel.json > $R/b${b}_relabel.txt 2>&1
  gates data/raw/sprint1_llm_b$b.clean.jsonl b${b}_after
done
python scripts/clean_llm_batch.py data/raw/sprint1_llm_b3.jsonl --drop-unplanned-pii > $R/b3_clean_run.txt 2>&1
python scripts/relabel_standalone_dates.py --batch data/raw/sprint1_llm_b3.clean.jsonl --in-place --report $R/b3_relabel.json > $R/b3_relabel.txt 2>&1
gates data/raw/sprint1_llm_b3.clean.jsonl b3_after
python scripts/relabel_standalone_dates.py --data-dir data/processed/merged_relabeled_swept_dated --report $R/corpus_dryrun.json > $R/corpus_dryrun.txt 2>&1
echo ALLDONE
