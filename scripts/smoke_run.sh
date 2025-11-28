#!/usr/bin/env bash
set -euo pipefail

# Smoke test: run a minimal pipeline on `example_transcription.txt`
# Steps: ingest -> tokenize -> stats. Validate outputs exist and are non-empty.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Running smoke test from $ROOT"

INPUT="$ROOT/example_transcription.txt"
OUT_DIR="$ROOT/data/processed"
INGEST_OUT="$OUT_DIR/example.jsonl"
TOK_OUT="$OUT_DIR/example_tokens.jsonl"
NGRAM_OUT="$OUT_DIR/example_ngrams.json"

mkdir -p "$OUT_DIR"

echo "1/3 - Ingesting $INPUT -> $INGEST_OUT"
python3 "$ROOT/src/ingest/ingest.py" "$INPUT" -o "$INGEST_OUT"

echo "2/3 - Tokenizing -> $TOK_OUT"
python3 "$ROOT/src/ingest/tokenize.py" "$INGEST_OUT" -o "$TOK_OUT"

echo "3/3 - Computing n-grams -> $NGRAM_OUT"
python3 "$ROOT/src/analytics/stats.py" "$INGEST_OUT" -o "$NGRAM_OUT"

echo "Validating outputs..."
for f in "$INGEST_OUT" "$TOK_OUT" "$NGRAM_OUT"; do
  if [ ! -f "$f" ]; then
    echo "Smoke test failed: missing file $f" >&2
    exit 2
  fi
  if [ ! -s "$f" ]; then
    echo "Smoke test failed: empty file $f" >&2
    exit 3
  fi
done

echo "Smoke test passed — generated files:"
ls -lh "$INGEST_OUT" "$TOK_OUT" "$NGRAM_OUT"

echo "Tip: make executable with 'chmod +x scripts/smoke_run.sh' and run './scripts/smoke_run.sh'"

exit 0
