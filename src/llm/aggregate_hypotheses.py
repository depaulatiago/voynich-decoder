#!/usr/bin/env python3
"""Aggregate and normalize hypothesis logs in `reports/hypotheses/`.

This script reads JSONL files from `reports/hypotheses/` (for example
`prompts.jsonl`, `llm_responses_local.jsonl`, `rule_based.jsonl`) and
produces:

- `reports/hypotheses/hypotheses_aggregated.jsonl` : normalized JSONL
- `reports/hypotheses/hypotheses_summary.md`       : human-readable summary
- `reports/hypotheses/hypotheses_summary.csv`      : CSV table for analysis

Normalization policy (fields in output JSONL):
- id: original id if present, else generated
- source: filename where record came from
- timestamp: if present in record, else file mtime (ISO)
- prompt: input prompt or text
- response: model output or rule output
- model: model name if present
- notes: any leftover fields serialized as JSON string

Usage: python3 src/llm/aggregate_hypotheses.py
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
import csv
import os
import sys
from typing import Any, Dict
try:
    from ..utils.experiment_logger import enrich_record
except Exception:
    # fallback if utils not importable; define no-op enrich
    def enrich_record(r, **kw):
        return r

ROOT = Path(__file__).resolve().parents[2]
HYP_DIR = ROOT / 'reports' / 'hypotheses'
OUT_JSONL = HYP_DIR / 'hypotheses_aggregated.jsonl'
OUT_MD = HYP_DIR / 'hypotheses_summary.md'
OUT_CSV = HYP_DIR / 'hypotheses_summary.csv'


def list_jsonl_files(d: Path):
    if not d.exists():
        return []
        # Exclude output files to avoid circular processing
        excluded = {'hypotheses_aggregated.jsonl', 'hypotheses_summary.jsonl'}
        return sorted([p for p in d.iterdir() 
                       if p.is_file() and p.suffix == '.jsonl' and p.name not in excluded])


def load_records(path: Path):
    with path.open('r', encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                # fallback: wrap raw line as prompt
                obj = {'prompt': ln}
            yield obj


def iso_from_mtime(p: Path):
    try:
        m = p.stat().st_mtime
        return datetime.fromtimestamp(m, timezone.utc).isoformat()
    except Exception:
        return ''


def normalize_record(obj: Dict[str, Any], source: str, fallback_ts: str, gen_id: int):
    # pick id
    rid = obj.get('id') or obj.get('idx') or obj.get('prompt_id') or f'gen-{gen_id}'
    # timestamp
    ts = obj.get('timestamp') or obj.get('time') or obj.get('created_at') or fallback_ts
    # prompt
    prompt = obj.get('prompt') or obj.get('text') or obj.get('input') or obj.get('query') or ''
    # response
    response = obj.get('response') or obj.get('answer') or obj.get('generated_text') or obj.get('summary_text') or ''
    # model
    model = obj.get('model') or obj.get('model_name') or ''
    # notes: capture extra fields
    extras = {k: v for k, v in obj.items() if k not in {'id', 'idx', 'prompt_id', 'timestamp', 'time', 'created_at', 'prompt', 'text', 'input', 'query', 'response', 'answer', 'generated_text', 'summary_text', 'model', 'model_name'}}
    notes = ''
    if extras:
        try:
            notes = json.dumps(extras, ensure_ascii=False)
        except Exception:
            notes = str(extras)

    base = {
        'id': rid,
        'source': source,
        'timestamp': ts,
        'prompt': prompt,
        'response': response,
        'model': model,
        'notes': notes,
    }
    # enrich with experiment metadata if available
    try:
        enriched = enrich_record(base)
        return enriched
    except Exception:
        return base


def aggregate():
    files = list_jsonl_files(HYP_DIR)
    if not files:
        # Gracefully create empty artifacts so CI passes
        empty_md = ['# Hypotheses aggregation summary', '', f'Generated: {datetime.now(timezone.utc).isoformat()}', '', '## Source file counts', '', 'No source hypothesis files found.', '', 'Total records: **0**', '', '## Sample entries (first 10)', '', '(none)']
        HYP_DIR.mkdir(parents=True, exist_ok=True)
        with OUT_JSONL.open('w', encoding='utf-8') as fh_json, \
             OUT_CSV.open('w', encoding='utf-8', newline='') as fh_csv, \
             OUT_MD.open('w', encoding='utf-8') as fh_md:
            # write valid but empty jsonl (just a comment line for clarity)
            fh_json.write('')
            # write csv header
            writer = csv.writer(fh_csv)
            writer.writerow(['id','source','timestamp','prompt','response','model','notes'])
            # write markdown summary
            fh_md.write('\n'.join(empty_md) + '\n')
        print('No source hypothesis files; created empty artifacts.', file=sys.stderr)
        return 0

    aggregated = []
    gen_id = 1
    counts = {}
    for f in files:
        fallback_ts = iso_from_mtime(f)
        n = 0
        for obj in load_records(f):
            rec = normalize_record(obj, f.name, fallback_ts, gen_id)
            aggregated.append(rec)
            gen_id += 1
            n += 1
        counts[f.name] = n

    # write aggregated jsonl
    with OUT_JSONL.open('w', encoding='utf-8') as fh:
        for r in aggregated:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    # write CSV
    with OUT_CSV.open('w', encoding='utf-8', newline='') as fh:
        cols = ['id', 'source', 'timestamp', 'model', 'prompt', 'response', 'notes']
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in aggregated:
            w.writerow({k: (r.get(k) or '') for k in cols})

    # write summary markdown
    with OUT_MD.open('w', encoding='utf-8') as fh:
        fh.write('# Hypotheses aggregation summary\n\n')
        fh.write(f'Generated: {datetime.now(timezone.utc).isoformat()}\n\n')
        fh.write('## Source file counts\n\n')
        for k, v in counts.items():
            fh.write(f'- **{k}**: {v} records\n')
        fh.write('\n')
        fh.write(f'Total records: **{len(aggregated)}**\n\n')

        fh.write('## Sample entries (first 10)\n\n')
        for r in aggregated[:10]:
            fh.write('---\n')
            fh.write(f"- id: {r.get('id')}\n")
            fh.write(f"  source: {r.get('source')}\n")
            fh.write(f"  timestamp: {r.get('timestamp')}\n")
            if r.get('model'):
                fh.write(f"  model: {r.get('model')}\n")
            prompt_text = r.get('prompt', '')[:400].replace('\n', '\n    ')
            response_text = r.get('response', '')[:400].replace('\n', '\n    ')
            fh.write(f"  prompt: >\n    {prompt_text}\n")
            fh.write(f"  response: >\n    {response_text}\n")

    print('Wrote aggregated JSONL to', OUT_JSONL)
    print('Wrote CSV to', OUT_CSV)
    print('Wrote summary to', OUT_MD)
    return 0


def main(argv=None):
    HYP_DIR.mkdir(parents=True, exist_ok=True)
    return aggregate()


if __name__ == '__main__':
    sys.exit(main())
