#!/usr/bin/env python3
"""Command-line entrypoint for common project tasks.

Usage: python3 src/cli.py <subcommand> [options]

Subcommands:
  ingest              Run `src/ingest/ingest.py`
  tokenize            Run `src/ingest/tokenize.py`
  stats               Run `src/analytics/stats.py`
  train-embeddings    Run `src/embeddings/train.py`
  sentence-embeddings Run `src/embeddings/sentence_embeddings.py`
  llm                 Run `src/llm/local_llm_runner.py`
  overlay             Run `src/visualization/overlay.py`
  smoke               Run `scripts/smoke_run.sh`

This CLI is a thin wrapper that calls the existing scripts in the repo.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd: list[str]):
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("Command failed with exit code", e.returncode, file=sys.stderr)
        sys.exit(e.returncode)


def cmd_ingest(args: argparse.Namespace):
    script = ROOT / 'src' / 'ingest' / 'ingest.py'
    cmd = [sys.executable, str(script), args.input, '-o', args.output]
    if args.no_strip_html:
        cmd.append('--no-strip-html')
    if args.no_remove_numbers:
        cmd.append('--no-remove-numbers')
    if args.no_remove_uncertainty:
        cmd.append('--no-remove-uncertainty')
    run_cmd(cmd)


def cmd_tokenize(args: argparse.Namespace):
    script = ROOT / 'src' / 'ingest' / 'tokenize.py'
    cmd = [sys.executable, str(script), args.input, '-o', args.output]
    run_cmd(cmd)


def cmd_stats(args: argparse.Namespace):
    script = ROOT / 'src' / 'analytics' / 'stats.py'
    cmd = [sys.executable, str(script), args.input, '-o', args.output]
    if args.top:
        cmd.extend(['--top', str(args.top)])
    run_cmd(cmd)


def cmd_train(args: argparse.Namespace):
    script = ROOT / 'src' / 'embeddings' / 'train.py'
    cmd = [sys.executable, str(script), args.input, '--output', args.output, '--model', args.model]
    if args.size:
        cmd.extend(['--size', str(args.size)])
    if args.epochs:
        cmd.extend(['--epochs', str(args.epochs)])
    run_cmd(cmd)


def cmd_sentence_emb(args: argparse.Namespace):
    script = ROOT / 'src' / 'embeddings' / 'sentence_embeddings.py'
    cmd = [sys.executable, str(script)]
    run_cmd(cmd)


def cmd_llm(args: argparse.Namespace):
    script = ROOT / 'src' / 'llm' / 'local_llm_runner.py'
    cmd = [sys.executable, str(script)]
    if args.model:
        cmd.extend(['--model', args.model])
    if args.max_new_tokens:
        cmd.extend(['--max_new_tokens', str(args.max_new_tokens)])
    run_cmd(cmd)


def cmd_overlay(args: argparse.Namespace):
    script = ROOT / 'src' / 'visualization' / 'overlay.py'
    cmd = [sys.executable, str(script)]
    run_cmd(cmd)


def cmd_smoke(args: argparse.Namespace):
    script = ROOT / 'scripts' / 'smoke_run.sh'
    cmd = [str(script)]
    run_cmd(cmd)


def cmd_aggregate(args: argparse.Namespace):
    script = ROOT / 'src' / 'llm' / 'aggregate_hypotheses.py'
    cmd = [sys.executable, str(script)]
    run_cmd(cmd)


def cmd_compare_corpora(args: argparse.Namespace):
    script = ROOT / 'src' / 'compare' / 'compare_corpora.py'
    cmd = [sys.executable, str(script), '--voynich', args.voynich, '--corpora', args.corpora, '--out', args.out]
    run_cmd(cmd)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog='voynich-cli')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_ing = sub.add_parser('ingest', help='Run ingest script')
    p_ing.add_argument('input')
    p_ing.add_argument('-o', '--output', default=str(ROOT / 'data' / 'processed' / 'transcription.jsonl'))
    p_ing.add_argument('--no-strip-html', action='store_true')
    p_ing.add_argument('--no-remove-numbers', action='store_true')
    p_ing.add_argument('--no-remove-uncertainty', action='store_true')
    p_ing.set_defaults(func=cmd_ingest)

    p_tok = sub.add_parser('tokenize', help='Run tokenize script')
    p_tok.add_argument('input')
    p_tok.add_argument('-o', '--output', default=str(ROOT / 'data' / 'processed' / 'tokens.jsonl'))
    p_tok.set_defaults(func=cmd_tokenize)

    p_stats = sub.add_parser('stats', help='Run stats analysis')
    p_stats.add_argument('input')
    p_stats.add_argument('-o', '--output', default=str(ROOT / 'data' / 'processed' / 'ngrams.json'))
    p_stats.add_argument('--top', type=int, default=20)
    p_stats.set_defaults(func=cmd_stats)

    p_train = sub.add_parser('train-embeddings', help='Train gensim embeddings')
    p_train.add_argument('input')
    p_train.add_argument('--output', default=str(ROOT / 'models' / 'gensim'))
    p_train.add_argument('--model', choices=['word2vec', 'fasttext', 'both'], default='both')
    p_train.add_argument('--size', type=int, default=100)
    p_train.add_argument('--epochs', type=int, default=5)
    p_train.set_defaults(func=cmd_train)

    p_sent = sub.add_parser('sentence-embeddings', help='Sentence embeddings + clustering')
    p_sent.set_defaults(func=cmd_sentence_emb)

    p_llm = sub.add_parser('llm', help='Run local LLM runner')
    p_llm.add_argument('--model', default='google/flan-t5-small')
    p_llm.add_argument('--max_new_tokens', type=int, default=128)
    p_llm.set_defaults(func=cmd_llm)

    p_ov = sub.add_parser('overlay', help='Generate overlays')
    p_ov.set_defaults(func=cmd_overlay)

    p_sm = sub.add_parser('smoke', help='Run smoke test script')
    p_sm.set_defaults(func=cmd_smoke)

    p_agg = sub.add_parser('aggregate-hypotheses', help='Aggregate hypothesis logs in reports/hypotheses')
    p_agg.set_defaults(func=cmd_aggregate)

    p_cmp = sub.add_parser('compare-corpora', help='Compare Voynich with corpora')
    p_cmp.add_argument('--voynich', default=str(ROOT / 'data' / 'processed' / 'voynich_takahashi.jsonl'))
    p_cmp.add_argument('--corpora', default=str(ROOT / 'data' / 'corpora'))
    p_cmp.add_argument('--out', default=str(ROOT / 'reports' / 'comparison'))
    p_cmp.set_defaults(func=cmd_compare_corpora)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
