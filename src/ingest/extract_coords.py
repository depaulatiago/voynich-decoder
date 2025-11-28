#!/usr/bin/env python3
"""Create a small example `token_coords.jsonl` for overlay demos.

This script creates `data/processed/token_coords_example.jsonl` with a few
example token coordinate records matching the expected `docs/token_coords.md` spec.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'processed' / 'token_coords_example.jsonl'


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample = [
        {"token": "daiin", "page": "f1r", "x": 120, "y": 340, "w": 40, "h": 12},
        {"token": "qokedy", "page": "f1r", "x": 170, "y": 340, "w": 46, "h": 12},
        {"token": "ol", "page": "f2v", "x": 52, "y": 210, "w": 28, "h": 10},
    ]
    with OUT.open('w', encoding='utf-8') as fh:
        for r in sample:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('Wrote example token coords to', OUT)


if __name__ == '__main__':
    main()
