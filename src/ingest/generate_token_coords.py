#!/usr/bin/env python3
"""Generate token coordinates for manuscript images.

This script creates a token_coords.jsonl file with simulated bounding boxes
for tokens, distributed across the available folio images.
Since we don't have actual OCR coordinates, we generate plausible positions
based on typical manuscript layout patterns.
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any


def load_tokens(tokens_file: Path) -> List[Dict[str, Any]]:
    """Load tokenized data."""
    tokens = []
    if not tokens_file.exists():
        print(f"Warning: {tokens_file} not found")
        return tokens
    
    with tokens_file.open('r', encoding='utf-8') as f:
        for line in f:
            try:
                tokens.append(json.loads(line))
            except Exception as e:
                print(f"Error parsing line: {e}")
    return tokens


def get_available_folios(images_dir: Path) -> List[str]:
    """Get list of available folio identifiers from images directory."""
    if not images_dir.exists():
        return []
    
    folios = []
    for img_path in images_dir.glob('*.jpg'):
        # Extract folio identifier (e.g., '1r', '103v', '25r')
        name = img_path.stem
        if name != 'inside-front':  # Skip non-folio images
            folios.append(name)
    
    return sorted(folios)


def generate_coords(tokens: List[Dict], folios: List[str], seed: int = 42) -> List[Dict]:
    """Generate plausible bounding box coordinates for tokens.
    
    Args:
        tokens: List of token dictionaries with 'line', 'token_index', 'token'
        folios: List of folio identifiers to distribute tokens across
        seed: Random seed for reproducibility
    
    Returns:
        List of coordinate records with format:
        {"token": str, "folio": str, "bbox": [x, y, w, h], "line_id": int, "token_index": int}
    """
    random.seed(seed)
    coords = []
    
    if not folios:
        print("No folios available, using placeholder 'f1r'")
        folios = ['f1r']
    
    # Typical manuscript layout constants (pixels, assuming ~2000x3000 image)
    MARGIN_LEFT = 200
    MARGIN_TOP = 300
    LINE_HEIGHT = 80
    TOKEN_BASE_WIDTH = 60
    TOKEN_HEIGHT = 40
    CHAR_WIDTH = 12  # approximate pixels per character
    SPACING = 20
    
    # Group tokens by line
    lines = {}
    for token_rec in tokens:
        line_id = token_rec.get('line', 1)
        if line_id not in lines:
            lines[line_id] = []
        lines[line_id].append(token_rec)
    
    # Distribute lines across available folios
    sorted_lines = sorted(lines.keys())
    lines_per_folio = max(1, len(sorted_lines) // len(folios))
    
    for i, line_id in enumerate(sorted_lines):
        folio_idx = min(i // lines_per_folio, len(folios) - 1)
        folio = folios[folio_idx]
        
        # Calculate line position
        line_offset = (i % lines_per_folio) * LINE_HEIGHT
        y = MARGIN_TOP + line_offset
        
        # Position tokens horizontally within the line
        x = MARGIN_LEFT
        for token_rec in lines[line_id]:
            token = token_rec.get('token', '')
            token_index = token_rec.get('token_index', 0)
            
            # Calculate width based on token length
            w = max(TOKEN_BASE_WIDTH, len(token) * CHAR_WIDTH)
            h = TOKEN_HEIGHT
            
            # Add some random jitter for realism
            x_jitter = random.randint(-5, 5)
            y_jitter = random.randint(-3, 3)
            
            coord_rec = {
                'token': token,
                'folio': folio,
                'bbox': [x + x_jitter, y + y_jitter, w, h],
                'line_id': line_id,
                'token_index': token_index
            }
            coords.append(coord_rec)
            
            x += w + SPACING
    
    return coords


def main():
    root = Path(__file__).resolve().parents[2]
    tokens_file = root / 'data' / 'processed' / 'voynich_run_tokens.jsonl'
    images_dir = root / 'data' / 'external' / 'images'
    output_file = root / 'data' / 'processed' / 'token_coords.jsonl'
    
    print(f"Loading tokens from {tokens_file}")
    tokens = load_tokens(tokens_file)
    print(f"Loaded {len(tokens)} tokens")
    
    print(f"Scanning images directory: {images_dir}")
    folios = get_available_folios(images_dir)
    print(f"Found {len(folios)} folios: {folios}")
    
    print("Generating coordinates...")
    coords = generate_coords(tokens, folios)
    print(f"Generated {len(coords)} coordinate records")
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w', encoding='utf-8') as f:
        for rec in coords:
            f.write(json.dumps(rec) + '\n')
    
    print(f"Wrote coordinates to {output_file}")
    print("\nSample records:")
    for rec in coords[:5]:
        print(f"  {rec}")


if __name__ == '__main__':
    main()
