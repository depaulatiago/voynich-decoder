#!/usr/bin/env python3
"""Run simple hypothesis generation over input text and write JSONL records.

This minimal runner prefers a light-weight local rule-based generator so it
works without heavy dependencies. If `HUGGINGFACE_API_KEY` or similar is
available and `transformers` is installed, it may use a small model.

Outputs go to `reports/hypotheses/run_hypotheses.jsonl` by default.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Iterable
import os

try:
    from ..utils.experiment_logger import enrich_record, make_run_id
except Exception:
    def enrich_record(r: Dict[str, Any], **kw):
        r.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
        r.setdefault('run_id', 'local')
        return r
    def make_run_id():
        return 'local'


def try_load_transformers(model_name: str):
    """Attempt to create a transformers text-generation pipeline for a local model.
    Returns a callable generate(prompt) -> str or None if unavailable."""
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        # prefer causal models like distilgpt2 or gpt2
        tok = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        gen = pipeline('text-generation', model=model, tokenizer=tok, device=-1)

        def generate(prompt: str) -> str:
            out = gen(prompt, max_length=min(200, len(prompt.split()) + 50), do_sample=True, top_k=50, num_return_sequences=1)
            return out[0]['generated_text']

        return generate
    except Exception:
        return None


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / 'reports' / 'hypotheses'
OUT_PATH = OUT_DIR / 'run_hypotheses.jsonl'


def simple_rule_generate(text: str) -> str:
    # Very small heuristic: identify frequent tokens and propose they map to common nouns
    tokens = [t for t in text.split() if t.strip()]
    if not tokens:
        return 'No tokens to generate hypothesis.'
    top = tokens[0]
    return f"Hypothesis: token '{top}' may represent a common noun or determiner. Frequency hint: {len(tokens)} tokens."


def read_inputs(path: Path) -> Iterable[str]:
    if not path.exists():
        return []
    if path.suffix == '.jsonl':
        with path.open('r', encoding='utf-8') as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    obj = json.loads(ln)
                    # try to extract a text field
                    txt = obj.get('text') or obj.get('line') or obj.get('content') or obj.get('raw') or obj.get('transcription')
                    if txt:
                        yield txt
                except Exception:
                    yield ln
    else:
        with path.open('r', encoding='utf-8') as fh:
            yield fh.read()


def generate_records(input_path: Path, model_name: str | None = None, run_id: str | None = None):
    run_id = run_id or make_run_id()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    generator = None
    if model_name:
        generator = try_load_transformers(model_name)
        if generator is None:
            print('Warning: requested local model', model_name, 'but transformers or model not available. Falling back to rule-based generator.')

    for txt in read_inputs(input_path):
        if generator:
            try:
                resp = generator(txt)
            except Exception:
                resp = simple_rule_generate(txt)
        else:
            resp = simple_rule_generate(txt)

        rec: Dict[str, Any] = {
            'prompt': txt[:400],
            'response': resp,
            'model': model_name or 'local-rule',
        }
        rec = enrich_record(rec, run_id=run_id, input_file=str(input_path), model=model_name or 'local-rule')
        records.append(rec)

    with OUT_PATH.open('w', encoding='utf-8') as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    print('Wrote', len(records), 'hypothesis records to', OUT_PATH)
    return OUT_PATH


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('input', nargs='?', default=str(ROOT / 'example_transcription.txt'))
    p.add_argument('--model', default=None)
    p.add_argument('--out', default=str(OUT_PATH))
    args = p.parse_args(argv)
    input_path = Path(args.input)
    return generate_records(input_path, model_name=args.model)


if __name__ == '__main__':
    main()
