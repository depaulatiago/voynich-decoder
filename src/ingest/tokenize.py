#!/usr/bin/env python3
"""Tokenize normalized JSONL into a JSONL of word tokens.

Input: JSONL with records containing `line` and `text` fields (normalized lines).
Output: JSONL where each record is a token with fields:
  - line: original line number
  - token_index: position of token in the line (1-based)
  - token: the token string
  - raw: original raw line (for reference)

Usage:
  python3 src/ingest/tokenize.py data/processed/transcription.jsonl -o data/processed/tokens.jsonl
"""
import argparse
import json
import os
import re


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(records, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def tokenize_jsonl(input_path, output_path):
    out = []
    for rec in read_jsonl(input_path):
        line_no = rec.get("line")
        raw = rec.get("raw", "")
        text = rec.get("text", "")
        tokens = TOKEN_RE.findall(text.lower())
        for i, t in enumerate(tokens, start=1):
            out.append({"line": line_no, "token_index": i, "token": t, "raw": raw})
    write_jsonl(out, output_path)
    print(f"Wrote {len(out)} token records to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Tokenize normalized JSONL into per-token JSONL")
    parser.add_argument("input", help="Path to normalized JSONL (with `text` field)")
    parser.add_argument("-o", "--output", default="data/processed/tokens.jsonl", help="Output tokens JSONL path")
    args = parser.parse_args()
    tokenize_jsonl(args.input, args.output)


if __name__ == "__main__":
    main()
