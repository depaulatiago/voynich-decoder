"""Helper functions to create visual overlays of tokens on manuscript images.

This module expects:
- manuscript images in `data/external/images/` named like `folio_001.png` or similar
- a token->coords JSONL at `data/processed/token_coords.jsonl` with records:
  {"token": "daiin", "folio": "f001r", "bbox": [x,y,w,h], "line_id": 123, "token_index": 4}

If token_coords is missing, the module will report what is required.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import random


# Always use project root, regardless of where script is called from
ROOT = Path(__file__).resolve().parents[2]
IM_DIR = ROOT / 'data' / 'external' / 'images'
COORDS = ROOT / 'data' / 'processed' / 'token_coords.jsonl'
OUT = ROOT / 'reports' / 'figures' / 'overlays'
OUT.mkdir(parents=True, exist_ok=True)


def load_coords():
    if not COORDS.exists():
        print('No token_coords.jsonl found at', COORDS)
        return []
    recs = []
    with COORDS.open('r', encoding='utf-8') as fh:
        for ln in fh:
            try:
                recs.append(json.loads(ln))
            except Exception:
                continue
    return recs


def generate_color_palette(n: int, seed: int = 42) -> List[tuple]:
    """Generate n visually distinct colors."""
    random.seed(seed)
    colors = []
    for i in range(n):
        hue = (i * 137.5) % 360  # Golden angle for good distribution
        saturation = 0.7 + random.random() * 0.3
        value = 0.7 + random.random() * 0.3
        # Convert HSV to RGB
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue / 360, saturation, value)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


def assign_token_colors(coords: List[Dict[str, Any]]) -> Dict[str, tuple]:
    """Assign a unique color to each unique token for visualization."""
    unique_tokens = sorted({r.get('token', '') for r in coords if r.get('token')})
    palette = generate_color_palette(len(unique_tokens))
    return {token: palette[i] for i, token in enumerate(unique_tokens)}


def overlays_for_folio(
    folio: str, 
    coords: List[Dict[str, Any]], 
    out_dir: Path = OUT, 
    image_dir: Path = IM_DIR,
    color_by_token: bool = True,
    show_labels: bool = True,
    show_legend: bool = True
):
    """Generate overlay visualization for a specific folio.
    
    Args:
        folio: Folio identifier (e.g., '1r', '103v')
        coords: List of coordinate records
        out_dir: Output directory for overlay images
        image_dir: Directory containing manuscript images
        color_by_token: If True, color boxes by token; else use single color
        show_labels: If True, show token text above bounding boxes
        show_legend: If True, add legend showing token-color mapping
    """
    # find image file for folio
    candidates = list(image_dir.glob(f'*{folio}*'))
    if not candidates:
        print('No image found for folio', folio, 'in', image_dir)
        return None
    img_p = candidates[0]
    img = Image.open(img_p).convert('RGBA')

    overlay = Image.new('RGBA', img.size, (255,255,255,0))
    draw = ImageDraw.Draw(overlay)

    # Load font
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    except:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    # Get colors for tokens
    folio_coords = [r for r in coords if str(r.get('folio')) == str(folio)]
    if not folio_coords:
        print(f'No coordinates found for folio {folio}')
        return None
    
    token_colors = assign_token_colors(folio_coords) if color_by_token else {}
    default_color = (255, 0, 0)

    # Draw bounding boxes and labels
    for r in folio_coords:
        bbox = r.get('bbox')
        token = r.get('token', '')
        if not bbox:
            continue
        
        x, y, w, h = bbox
        rect = [x, y, x + w, y + h]
        
        color = token_colors.get(token, default_color) if color_by_token else default_color
        
        # Draw semi-transparent filled rectangle
        draw.rectangle(rect, fill=(*color, 80), outline=(*color, 200), width=3)
        
        # Draw label
        if show_labels and font:
            label_bg = [x, y - 20, x + w, y]
            draw.rectangle(label_bg, fill=(*color, 180))
            draw.text((x + 2, y - 18), token, fill=(255, 255, 255), font=font)

    # Add legend if requested
    if show_legend and color_by_token and token_colors:
        add_legend(draw, token_colors, font, img.size)

    composite = Image.alpha_composite(img, overlay)
    out_p = out_dir / f'overlay_{folio}.png'
    composite.convert('RGB').save(out_p, dpi=(150,150))
    print('Wrote overlay to', out_p)
    
    # write provenance metadata for this overlay
    try:
        meta = {
            'folio': folio,
            'image': str(img_p),
            'coords_source': str(COORDS),
            'output': str(out_p),
            'num_tokens': len(folio_coords),
            'unique_tokens': len(set(r.get('token') for r in folio_coords)),
            'color_by_token': color_by_token,
            'show_labels': show_labels,
            'show_legend': show_legend
        }
        with (out_dir / f'overlay_{folio}_metadata.json').open('w', encoding='utf-8') as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return out_p


def add_legend(draw: ImageDraw, token_colors: Dict[str, tuple], font, img_size: tuple):
    """Add a color legend to the overlay."""
    legend_x = img_size[0] - 250
    legend_y = 50
    box_size = 20
    padding = 5
    
    # Draw legend background
    legend_height = len(token_colors) * (box_size + padding) + 40
    draw.rectangle(
        [legend_x - 10, legend_y - 10, legend_x + 240, legend_y + legend_height],
        fill=(255, 255, 255, 220),
        outline=(0, 0, 0, 255),
        width=2
    )
    
    # Title
    if font:
        draw.text((legend_x, legend_y), "Token Legend:", fill=(0, 0, 0), font=font)
    
    # Draw legend items
    y_offset = legend_y + 25
    for token, color in sorted(token_colors.items()):
        # Color box
        draw.rectangle(
            [legend_x, y_offset, legend_x + box_size, y_offset + box_size],
            fill=color,
            outline=(0, 0, 0),
            width=1
        )
        # Label
        if font:
            draw.text((legend_x + box_size + 10, y_offset + 2), token, fill=(0, 0, 0), font=font)
        y_offset += box_size + padding


def generate_all_overlays(limit: int = 10, **kwargs):
    """Generate overlays for all folios with coordinates.
    
    Args:
        limit: Maximum number of overlays to generate (None for all)
        **kwargs: Additional arguments passed to overlays_for_folio
    """
    recs = load_coords()
    if not recs:
        print('No coords to generate overlays.')
        return
    folios = sorted({r.get('folio') for r in recs})
    print(f'Generating overlays for {len(folios)} folios (limit={limit})')
    count = 0
    outputs = []
    for f in folios:
        out_p = overlays_for_folio(f, recs, **kwargs)
        if out_p:
            outputs.append(out_p)
        count += 1
        if limit and count >= limit:
            break
    print(f'\nGenerated {len(outputs)} overlay images')
    return outputs


def generate_summary_report(coords: List[Dict[str, Any]], out_dir: Path = OUT):
    """Generate a summary report of overlay statistics."""
    if not coords:
        return
    
    # Statistics
    folios = defaultdict(list)
    for rec in coords:
        folios[rec.get('folio')].append(rec)
    
    report = {
        'total_tokens': len(coords),
        'unique_tokens': len(set(r.get('token') for r in coords)),
        'folios': len(folios),
        'folio_stats': {}
    }
    
    for folio, folio_coords in folios.items():
        report['folio_stats'][folio] = {
            'tokens': len(folio_coords),
            'unique_tokens': len(set(r.get('token') for r in folio_coords)),
            'lines': len(set(r.get('line_id') for r in folio_coords))
        }
    
    # Write report
    report_path = out_dir / 'overlay_summary.json'
    with report_path.open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f'\nOverlay Summary:')
    print(f'  Total tokens: {report["total_tokens"]}')
    print(f'  Unique tokens: {report["unique_tokens"]}')
    print(f'  Folios: {report["folios"]}')
    print(f'  Report saved to: {report_path}')
    
    return report


if __name__ == '__main__':
    import sys
    
    # Load coordinates
    coords = load_coords()
    if not coords:
        print('ERROR: No coordinates found. Run src/ingest/generate_token_coords.py first.')
        sys.exit(1)
    
    # Generate summary report
    generate_summary_report(coords)
    
    # Generate all overlays with enhanced visualization
    print('\n' + '='*60)
    print('Generating enhanced overlays with color-coded tokens...')
    print('='*60 + '\n')
    
    generate_all_overlays(
        limit=20, 
        color_by_token=True, 
        show_labels=True, 
        show_legend=True
    )
    
    print('\n✅ Overlay generation complete!')
    print(f'📁 Check outputs in: {OUT}')

