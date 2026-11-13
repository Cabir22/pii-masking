#!/bin/bash
# Batch 4, before cleaning: audit (with rejects), validate_corpus, leakage guard (P2-5 batch 4).
# Run on main @ c4c6f1f, before this branch's fixes. The replay (today's code on the stored
# texts) is run after them:
#   python scripts/piigen/audit_llm_batch.py data/raw/sprint1_llm_b4.jsonl --replay --json reports/llm_batch4/b4_audit_replay_after.json
set -u
export PYTHONIOENCODING=utf-8
R=reports/llm_batch4
B=data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl
F=data/raw/sprint1_llm_b4.jsonl
python scripts/piigen/audit_llm_batch.py $F --rejects data/raw/sprint1_llm_b4.rejects.jsonl --json $R/b4_audit_before.json > $R/b4_audit_before.txt 2>&1
python scripts/validate_corpus.py $F --skip-dedup --json $R/b4_validate_before.json > $R/b4_validate_before.txt 2>&1
python eval/leakage_guard.py $F --bench-docs $B 2>&1 | grep -E '^(LEAKAGE|inputs|D-2|Benchmark values|CHECK|documents scanned|RESULT)' > $R/b4_leakage_guard_before.txt
