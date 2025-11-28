"""Simple experiment logger to standardize hypothesis metadata.

Functions here help ensure records include `timestamp`, `run_id`, `input_file`,
`model` and `params`. They do not enforce provenance but make aggregation
consistent when scripts call `record_experiment` before writing logs.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import uuid


def make_run_id() -> str:
    return uuid.uuid4().hex


def enrich_record(record: Dict[str, Any], *, run_id: str | None = None, input_file: str | None = None, model: str | None = None, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    out = dict(record) if record is not None else {}
    out.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
    out.setdefault('run_id', run_id or make_run_id())
    if input_file:
        out.setdefault('input_file', input_file)
    if model:
        out.setdefault('model', model)
    if params:
        out.setdefault('params', params)
    return out


def write_jsonl(path: str | Path, records: list[Dict[str, Any]]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
