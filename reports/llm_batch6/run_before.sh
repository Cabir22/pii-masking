#!/bin/bash
# Batch 5, before cleaning: audit (with rejects), validate_corpus, leakage guard (P2-5 batch 6).
# Run on main @ 6e23d8c.
set -u
export PYTHONIOENCODING=utf-8
R=reports/llm_batch6
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
F=data/raw/sprint1_llm_b6.jsonl
PY=${PY:-python}
$PY scripts/piigen/audit_llm_batch.py $F --rejects data/raw/sprint1_llm_b6.rejects.jsonl --json $R/b6_audit_before.json > $R/b6_audit_before.txt 2>&1
$PY scripts/validate_corpus.py $F --skip-dedup --json $R/b6_validate_before.json > $R/b6_validate_before.txt 2>&1
$PY eval/leakage_guard.py $F --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/b6_leakage_guard_before.txt
