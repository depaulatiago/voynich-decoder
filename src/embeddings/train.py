#!/usr/bin/env python3
"""Train word embeddings (Word2Vec / FastText) on Voynich transcriptions.

Reads a normalized JSONL (records with `text` field) and trains embeddings.
Saves models under the specified output directory.

Usage:
  python3 src/embeddings/train.py data/processed/transcription.jsonl --output models --model both
"""
import argparse
import json
import os
import re
# no need for collections.Iterable (removed in newer Python versions)

try:
    from gensim.models import Word2Vec, FastText
except Exception:
    Word2Vec = None
    FastText = None
try:
    from ..utils.experiment_logger import enrich_record, make_run_id
except Exception:
    def enrich_record(r, **kw):
        return r
    def make_run_id():
        return 'local'

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def read_sentences(jsonl_path):
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = rec.get("text", "")
            tokens = TOKEN_RE.findall(text.lower())
            if tokens:
                yield tokens


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def train_word2vec(sentences, output_dir, size=100, window=5, min_count=2, epochs=5, workers=1):
    if Word2Vec is None:
        raise RuntimeError("gensim.Word2Vec not available. Install gensim in the environment.")
    print("Training Word2Vec: size=%d window=%d min_count=%d epochs=%d" % (size, window, min_count, epochs))
    model = Word2Vec(sentences=sentences, vector_size=size, window=window, min_count=min_count, workers=workers, epochs=epochs)
    out_path = os.path.join(output_dir, "word2vec.model")
    model.save(out_path)
    print(f"Saved Word2Vec model to {out_path}")
    return out_path


def train_fasttext(sentences, output_dir, size=100, window=5, min_count=2, epochs=5, workers=1):
    if FastText is None:
        raise RuntimeError("gensim.FastText not available. Install gensim in the environment.")
    print("Training FastText: size=%d window=%d min_count=%d epochs=%d" % (size, window, min_count, epochs))
    model = FastText(sentences=sentences, vector_size=size, window=window, min_count=min_count, workers=workers, epochs=epochs)
    out_path = os.path.join(output_dir, "fasttext.model")
    model.save(out_path)
    print(f"Saved FastText model to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Train embeddings on normalized Voynich JSONL")
    parser.add_argument("input", help="Path to normalized JSONL with `text` field")
    parser.add_argument("--output", default="models", help="Directory to save models")
    parser.add_argument("--model", choices=["word2vec", "fasttext", "both"], default="both")
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    ensure_dir(args.output)
    sentences = list(read_sentences(args.input))
    if not sentences:
        print("No sentences found in input; aborting.")
        return

    # For small toy runs, min_count may be 1
    saved = {}
    if args.model in ("word2vec", "both"):
        try:
            saved['word2vec'] = train_word2vec(sentences, args.output, size=args.size, window=args.window, min_count=args.min_count, epochs=args.epochs, workers=args.workers)
        except Exception as e:
            print("Word2Vec training failed:", e)

    if args.model in ("fasttext", "both"):
        try:
            saved['fasttext'] = train_fasttext(sentences, args.output, size=args.size, window=args.window, min_count=args.min_count, epochs=args.epochs, workers=args.workers)
        except Exception as e:
            print("FastText training failed:", e)

    # Quick sanity check: print most-similar for top tokens if Word2Vec saved
    try:
        from gensim.models import Word2Vec as W2
        if 'word2vec' in saved:
            m = W2.load(saved['word2vec'])
            vocab = list(m.wv.index_to_key)[:10]
            print("Sample vocab:", vocab)
            if 'zot' in m.wv:
                print("Most similar to 'zot':", m.wv.most_similar('zot', topn=5))
    except Exception:
        pass

    # write metadata about this training run for provenance
    meta = {
        'run_id': make_run_id(),
        'input': args.input,
        'model_requested': args.model,
        'params': {
            'size': args.size,
            'window': args.window,
            'min_count': args.min_count,
            'epochs': args.epochs,
            'workers': args.workers,
        },
        'saved': saved,
    }
    try:
        import json
        with open(os.path.join(args.output, 'embeddings_training_metadata.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
        print('Wrote training metadata to', os.path.join(args.output, 'embeddings_training_metadata.json'))
    except Exception:
        pass


if __name__ == "__main__":
    main()
