#!/usr/bin/env python3
"""Compare Voynich processed text with external corpora.

Computes:
- unigram and bigram frequency distributions
- Jensen-Shannon divergence (JSD) between Voynich and each corpus
- optional: mean cosine similarity between sentence embeddings (requires sentence-transformers)

Writes outputs to `reports/comparison/`:
- `summary.csv` (corpus, jsd_unigram, jsd_bigram, embedding_sim)
- `{corpus}_details.json` with top ngrams and counts
- `summary.md` human-readable ranking

Usage:
  python3 src/compare/compare_corpora.py --voynich data/processed/voynich_takahashi.jsonl --corpora data/corpora --out reports/comparison
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
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
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def counter_to_prob(counter: Counter) -> Dict[str, float]:
    total = float(sum(counter.values()))
    if total == 0:
        return {}
    return {k: v/total for k, v in counter.items()}


def js_divergence(p: Dict[str, float], q: Dict[str, float]) -> float:
    # Jensen-Shannon divergence using log2
    keys = set(p.keys()) | set(q.keys())
    m = {}
    for k in keys:
        m[k] = 0.5 * (p.get(k, 0.0) + q.get(k, 0.0))

    def kl(a, b):
        s = 0.0
        for k, v in a.items():
            if v == 0:
                continue
            bv = b.get(k, 0.0)
            if bv == 0:
                # avoid log(0); treat as large divergence
                s += v * math.log2(v / (1e-12))
            else:
                s += v * math.log2(v / bv)
        return s

    return 0.5 * (kl(p, m) + kl(q, m))


def read_voynich_lines(path: Path) -> List[str]:
    lines = []
    with path.open('r', encoding='utf-8') as fh:
        for ln in fh:
            if not ln.strip():
                continue
            obj = json.loads(ln)
            text = obj.get('text') or ' '.join(obj.get('tokens', []))
            if text:
                lines.append(text)
    return lines


def read_corpus_text(path: Path) -> str:
    with path.open('r', encoding='utf-8', errors='ignore') as fh:
        return fh.read()


def top_items(counter: Counter, n=30):
    return counter.most_common(n)


def embed_similarity(v_texts: List[str], c_texts: List[str], model_name='all-MiniLM-L6-v2') -> float | None:
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except Exception:
        return None

    model = SentenceTransformer(model_name)
    # sample up to 200 lines each
    s_v = v_texts[:200]
    s_c = c_texts[:200]
    if not s_v or not s_c:
        return None
    emb_v = model.encode(s_v, show_progress_bar=False, convert_to_numpy=True)
    emb_c = model.encode(s_c, show_progress_bar=False, convert_to_numpy=True)
    # compute mean pairwise cosine similarity (approx: mean of normalized dot products)
    def mean_sim(a, b):
        a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
        sims = a_norm @ b_norm.T
        return float(sims.mean())

    return mean_sim(emb_v, emb_c)


def compare(voynich_path: Path, corpora_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id()
    # write run-level metadata
    meta = {
        'run_id': run_id,
        'voynich_source': str(voynich_path),
        'corpora_dir': str(corpora_dir),
    }
    with (out_dir / 'comparison_metadata.json').open('w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    # load Voynich lines
    v_lines = read_voynich_lines(voynich_path)
    v_tokens = []
    for t in v_lines:
        v_tokens.extend(tokenize(t))

    v_uni = Counter(v_tokens)
    v_bi = Counter(' '.join(ng) for ng in ngrams(v_tokens, 2))
    p_v_uni = counter_to_prob(v_uni)
    p_v_bi = counter_to_prob(v_bi)

    results = []
    for corpus_file in sorted(corpora_dir.iterdir()):
        if not corpus_file.is_file():
            continue
        name = corpus_file.stem
        text = read_corpus_text(corpus_file)
        c_tokens = tokenize(text)
        c_uni = Counter(c_tokens)
        c_bi = Counter(' '.join(ng) for ng in ngrams(c_tokens, 2))
        p_c_uni = counter_to_prob(c_uni)
        p_c_bi = counter_to_prob(c_bi)
        jsd_uni = js_divergence(p_v_uni, p_c_uni)
        jsd_bi = js_divergence(p_v_bi, p_c_bi)

        # try embedding similarity (may be None)
        emb_sim = embed_similarity(v_lines, text.splitlines())

        detail = {
            'corpus': name,
            'file': str(corpus_file),
            'jsd_unigram': jsd_uni,
            'jsd_bigram': jsd_bi,
            'embedding_similarity': emb_sim,
            'top_unigrams': top_items(c_uni, 40),
            'top_bigrams': top_items(c_bi, 40),
        }
        # attach provenance metadata
        detail = enrich_record(detail, run_id=run_id, input_file=str(voynich_path), params={'corpus': name})
        results.append(detail)
        # write detail per corpus
        with (out_dir / f"{name}_details.json").open('w', encoding='utf-8') as fh:
            json.dump(detail, fh, ensure_ascii=False, indent=2)

    # write summary CSV
    import csv
    csv_p = out_dir / 'summary.csv'
    with csv_p.open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['corpus', 'jsd_unigram', 'jsd_bigram', 'embedding_similarity'])
        for r in results:
            w.writerow([r['corpus'], r['jsd_unigram'], r['jsd_bigram'], r['embedding_similarity']])

    # write markdown summary
    md_p = out_dir / 'summary.md'
    with md_p.open('w', encoding='utf-8') as fh:
        fh.write('# Corpus comparison summary\n\n')
        fh.write(f'Voynich source: {voynich_path}\n\n')
        fh.write('| corpus | jsd_unigram | jsd_bigram | embedding_similarity |\n')
        fh.write('|---|---:|---:|---:|\n')
        # sort by jsd_unigram ascending (more similar = lower)
        for r in sorted(results, key=lambda x: x['jsd_unigram'] if x['jsd_unigram'] is not None else 1e9):
            fh.write(f"| {r['corpus']} | {r['jsd_unigram']:.6f} | {r['jsd_bigram']:.6f} | {'' if r['embedding_similarity'] is None else f'{r['embedding_similarity']:.4f}'} |\n")

    print('Wrote comparison outputs to', out_dir)


def main():
    parser = argparse.ArgumentParser(description='Compare Voynich with corpora')
    parser.add_argument('--voynich', required=True, help='Path to processed Voynich JSONL with text field')
    parser.add_argument('--corpora', required=True, help='Path to corpora directory (text files)')
    parser.add_argument('--out', default='reports/comparison', help='Output directory')
    args = parser.parse_args()
    compare(Path(args.voynich), Path(args.corpora), Path(args.out))


if __name__ == '__main__':
    main()
