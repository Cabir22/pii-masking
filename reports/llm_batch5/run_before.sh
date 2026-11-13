#!/bin/bash
# Batch 5, before cleaning: audit (with rejects), validate_corpus, leakage guard (P2-5 batch 5).
# Run on main @ 653c88f.
set -u
export PYTHONIOENCODING=utf-8
R=reports/llm_batch5
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
F=data/raw/sprint1_llm_b5.jsonl
PY=${PY:-python}
$PY scripts/piigen/audit_llm_batch.py $F --rejects data/raw/sprint1_llm_b5.rejects.jsonl --json $R/b5_audit_before.json > $R/b5_audit_before.txt 2>&1
$PY scripts/validate_corpus.py $F --skip-dedup --json $R/b5_validate_before.json > $R/b5_validate_before.txt 2>&1
$PY eval/leakage_guard.py $F --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/b5_leakage_guard_before.txt
