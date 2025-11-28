#!/usr/bin/env python3
"""Orchestrate a full experiment run: ingest -> tokenize -> metrics -> hypotheses -> compare -> aggregate.

This script calls existing utilities and writes a lightweight final report pointer.
It prefers existing scripts in `src/` and will fail fast if any step errors.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run(cmd, cwd=None):
    print('>',' '.join(cmd))
    p = subprocess.run(cmd, cwd=cwd or str(ROOT))
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def main(argv=None):
    # default inputs/outputs
    example = ROOT / 'example_transcription.txt'
    processed = ROOT / 'data' / 'processed'

    # 1) ingest
    run([sys.executable, str(ROOT / 'src' / 'ingest' / 'ingest.py'), str(example), '-o', str(processed / 'voynich_run.jsonl')])

    # 2) tokenize
    run([sys.executable, str(ROOT / 'src' / 'ingest' / 'tokenize.py'), str(processed / 'voynich_run.jsonl'), '-o', str(processed / 'voynich_run_tokens.jsonl')])

    # 3) metrics
    run([sys.executable, str(ROOT / 'src' / 'analysis' / 'report_metrics.py'), '--input', str(processed / 'voynich_run.jsonl'), '--out', str(ROOT / 'reports')])

    # 4) hypotheses (LLM or rule)
    run([sys.executable, str(ROOT / 'src' / 'llm' / 'run_hypotheses.py'), str(processed / 'voynich_run.jsonl')])

    # 5) compare corpora (use all files in data/corpora)
    run([sys.executable, str(ROOT / 'src' / 'compare' / 'compare_corpora.py'), '--voynich', str(processed / 'voynich_run.jsonl'), '--corpora', str(ROOT / 'data' / 'corpora'), '--out', str(ROOT / 'reports' / 'comparison')])

    # 6) aggregate hypotheses
    run([sys.executable, str(ROOT / 'src' / 'llm' / 'aggregate_hypotheses.py')])

    print('\nFull pipeline finished. Important artifacts:')
    print('- reports/experiment_metrics.json')
    print('- reports/hypotheses/hypotheses_aggregated.jsonl')
    print('- reports/comparison/')


if __name__ == '__main__':
    main()
