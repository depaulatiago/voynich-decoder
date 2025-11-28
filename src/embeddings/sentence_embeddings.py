#!/usr/bin/env python3
"""Single script: sentence embeddings -> PCA/UMAP -> HDBSCAN clustering for lines.

Writes:
- `notebooks/outputs/voynich_line_embeddings.npy`
- `notebooks/outputs/voynich_lines.jsonl`
- `notebooks/outputs/voynich_line_clusters.csv`
- `notebooks/outputs/voynich_line_cluster_top_examples.json`
- `notebooks/outputs/voynich_line_projection.png`
"""
from pathlib import Path
import json
import numpy as np
import sys
try:
    from ..utils.experiment_logger import enrich_record, make_run_id
except Exception:
    def enrich_record(r, **kw):
        return r
    def make_run_id():
        return 'local'

ROOT = Path('.').resolve()
OUT = ROOT / 'notebooks' / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)


def load_lines():
    proc = ROOT / 'data' / 'processed' / 'voynich_takahashi.jsonl'
    if not proc.exists():
        print('Processed file not found:', proc, file=sys.stderr)
        return []
    lines = []
    with proc.open('r', encoding='utf-8') as fh:
        for i, ln in enumerate(fh):
            rec = json.loads(ln)
            # prefer `text` field, fallback to tokens
            text = rec.get('text') or ' '.join(rec.get('tokens', []))
            lines.append({'id': i, 'text': text})
    return lines


def run():
    lines = load_lines()
    if not lines:
        return
    texts = [l['text'] for l in lines]

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print('Please install sentence-transformers in the .venv:', e, file=sys.stderr)
        raise

    model_name = 'all-MiniLM-L6-v2'
    print('Loading sentence-transformers model', model_name)
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    print('Embeddings shape', emb.shape)
    np.save(OUT / 'voynich_line_embeddings.npy', emb)

    # save lines jsonl
    with (OUT / 'voynich_lines.jsonl').open('w', encoding='utf-8') as fh:
        for l in lines:
            fh.write(json.dumps(l, ensure_ascii=False) + '\n')

    # reduce + project
    try:
        from sklearn.decomposition import PCA
        import umap
        reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
        emb_pca = PCA(n_components=min(50, emb.shape[1]-1)).fit_transform(emb)
        proj = reducer.fit_transform(emb_pca)
        proj_method = 'umap'
    except Exception:
        from sklearn.manifold import TSNE
        from sklearn.decomposition import PCA
        emb_pca = PCA(n_components=min(50, emb.shape[1]-1)).fit_transform(emb)
        proj = TSNE(n_components=2, perplexity=30, random_state=42, n_iter=1000).fit_transform(emb_pca)
        proj_method = 'tsne'

    # cluster with HDBSCAN
    try:
        import hdbscan
    except Exception:
        print('Please install hdbscan in the .venv', file=sys.stderr)
        raise

    clusterer = hdbscan.HDBSCAN(min_cluster_size=5, metric='euclidean', cluster_selection_method='eom')
    labels = clusterer.fit_predict(emb_pca)
    print('Cluster labels range', set(labels))

    # write CSV of clusters
    import csv
    label_counts = {}
    for l in labels:
        label_counts.setdefault(int(l), 0)
        label_counts[int(l)] += 1

    csv_p = OUT / 'voynich_line_clusters.csv'
    with csv_p.open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['line_id', 'label', 'cluster_size'])
        for i, l in enumerate(labels):
            w.writerow([i, int(l), int(label_counts.get(int(l), 0))])

    # top examples per cluster (closest to centroid)
    from numpy.linalg import norm
    cluster_examples = {}
    for lab in sorted(set(labels)):
        if lab == -1:
            continue
        idx = [i for i, x in enumerate(labels) if x == lab]
        pts = emb_pca[idx]
        cen = pts.mean(axis=0)
        sims = (emb_pca @ cen) / (norm(emb_pca, axis=1) * (norm(cen) + 1e-12))
        # pick highest-scoring items that are in this cluster
        order = [int(i) for i in sims.argsort()[::-1] if int(i) in idx][:10]
        cluster_examples[int(lab)] = [{'id': int(i), 'text': texts[int(i)], 'score': float(sims[int(i)])} for i in order]

    with (OUT / 'voynich_line_cluster_top_examples.json').open('w', encoding='utf-8') as fh:
        json.dump(cluster_examples, fh, ensure_ascii=False, indent=2)

    # plot projection
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.figure(figsize=(10,8))
    uniq = sorted(set(labels))
    palette = sns.color_palette('tab20', n_colors=max(2, len(uniq)))
    for lab in uniq:
        idx = [i for i,x in enumerate(labels) if x==lab]
        if lab == -1:
            col = (0.75,0.75,0.75)
            labname='-1 (noise)'
        else:
            col = palette[int(lab) % len(palette)]
            labname=str(int(lab))
        pts = proj[idx]
        plt.scatter(pts[:,0], pts[:,1], s=8, color=col, label=labname, alpha=0.8)
    plt.legend(bbox_to_anchor=(1.02,1), loc='upper left', fontsize='small')
    plt.title(f'Voynich lines projection ({proj_method}) + HDBSCAN')
    plt.tight_layout()
    plt.savefig(OUT / 'voynich_line_projection.png', dpi=150)
    print('Wrote outputs to', OUT)

    # write provenance metadata for sentence-embedding run
    try:
        meta = {
            'run_id': make_run_id(),
            'model': model_name,
            'n_lines': len(texts),
            'out_files': [
                str(OUT / 'voynich_line_embeddings.npy'),
                str(OUT / 'voynich_lines.jsonl'),
                str(OUT / 'voynich_line_clusters.csv'),
                str(OUT / 'voynich_line_cluster_top_examples.json'),
                str(OUT / 'voynich_line_projection.png'),
            ],
        }
        with (OUT / 'sentence_embeddings_metadata.json').open('w', encoding='utf-8') as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
        print('Wrote sentence embeddings metadata to', OUT / 'sentence_embeddings_metadata.json')
    except Exception:
        pass


if __name__ == '__main__':
    run()
