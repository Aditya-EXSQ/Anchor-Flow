# OCR Service

A FastAPI service that extracts text from PDF documents using **Azure Document Intelligence** and enriches structured menu data with spatial bounding-box and quadrant information.

---

## Features

- **PDF → OCR** — Upload any PDF and receive the full Azure `analyzeResult` JSON back in one call.
- **JSON Enrichment** — Pass menu extraction data alongside Azure OCR output to automatically locate each menu item on the page and tag it with a bounding box and quadrant position.
- **JSON Merging** — Merge up to 5 OCR JSON files into a single flat list via a dedicated endpoint, with per-entry provenance tracking via `_source_file`.
- **Modular architecture** — Clean separation between routing, service logic, and configuration.
- **Async throughout** — Built on `asyncio`, `httpx`, and `aiofiles` for non-blocking I/O.

---

## Project Structure

```
app/
├── main.py                   # FastAPI app factory + /health endpoint
├── core/
│   └── config.py             # Pydantic settings (reads from .env)
├── routers/
│   └── ocr.py                # API routes — no business logic
└── services/
    ├── azure_service.py      # httpx-based Azure Document Intelligence client
    ├── extraction.py         # SDK-based OCR extraction + file saving
    ├── batch_processor.py    # Batch PDF → OCR for entire ticket directories
    ├── merge.py              # Merges per-PDF JSONs into per-ticket archives + API-level merge
    ├── enrichment.py         # Quadrant + bounding-box calculation
    └── json_service.py       # Enrichment orchestration (used by the API)

Scripts/                      # Original standalone scripts (not used by the API)
├── AzureTextExtraction.py
├── ProcessPDF's.py
├── MergeJSON.py
└── TextAnchor.py             # Standalone text-anchor generation + quadrant logic

Data/
├── Tickets/                  # Input PDFs, organised by ticket ID
├── Output/                   # Per-PDF OCR JSON outputs
└── JSON/                     # Merged per-ticket JSON archives
```

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/upload-document` | Upload a PDF → returns Azure `analyzeResult` JSON |
| `POST` | `/api/process-json` | Enrich menu JSON with bounding boxes and quadrants |
| `POST` | `/api/merge-jsons` | Merge up to 5 OCR JSON files into one list |
| `GET`  | `/health` | Health check |

### `POST /api/upload-document`

**Input:** `multipart/form-data` with a `file` field (PDF).

**Flow:**
1. Receives PDF bytes (not saved to disk).
2. POSTs to Azure Document Intelligence (`prebuilt-layout` model).
3. Polls the operation until `succeeded` (2 s interval, 120 s timeout).
4. Returns `analyzeResult`.

### `POST /api/process-json`

**Input:** `multipart/form-data` with two JSON file fields:

| Field | Description |
|-------|-------------|
| `existing_json` | Menu extraction data (`extract.json` structure) |
| `azure_json` | Merged Azure OCR output |

**Flow:**
1. For each menu item `name`, fuzzy-searches the Azure OCR data for the best matching text block.
2. Computes the page quadrant (Top-Left=1, Top-Right=2, Bottom-Left=3, Bottom-Right=4) from the bounding box centroid.
3. Returns a flat mapping of item names to their `text_anchors`:

```json
{
  "Margherita Pizza": {
    "anchor": "Margherita Pizza",
    "page_index": 1,
    "quadrant": 2,
    "bounding_box": [x1, y1, x2, y2, x3, y3, x4, y4],
    "meta_page_idx": { "page_index": 1, "document": "menu_p1.pdf" }
  },
  ...
}
```

### `POST /api/merge-jsons`

**Input:** `multipart/form-data` with up to 5 JSON file fields (`file1` … `file5`). Only `file1` is required.

**Flow:**
1. Parses each uploaded JSON file.
2. Tags every entry with a `_source_file` field containing the original filename.
3. Returns a merged list and the number of files processed.

**Response:**
```json
{
  "merged": [ ... ],
  "file_count": 3
}
```

---

## Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Python 3.11+

### 1. Clone & install

```bash
git clone <repo-url>
cd OCR
uv pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
AZURE_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_KEY=<your-api-key>
```

### 3. Run the server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Interactive API docs available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## Quadrant Reference

```
┌────────────────┬────────────────┐
│   1 (Top-Left) │  2 (Top-Right) │
├────────────────┼────────────────┤
│  3 (Bot-Left)  │  4 (Bot-Right) │
└────────────────┴────────────────┘
```

Quadrant is determined by the centroid of the matched text's bounding box relative to the page dimensions returned by Azure.
