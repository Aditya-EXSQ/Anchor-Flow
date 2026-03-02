# Scripts Documentation

Standalone utility scripts for the OCR pipeline. These scripts are **not used by the FastAPI app** — they are one-off tools for local development and data preparation.

> All commands should be run from the **project root** (`/path/to/OCR/`).

---

## Table of Contents

1. [AzureTextExtraction.py](#azuretextextractionpy) — low-level Azure OCR helper
2. [ProcessPDF's.py](#processpdfspy) — batch PDF → JSON extraction
3. [MergeJSON.py](#mergejsonpy) — merge per-PDF JSONs into per-ticket archives
4. [TextAnchor.py](#textanchorpy) — enrich extract.json with text anchors & quadrants
5. [CompareJSON.py](#CompareJSONpy) — visual diff of two extract.json files

---

## AzureTextExtraction.py

**Purpose:** Low-level async helper that sends a single PDF to Azure Document Intelligence and saves the raw OCR result as JSON.

### Functions

| Function | Description |
|----------|-------------|
| `extract_text_from_pdf(endpoint, key, model_id, file_path)` | Calls Azure Document Intelligence async and returns the result as a dict |
| `save_response_to_json(response_data, output_file_path)` | Writes a dict to a JSON file asynchronously |

### Usage

The script's `main()` is hardcoded to a single PDF path for quick ad-hoc testing. Edit the `file_path` and output path directly in `main()`, then run:

```bash
python3 -m Scripts.AzureTextExtraction
```

> **Note:** Requires `AZURE_DOCUMENT_ENDPOINT` and `AZURE_DOCUMENT_KEY` in your `.env` file.

### Environment variables required

```env
AZURE_DOCUMENT_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DOCUMENT_KEY=<your-api-key>
```

### Output

A single JSON file at the path specified in `main()`, containing the full Azure `analyzeResult` payload.

---

## ProcessPDF's.py

**Purpose:** Batch-processes **all PDFs** found under `Data/Tickets/` through Azure Document Intelligence, preserving the folder structure in `Data/Output/`.

### Folder structure

```
Data/Tickets/
  29211/
    Main - Fish City Grill - Q4'25.pdf   ← input
    ...
Data/Output/
  29211/
    Main - Fish City Grill - Q4'25.json  ← output (created automatically)
    ...
```

### Usage

```bash
python3 -m Scripts.ProcessPDF's
```

> PDFs are processed **sequentially** to avoid Azure rate-limit errors (429). Change to `asyncio.gather()` if your Azure tier supports higher concurrency.

### Environment variables required

```env
AZURE_DOCUMENT_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DOCUMENT_KEY=<your-api-key>
```

### Output

One `.json` file per PDF in the matching `Data/Output/<ticket_id>/` subdirectory.

---

## MergeJSON.py

**Purpose:** Merges all per-PDF JSON files inside each `Data/Output/<ticket_id>/` folder into a single archive at `Data/JSON/<ticket_id>.json`. Adds a `_source_file` field to every entry for provenance tracking.

### Folder structure

```
Data/Output/
  29211/
    GF.json
    Kids.json
    Main.json
Data/JSON/
  29211.json    ← merged output (created automatically)
```

### Usage

```bash
python3 -m Scripts.MergeJSON
```

No arguments or environment variables required.

### Output

One `Data/JSON/<ticket_id>.json` per ticket folder, containing a JSON array of all per-PDF results with a `_source_file` field on each entry.

---

## TextAnchor.py

**Purpose:** Enriches `extract.json` menu data with spatial text anchors. For each menu item, it fuzzy-searches the merged Azure OCR data to find the best matching text block, then attaches the page number, quadrant, and bounding box.

### Functions

| Function | Description |
|----------|-------------|
| `normalize_polygon(polygon)` | Normalises polygon to flat `[x1,y1,x2,y2,x3,y3,x4,y4]` format |
| `calculate_quadrant(bounding_box, width, height)` | Returns quadrant 1–4 from a bounding box centroid |
| `generate_text_anchors(item_name, azure_data)` | Fuzzy-matches an item name against all OCR candidates and returns a text anchor dict |

### Quadrant reference

```
┌──────────────┬──────────────┐
│  1 (Top-Left)│ 2 (Top-Right)│
├──────────────┼──────────────┤
│ 3 (Bot-Left) │ 4 (Bot-Right)│
└──────────────┴──────────────┘
```

### Usage

The script's `main()` is hardcoded to ticket `29212`. To use it for a different ticket, edit the file paths at the top of `main()`, then run:

```bash
python3 -m Scripts.TextAnchor
```

### Input

| File | Description |
|------|-------------|
| `Data/Tickets/<ticket_id>/extract.json` | Menu extraction data |
| `Data/JSON/<ticket_id>.json` | Merged Azure OCR output |

### Output

`Data/Tickets/<ticket_id>/extract_enriched.json` — a copy of `extract.json` with a `new_text_anchors` field added to each menu item.

---

## CompareJSON.py

**Purpose:** Visual terminal diff of two `extract.json`-format files. Walks the comparison from broadest to finest:

```
Section existence → Section properties → Item existence → Item properties → text_anchor fields
```

> `bounding_box` (inside each `text_anchor`) is **excluded** from the comparison.

### Colour coding

| Colour | Meaning |
|--------|---------|
| 🟢 Green panel | Section and all items fully match |
| 🟡 Yellow panel | Exists in both files but has differences |
| 🔴 Red panel | Only in File A (removed) |
| 🔵 Blue panel | Only in File B (added) |

### Usage

```bash
# Full diff — per-section coloured panels + summary table
python3 Scripts/CompareJSON.py <file_a.json> <file_b.json>

# Summary table only (no per-section detail)
python3 Scripts/CompareJSON.py <file_a.json> <file_b.json> --summary

# Also save output to a plain-text file
python3 Scripts/CompareJSON.py <file_a.json> <file_b.json> --output report.txt
```

### Example commands

```bash
# Compare two identical files — expect zero differences
python3 Scripts/CompareJSON.py \
  Data/Tickets/29211/extract.json \
  Data/Tickets/29211/extract.json

# Compare two different tickets
python3 Scripts/CompareJSON.py \
  Data/Tickets/29211/extract.json \
  Data/Tickets/29212/extract.json

# Quick summary of what changed
python3 Scripts/CompareJSON.py \
  Data/Tickets/29211/extract.json \
  Data/Tickets/29212/extract.json \
  --summary
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `file_a` | ✅ | Baseline JSON file |
| `file_b` | ✅ | JSON file to compare against |
| `--summary` | ❌ | Print only the summary table |
| `--output FILE` | ❌ | Save a copy of the output to `FILE` |

### Dependencies

Uses [`rich`](https://github.com/Textualize/rich) for terminal formatting (already in `requirements.txt`).
