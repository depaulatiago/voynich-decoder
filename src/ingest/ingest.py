#!/usr/bin/env python3
"""Simple ingestion and normalization script for Voynich transcriptions.

Creates a JSONL with fields: `line`, `raw`, `text` (normalized).

Usage:
  python src/ingest/ingest.py path/to/transcription.txt -o data/processed/transcription.jsonl
"""
import re
import json
import os
import argparse

UNCERTAINTY_PATTERN = r"[?*†()¶\[\]]"
PUNCT_PATTERN = r"[.,:;!\"'`/<>]"


def remove_html_tags(text: str) -> str:
    # simple HTML tag stripper
    return re.sub(r"<[^>]+>", " ", text)


def normalize_text(text: str,
                   strip_html: bool = True,
                   remove_numbers: bool = True,
                   remove_uncertainty: bool = True) -> str:
    """Normalize a single line of transcription.

    Options:
    - strip_html: remove tags like <p>, </n>, etc.
    - remove_numbers: remove digit-only tokens or numeric sequences
    - remove_uncertainty: remove characters used as uncertainty markers
    """
    if text is None:
        return ""
    s = text
    if strip_html:
        s = remove_html_tags(s)
    # remove uncertainty/annotation chars
    if remove_uncertainty:
        s = re.sub(UNCERTAINTY_PATTERN, "", s)
    # replace hyphens with space to separate joined tokens
    s = s.replace("-", " ")
    # remove punctuation
    s = re.sub(PUNCT_PATTERN, "", s)
    # optionally remove numbers (either standalone or within tokens)
    if remove_numbers:
        s = re.sub(r"\d+", " ", s)
    # remove backslash escapes like \n, \t
    s = re.sub(r"\\[ntbrf]", " ", s)
    # remove any remaining angle brackets or stray slashes
    s = re.sub(r"[<>]", " ", s)
    s = re.sub(r"/(?=[A-Za-z])", " ", s)
    # collapse whitespace and lowercase
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def load_transcription(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_jsonl(records, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def process_file(in_path: str, out_path: str, **norm_kwargs):
    text = load_transcription(in_path)
    lines = text.splitlines()
    records = []
    for i, l in enumerate(lines, start=1):
        norm = normalize_text(l, **norm_kwargs)
        if not norm:
            continue
        records.append({"line": i, "raw": l, "text": norm})
    write_jsonl(records, out_path)
    print(f"Wrote {len(records)} records to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Ingest and normalize a Voynich transcription")
    parser.add_argument("input", help="Path to transcription text file")
    parser.add_argument("-o", "--output", default="data/processed/transcription.jsonl", help="Output JSONL path")
    parser.add_argument("--no-strip-html", dest="strip_html", action="store_false", help="Don't remove HTML tags")
    parser.add_argument("--no-remove-numbers", dest="remove_numbers", action="store_false", help="Don't remove numbers")
    parser.add_argument("--no-remove-uncertainty", dest="remove_uncertainty", action="store_false", help="Don't remove uncertainty markers")
    args = parser.parse_args()
    process_file(args.input, args.output,
                 strip_html=args.strip_html,
                 remove_numbers=args.remove_numbers,
                 remove_uncertainty=args.remove_uncertainty)


if __name__ == "__main__":
    main()
