#!/usr/bin/env python3
"""
Rule-based hypothesis generator for Voynich token clusters.

Reads `notebooks/outputs/top_terms_by_cluster_gensim.json` and optional
`notebooks/outputs/gensim_sample_nn.json` and writes concise hypotheses and
checks to `reports/hypotheses/rule_based.jsonl`.

This is intentionally lightweight and does not call any external APIs.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import List


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def substr_counts(tokens: List[str], min_len=3, max_len=5):
    cnt = Counter()
    for t in tokens:
        L = len(t)
        for l in range(min_len, max_len + 1):
            if L < l:
                continue
            for i in range(0, L - l + 1):
                s = t[i:i + l]
                cnt[s] += 1
    return cnt


def best_affixes(tokens: List[str], min_len=2, max_len=6, min_count=2):
    suf = Counter()
    pre = Counter()
    for t in tokens:
        for l in range(min_len, min(max_len, len(t)) + 1):
            suf[t[-l:]] += 1
            pre[t[:l]] += 1
    # choose affix appearing in at least min_count tokens and with maximal count
    best_suf, best_pre = None, None
    if suf:
        s, c = suf.most_common(1)[0]
        if c >= min_count:
            best_suf = (s, c)
    if pre:
        p, c = pre.most_common(1)[0]
        if c >= min_count:
            best_pre = (p, c)
    return best_pre, best_suf


def make_hypothesis(cluster_id: str, top_terms: List[List], sample_neighbors: dict):
    tokens = [t for t, _ in top_terms]
    size = len(tokens)

    pref, suf = best_affixes(tokens, min_len=2, max_len=6, min_count=max(2, int(0.25 * size)))

    substr = substr_counts(tokens, min_len=3, max_len=5)
    common_substrs = [s for s, c in substr.most_common(6) if c >= max(2, int(0.2 * size))]

    parts = []
    evidence = {}
    if suf:
        parts.append(f"Many tokens share the suffix '{suf[0]}' (count={suf[1]}). This suggests a possible suffix or inflectional ending.")
        evidence['suffix'] = {'affix': suf[0], 'count': suf[1]}
    if pref:
        parts.append(f"Many tokens share the prefix '{pref[0]}' (count={pref[1]}). This suggests a possible prefix or common root.")
        evidence['prefix'] = {'affix': pref[0], 'count': pref[1]}
    if common_substrs:
        parts.append(f"Frequent internal substrings appear: {', '.join(common_substrs)} — may indicate recurring morphemes or ligature clusters.")
        evidence['substrings'] = common_substrs

    if not parts:
        parts = ["No strong common prefix/suffix detected; tokens may be orthographic variants or form different morphological classes."]

    # construct suggested checks
    checks = []
    if 'suffix' in evidence:
        a = evidence['suffix']['affix']
        checks.append(f"Compute proportion of occurrences where tokens end with '{a}' vs. total corpus; check line-final vs line-initial frequencies.")
    if 'prefix' in evidence:
        a = evidence['prefix']['affix']
        checks.append(f"Check co-occurrence of prefix '{a}' with other token classes and its distribution across pages/sections.")
    if 'substrings' in evidence:
        checks.append("Search for substring contexts (left/right neighbors) to test whether the substring behaves like an independent morpheme.")
    checks.append("Compare these tokens' frequencies and neighbor contexts with a control corpus or other Voynich transcriptions.")

    # caveats
    caveats = []
    caveats.append("Clusters come from distributional embeddings — shared spelling/orthography can dominate semantic signal.")
    caveats.append("Tokenization choices and transcription artifacts may create or split apparent 'families'.")

    # sample neighbors summary
    neigh_short = {k: v for k, v in list(sample_neighbors.items())[:4]}

    hypothesis = {
        'cluster_id': cluster_id,
        'size': size,
        'hypothesis': ' '.join(parts),
        'evidence': evidence,
        'sample_neighbors': neigh_short,
        'suggested_checks': checks,
        'caveats': caveats,
    }
    return hypothesis


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--clusters', type=Path, default=Path('notebooks/outputs/top_terms_by_cluster_gensim.json'))
    p.add_argument('--nns', type=Path, default=Path('notebooks/outputs/gensim_sample_nn.json'))
    p.add_argument('--out', type=Path, default=Path('reports/hypotheses/rule_based.jsonl'))
    args = p.parse_args()

    clusters = load_json(args.clusters) if args.clusters.exists() else {}
    nns = load_json(args.nns) if args.nns.exists() else {}

    args.out.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with args.out.open('w', encoding='utf-8') as fh:
        for cid, top_terms in clusters.items():
            sample_neighbors = {}
            # pick up to 5 tokens from top_terms that have neighbor entries
            for tok, _ in top_terms:
                if tok in nns:
                    sample_neighbors[tok] = nns[tok][:6]
                if len(sample_neighbors) >= 5:
                    break
            hyp = make_hypothesis(cid, top_terms, sample_neighbors)
            fh.write(json.dumps(hyp, ensure_ascii=False) + '\n')
            written += 1

    print(f'Wrote {written} rule-based hypotheses to {args.out}')


if __name__ == '__main__':
    main()
