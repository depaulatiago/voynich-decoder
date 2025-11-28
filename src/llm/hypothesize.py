#!/usr/bin/env python3
"""
Generate LLM prompts from cluster outputs and nearest-neighbors.

Produces a JSONL file with one prompt per cluster. By default runs in --dry-run
mode which only writes the prompts to disk and prints a short summary.

Optional: with --call openai will attempt to call OpenAI ChatCompletion if
`openai` is installed and `OPENAI_API_KEY` is set. Use with care.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, Any


PROMPT_TEMPLATE = (
    "You are a scholarly assistant analyzing a cluster of Voynich tokens.\n"
    "Given the top tokens below and some nearest-neighbor examples, produce:\n"
    "1) a concise (2-3 sentence) hypothesis about what unifying pattern these tokens might represent (morpheme, affix, word family, scribal variant, etc.),\n"
    "2) up to 3 suggested simple checks (n-gram overlaps, positional patterns, frequency tests) the researcher can run to validate the hypothesis,\n"
    "3) any immediate caveats or alternate interpretations.\n\n"
    "Top tokens: {top_tokens}\n"
    "Sample neighbors (token -> neighbors):\n{sample_neighbors}\n\n"
    "Write output as a short, enumerated answer with explicit steps. Be concise and factual.\n"
)


def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def build_prompt(cluster_id: str, top_terms: list, sample_neighbors: Dict[str, list]) -> str:
    top = ', '.join([t for t, _ in top_terms[:30]])
    # format neighbors
    neigh_lines = []
    for tok, neighbors in sample_neighbors.items():
        neigh_lines.append(f"- {tok}: {', '.join(neighbors[:8])}")
    neigh_text = '\n'.join(neigh_lines) if neigh_lines else '(no sample neighbors)'
    return PROMPT_TEMPLATE.format(top_tokens=top, sample_neighbors=neigh_text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--clusters', type=Path, default=Path('notebooks/outputs/top_terms_by_cluster_gensim.json'), help='JSON file with top terms per cluster')
    p.add_argument('--nns', type=Path, default=Path('notebooks/outputs/gensim_sample_nn.json'), help='JSON file with sample nearest neighbors')
    p.add_argument('--out', type=Path, default=Path('reports/hypotheses/prompts.jsonl'), help='Output JSONL with prompts')
    p.add_argument('--dry-run', action='store_true', help='Do not call any external API; only write prompts')
    p.add_argument('--call', choices=['openai'], help='If specified, call the named API (requires env vars).')
    p.add_argument('--sample-per-cluster', type=int, default=3, help='How many sample neighbor tokens to include per cluster')
    args = p.parse_args()

    clusters_path = args.clusters
    nns_path = args.nns
    out_path = args.out

    clusters = load_json(clusters_path) if clusters_path.exists() else {}
    nns = load_json(nns_path) if nns_path.exists() else {}

    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open('w', encoding='utf-8') as fh:
        for k_str, top_terms in clusters.items():
            # collect a few sample neighbors for tokens appearing in top_terms
            sample_neighbors = {}
            for tok, _ in top_terms[:args.sample_per_cluster*2]:
                if tok in nns:
                    sample_neighbors[tok] = nns[tok][:args.sample_per_cluster]
                if len(sample_neighbors) >= args.sample_per_cluster:
                    break

            prompt_text = build_prompt(k_str, top_terms, sample_neighbors)

            entry = {
                'cluster_id': str(k_str),
                'top_terms': [t for t,_ in top_terms[:50]],
                'sample_neighbors': sample_neighbors,
                'prompt': prompt_text,
            }
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
            written += 1

    print(f'Wrote {written} prompts to {out_path}')

    # optional API call (explicit)
    if args.call:
        if args.dry_run:
            print('Dry-run: skipping external API call (use --no-dry-run to actually call).')
            return
        if args.call == 'openai':
            try:
                import os
                import openai
                openai.api_key = os.environ.get('OPENAI_API_KEY')
                if not openai.api_key:
                    print('OPENAI_API_KEY not set; aborting call.')
                    return
                # read prompts and call OpenAI ChatCompletion per prompt (small batch)
                responses = []
                with out_path.open('r', encoding='utf-8') as fh:
                    for line in fh:
                        data = json.loads(line)
                        msg = [{'role':'system','content':'You are a concise scholarly assistant.'}, {'role':'user','content': data['prompt']}]
                        resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=msg, temperature=0.2, max_tokens=400)
                        text = resp['choices'][0]['message']['content']
                        responses.append({'cluster_id': data['cluster_id'], 'response': text})
                resp_path = out_path.parent / 'openai_responses.jsonl'
                with resp_path.open('w', encoding='utf-8') as fh2:
                    for r in responses:
                        fh2.write(json.dumps(r, ensure_ascii=False) + '\n')
                print('Saved OpenAI responses to', resp_path)
            except Exception as e:
                print('OpenAI call failed:', e)


if __name__ == '__main__':
    main()
