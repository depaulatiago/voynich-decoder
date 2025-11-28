#!/usr/bin/env python3
"""Run prompts locally with a small HF model (Flan-T5 small) and save responses.

Reads prompts from `reports/hypotheses/prompts.jsonl` (one JSON per line with fields
like `id` and `prompt`) and writes outputs to
`reports/hypotheses/llm_responses_local.jsonl`.

This is intended for quick, local hypothesis generation. For higher-quality
responses you may run a larger model or call a remote LLM.
"""
from pathlib import Path
import json
import sys
import argparse

ROOT = Path('.').resolve()
INP = ROOT / 'reports' / 'hypotheses' / 'prompts.jsonl'
OUT = ROOT / 'reports' / 'hypotheses' / 'llm_responses_local.jsonl'
OUT.parent.mkdir(parents=True, exist_ok=True)


def load_prompts():
    if not INP.exists():
        print('No prompts file found at', INP, file=sys.stderr)
        return []
    prompts = []
    with INP.open('r', encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            try:
                obj = json.loads(line)
            except Exception:
                obj = {'id': i, 'prompt': line.strip()}
            prompts.append(obj)
    return prompts


def truncate_text_to_tokenizer(text, tokenizer, max_len=None):
    # truncate based on tokenizer.model_max_length if available
    m = max_len or getattr(tokenizer, 'model_max_length', None) or 512
    toks = tokenizer.encode(text, add_special_tokens=False)
    if len(toks) > m - 4:
        toks = toks[: m - 4]
        return tokenizer.decode(toks, skip_special_tokens=True)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='google/flan-t5-small', help='HF model name (text2text)')
    parser.add_argument('--max_new_tokens', type=int, default=128)
    parser.add_argument('--temperature', type=float, default=0.7)
    parser.add_argument('--top_p', type=float, default=0.9)
    args = parser.parse_args()

    prompts = load_prompts()
    if not prompts:
        print('No prompts to run.')
        return

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
    except Exception as e:
        print('Please install transformers and sentencepiece in the .venv:', e, file=sys.stderr)
        raise

    model_name = args.model
    print('Loading model', model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    gen = pipeline('text2text-generation', model=model, tokenizer=tokenizer, device=-1)

    with OUT.open('w', encoding='utf-8') as fh:
        for idx, obj in enumerate(prompts):
            prompt_text = obj.get('prompt') or obj.get('text') or obj.get('prompt_text') or ''
            if not prompt_text:
                continue
            prompt_text = truncate_text_to_tokenizer(prompt_text, tokenizer)
            try:
                out = gen(prompt_text, max_new_tokens=args.max_new_tokens, do_sample=True, top_p=args.top_p, temperature=args.temperature)
                resp = out[0].get('generated_text') or out[0].get('summary_text') or ''
            except Exception as e:
                resp = f'ERROR: {e}'
            record = {
                'id': obj.get('id', idx),
                'prompt': prompt_text,
                'response': resp,
                'model': model_name
            }
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
            print('Wrote response for prompt id', record['id'])


if __name__ == '__main__':
    main()
