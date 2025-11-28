#!/usr/bin/env python3
"""Basic tokenization and n-gram statistics for Voynich transcriptions.

Reads a JSONL with records containing a `text` field (normalized lines).
Outputs top unigrams/bigrams/trigrams and writes n-gram counts to JSON.
"""
import argparse
import json
import os
import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str):
    if not text:
        return []
    return TOKEN_RE.findall(text.lower())


def ngrams(tokens, n):
    if n <= 0:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def shannon_entropy(counter: Counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for v in counter.values():
        p = v / total
        ent -= p * math.log2(p)
    return ent


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def analyze(input_path, output_path=None, top=20):
    uni = Counter()
    bi = Counter()
    tri = Counter()
    total_lines = 0
    total_tokens = 0

    for rec in read_jsonl(input_path):
        text = rec.get("text", "")
        tokens = tokenize(text)
        total_lines += 1
        total_tokens += len(tokens)
        uni.update(tokens)
        bi.update(ngrams(tokens, 2))
        tri.update(ngrams(tokens, 3))

    results = {
        "lines": total_lines,
        "tokens": total_tokens,
        "unigram_count": sum(uni.values()),
        "unigram_entropy": shannon_entropy(uni),
        "top_unigrams": uni.most_common(top),
        "top_bigrams": [([" ".join(t)], c) for t, c in bi.most_common(top)],
        "top_trigrams": [([" ".join(t)], c) for t, c in tri.most_common(top)],
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "unigrams": dict(uni),
                "bigrams": {" ".join(k): v for k, v in bi.items()},
                "trigrams": {" ".join(k): v for k, v in tri.items()},
            }, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Compute token and n-gram statistics from JSONL transcription")
    parser.add_argument("input", help="Path to JSONL produced by ingest script")
    parser.add_argument("-o", "--output", default="data/processed/ngrams.json", help="Path to write n-gram counts JSON")
    parser.add_argument("--top", type=int, default=20, help="How many top items to print")
    args = parser.parse_args()

    res = analyze(args.input, args.output, top=args.top)

    print(f"Lines: {res['lines']}")
    print(f"Tokens: {res['tokens']}")
    print(f"Unigram entropy: {res['unigram_entropy']:.4f}")
    print("Top unigrams:")
    for w, c in res["top_unigrams"]:
        print(f"  {w}: {c}")
    print("Top bigrams:")
    for pair, c in res["top_bigrams"]:
        print(f"  {pair[0]}: {c}")


if __name__ == "__main__":
    main()
