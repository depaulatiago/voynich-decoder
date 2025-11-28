#!/usr/bin/env python3
"""Preprocess the interlinear file to extract Takahashi (;H) transcription lines.

Writes a plain TXT file (one transcription line per line) suitable for the
`src/ingest/ingest.py` script. Removes `{...}` comments and keeps EVA markers.

Usage:
  python3 src/ingest/preprocess_takahashi.py data/raw/voynich_takashi.txt -o data/raw/voynich_takahashi_extracted.txt
"""
import re
import argparse
import os


TAK_RE = re.compile(r"^<[^>]*;H>\s*(.*)")
BRACE_RE = re.compile(r"\{[^}]*\}")


def extract_takahashi(in_path, out_path):
    out_lines = []
    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            m = TAK_RE.match(line)
            if not m:
                continue
            text = m.group(1).rstrip("\n\r")
            # remove inline {} comments
            text = BRACE_RE.sub("", text)
            # normalize spaces
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                out_lines.append(text)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for l in out_lines:
            f.write(l + "\n")
    print(f"Extracted {len(out_lines)} Takahashi lines to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract Takahashi ;H lines from interlinear file")
    parser.add_argument("input", help="Path to interlinear raw file")
    parser.add_argument("-o", "--output", default="data/raw/voynich_takahashi_extracted.txt", help="Output plain text path")
    args = parser.parse_args()
    extract_takahashi(args.input, args.output)


if __name__ == "__main__":
    main()
