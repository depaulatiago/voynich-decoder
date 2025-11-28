# `token_coords.jsonl` format

`src/visualization/overlay.py` expects a JSONL file at `data/processed/token_coords.jsonl` containing one JSON object per line with the following fields:

- `token` (string): the normalized token text (e.g., `daiin`).
- `folio` (string): folio identifier matching the image filename (e.g., `f001r` or `folio_001`). The overlay script searches `data/external/images/` for filenames containing this folio string.
- `bbox` (array): bounding box `[x, y, w, h]` in image pixel coordinates where `x,y` is the top-left corner and `w,h` are width and height.
- `line_id` (int or string): optional identifier of the source line in the processed JSONL.
- `token_index` (int): optional 1-based token index within the line.

Example JSONL record:

```json
{"token": "daiin", "folio": "f001r", "bbox": [120, 340, 45, 12], "line_id": 123, "token_index": 4}
```

Notes:

- Coordinates must match the resolution of the images placed in `data/external/images/`.
- The overlay tool will draw rectangles and token labels using these coords. If `bbox` is missing for a record the token will be skipped.
- Generating `token_coords.jsonl` typically requires a layout/OCR step or manual annotation. Keep the file in `data/processed/` and do not commit large files to the repo; add them to `.gitignore` if needed.
