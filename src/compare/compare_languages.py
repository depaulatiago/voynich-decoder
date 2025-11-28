#!/usr/bin/env python3
"""Compare Voynich n-gram distributions with candidate language corpora.

Searches for corpora files under `data/corpora/*.txt`. For each corpus found,
computes character n-gram (1..4) frequency distributions and compares them to
the Voynich token set (from `models/minimal/.../terms.npy`) using Jensen-Shannon
divergence and top-k overlap.

Writes results to `reports/comparison/compare_report.json` and per-corpus CSVs.

If no corpora are found, writes a short README explaining how to add corpora or
auto-download examples.
"""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import math
import csv
import sys


ROOT = Path('.').resolve()
OUT = ROOT / 'reports' / 'comparison'
OUT.mkdir(parents=True, exist_ok=True)


def load_terms():
    terms_p = ROOT / 'models' / 'minimal' / 'voynich_takahashi' / 'terms.npy'
    if not terms_p.exists():
        # fallback: try to build from processed lines
        proc = ROOT / 'data' / 'processed' / 'voynich_takahashi.jsonl'
        if not proc.exists():
            print('No terms or processed file found. Please run ingestion first.', file=sys.stderr)
            return []
        import json as _json
        terms = set()
        with proc.open('r', encoding='utf-8') as fh:
            for line in fh:
                rec = _json.loads(line)
                toks = rec.get('tokens') or []
                for t in toks:
                    terms.add(t)
        return sorted(list(terms))
    arr = np.load(terms_p, allow_pickle=True)
    return [str(x) for x in arr]


def ngram_counts(strings, n=3):
    c = Counter()
    for s in strings:
        s = s.lower()
        if len(s) < n:
            c[s] += 1
        else:
            for i in range(len(s)-n+1):
                c[s[i:i+n]] += 1
    return c


def normalize_counter(c):
    total = sum(c.values())
    if total == 0:
        return {}, total
    return {k: v/total for k, v in c.items()}, total


def js_divergence(p, q):
    # p and q are dicts of probabilities over same universe (may differ keys)
    keys = set(p) | set(q)
    p_vec = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    q_vec = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    m = 0.5 * (p_vec + q_vec)
    def kl(a, b):
        mask = (a > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * (kl(p_vec, m) + kl(q_vec, m))


def topk_overlap(p, q, k=50):
    pk = [x for x, _ in sorted(p.items(), key=lambda t: -t[1])][:k]
    qk = [x for x, _ in sorted(q.items(), key=lambda t: -t[1])][:k]
    setp = set(pk)
    setq = set(qk)
    inter = setp & setq
    return len(inter) / k if k > 0 else 0.0, list(inter)[:20]


def analyze_corpus(corpus_path, voy_terms):
    txt = corpus_path.read_text(encoding='utf-8', errors='ignore')
    # simple tokenization by whitespace
    words = [w for w in (txt.replace('\n', ' ').split(' ')) if w]
    results = {}
    for n in range(1, 5):
        c_corpus = ngram_counts(words, n=n)
        c_voy = ngram_counts(voy_terms, n=n)
        p_corpus, _ = normalize_counter(c_corpus)
        p_voy, _ = normalize_counter(c_voy)
        jsd = js_divergence(p_voy, p_corpus)
        overlap, common = topk_overlap(p_voy, p_corpus, k=50)
        results[f'{n}gram'] = {
            'js_divergence': jsd,
            'top50_overlap': overlap,
            'example_common': common,
            'voy_total_ngrams': sum(c_voy.values()),
            'corpus_total_ngrams': sum(c_corpus.values())
        }
    return results


def main():
    voy_terms = load_terms()
    corpora = sorted((ROOT / 'data' / 'corpora').glob('*.txt')) if (ROOT / 'data' / 'corpora').exists() else []
    report = {'voy_terms_count': len(voy_terms), 'corpora_analyzed': []}
    if not corpora:
        readme = OUT / 'README.txt'
        readme.write_text(
            'No corpora found under data/corpora/.\nPlace plain-text corpora files named e.g. latin.txt, hebrew.txt, english.txt there.\n'
            'Alternatively you can download examples from Project Gutenberg. Example:\n'
            '  mkdir -p data/corpora && wget -O data/corpora/latin.txt https://www.gutenberg.org/cache/epub/10643/pg10643.txt\n',
            encoding='utf-8')
        report['note'] = 'no corpora found; README written to reports/comparison/README.txt'
        (OUT / 'compare_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print('No corpora found; wrote README and empty report to', OUT)
        return

    for corpus in corpora:
        print('Analyzing', corpus)
        results = analyze_corpus(corpus, voy_terms)
        entry = {'corpus': str(corpus), 'results': results}
        report['corpora_analyzed'].append(entry)
        # write per-corpus CSV summary
        csv_p = OUT / (corpus.stem + '_summary.csv')
        with csv_p.open('w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['ngram','js_divergence','top50_overlap','voy_total','corpus_total','example_common'])
            for n in range(1,5):
                r = results[f'{n}gram']
                w.writerow([f'{n}', r['js_divergence'], r['top50_overlap'], r['voy_total_ngrams'], r['corpus_total_ngrams'], ';'.join(r['example_common'])])

    with (OUT / 'compare_report.json').open('w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print('Wrote compare_report.json to', OUT)


if __name__ == '__main__':
    main()
