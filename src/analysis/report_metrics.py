#!/usr/bin/env python3
"""Compute summary metrics for a processed Voynich JSONL and produce a report.

Outputs:
- `reports/experiment_metrics.json` : machine-readable metrics
- `reports/experiment_metrics.md`   : human-readable summary + lightweight interpretation

Metrics computed:
- lines, tokens, vocab size
- unigram entropy (Shannon)
- hapax legomena ratio (tokens with count==1)
- Zipf slope (log rank vs log freq linear fit)
- top unigrams and bigrams
- optional: silhouette score if embeddings and cluster CSV provided

Usage:
  python3 src/analysis/report_metrics.py --input data/processed/voynich_takahashi.jsonl

"""
from __future__ import annotations
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Tuple
try:
    from ..utils.experiment_logger import enrich_record, make_run_id
except Exception:
    def enrich_record(r, **kw):
        return r
    def make_run_id():
        return 'local'

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return TOKEN_RE.findall(text.lower())


def ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if n <= 0:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def shannon_entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for v in counter.values():
        p = v / total
        ent -= p * math.log2(p)
    return ent


def zipf_slope(counter: Counter) -> float | None:
    freqs = sorted(counter.values(), reverse=True)
    if len(freqs) < 3:
        return None
    import numpy as np

    ranks = np.arange(1, len(freqs) + 1)
    vals = np.array(freqs, dtype=float)
    # use top N points to avoid tail noise
    N = min(len(vals), 1000)
    x = np.log10(ranks[:N])
    y = np.log10(vals[:N])
    # linear fit y = a + b*x; slope = b
    b, a = np.polyfit(x, y, 1)
    return float(b)


def read_lines_from_jsonl(path: Path) -> List[str]:
    lines = []
    if not path.exists():
        return lines
    with path.open('r', encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            text = obj.get('text') or ' '.join(obj.get('tokens', []))
            if text:
                lines.append(text)
    return lines


def compute_metrics(lines: List[str]) -> dict:
    tokens = []
    for t in lines:
        tokens.extend(tokenize(t))

    uni = Counter(tokens)
    bi = Counter(' '.join(ng) for ng in ngrams(tokens, 2))
    total_tokens = sum(uni.values())
    vocab = len(uni)
    hapax = sum(1 for v in uni.values() if v == 1)
    hapax_ratio = hapax / vocab if vocab else 0.0
    entropy = shannon_entropy(uni)
    zipf = zipf_slope(uni)

    metrics = {
        'lines': len(lines),
        'tokens': total_tokens,
        'vocab_size': vocab,
        'hapax_legomena': hapax,
        'hapax_ratio': hapax_ratio,
        'unigram_entropy_bits': entropy,
        'zipf_slope_loglog': zipf,
        'top_unigrams': uni.most_common(30),
        'top_bigrams': bi.most_common(30),
    }
    return metrics


def interpret_metrics(metrics: dict) -> List[str]:
    notes = []
    ent = metrics.get('unigram_entropy_bits', 0.0)
    zipf = metrics.get('zipf_slope_loglog')
    hapax_ratio = metrics.get('hapax_ratio', 0.0)

    notes.append(f"Lines: {metrics.get('lines')}, Tokens: {metrics.get('tokens')}, Vocab: {metrics.get('vocab_size')}")

    if ent <= 0:
        notes.append('No token information to compute entropy.')
    else:
        notes.append(f"Unigram Shannon entropy: {ent:.3f} bits per token (higher = more unpredictable).")

    if zipf is None:
        notes.append('Zipf slope: not enough data to compute.')
    else:
        notes.append(f"Zipf slope (log-log) ~ {zipf:.3f}. Natural languages typically show a negative slope near -1 in rank-frequency plots; deviations may indicate atypical distribution or preprocessing artifacts.")

    if hapax_ratio > 0.2:
        notes.append(f"High hapax legomena ratio: {hapax_ratio:.3f} (many tokens occur only once) — could indicate high morphological variability, OCR/transcription noise, or a small dataset.")
    else:
        notes.append(f"Hapax legomena ratio: {hapax_ratio:.3f}.")

    notes.append('Top unigrams and bigrams are provided for manual inspection of frequent tokens (possible function words or repeated glyph sequences).')

    return notes


def save_results(metrics: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_p = out_dir / 'experiment_metrics.json'
    md_p = out_dir / 'experiment_metrics.md'
    # attach run metadata for provenance
    meta = {
        'generated_at': None,
        'run_id': make_run_id(),
        'input_file': None,
        'params': {},
    }
    # merge metadata into metrics output
    out_obj = dict(metrics)
    out_obj.setdefault('metadata', meta)

    with json_p.open('w', encoding='utf-8') as fh:
        json.dump(out_obj, fh, ensure_ascii=False, indent=2)

    with md_p.open('w', encoding='utf-8') as fh:
        fh.write('# Experiment metrics summary\n\n')
        fh.write(f"Generated: {Path('.').resolve()}\n\n")
        fh.write('## Overview\n\n')
        fh.write(f"- Lines: {metrics.get('lines')}\n")
        fh.write(f"- Tokens: {metrics.get('tokens')}\n")
        fh.write(f"- Vocabulary size: {metrics.get('vocab_size')}\n")
        fh.write(f"- Hapax legomena: {metrics.get('hapax_legomena')} (ratio {metrics.get('hapax_ratio'):.4f})\n")
        fh.write(f"- Unigram entropy (bits): {metrics.get('unigram_entropy_bits'):.4f}\n")
        s = metrics.get('zipf_slope_loglog')
        fh.write(f"- Zipf slope (log-log): {('N/A' if s is None else f'{s:.4f}')}\n")

        fh.write('\n## Interpretation notes\n\n')
        for n in interpret_metrics(metrics):
            fh.write(f'- {n}\n')

        fh.write('\n## Top unigrams\n\n')
        for w, c in metrics.get('top_unigrams', [])[:50]:
            fh.write(f'- {w}: {c}\n')

        fh.write('\n## Top bigrams\n\n')
        for w, c in metrics.get('top_bigrams', [])[:50]:
            fh.write(f'- {w}: {c}\n')

    print('Wrote metrics JSON to', json_p)
    print('Wrote human summary to', md_p)


def main():
    parser = argparse.ArgumentParser(description='Compute experiment metrics for Voynich processed file')
    parser.add_argument('--input', required=True, help='Path to processed JSONL with `text` field')
    parser.add_argument('--out', default='reports', help='Output directory to write experiment_metrics.json and .md')
    args = parser.parse_args()

    input_p = Path(args.input)
    out_p = Path(args.out)
    lines = read_lines_from_jsonl(input_p)
    metrics = compute_metrics(lines)
    save_results(metrics, out_p)


if __name__ == '__main__':
    main()
