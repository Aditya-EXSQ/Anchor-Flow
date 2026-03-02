# OCR Service

A FastAPI service that extracts text from PDF documents using **Azure Document Intelligence** and enriches structured menu data with spatial bounding-box and quadrant information.

---

## Features

- **PDF → OCR** — Upload any PDF and receive the full Azure `analyzeResult` JSON back in one call.
- **JSON Enrichment** — Pass menu extraction data alongside Azure OCR output to automatically locate each menu item on the page and tag it with a bounding box and quadrant position.
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
    ├── merge.py              # Merges per-PDF JSONs into per-ticket archives
    ├── enrichment.py         # Quadrant + bounding-box calculation
    └── json_service.py       # Enrichment orchestration (used by the API)

Scripts/                      # Original standalone scripts (not used by the API)
├── AzureTextExtraction.py
├── ProcessPDF's.py
├── MergeJSON.py
├── CalculateQuadrant.py
└── TweakedCalculateQuadrant.py

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
| `GET`  | `/health` | Health check |

### `POST /api/upload-document`

**Input:** `multipart/form-data` with a `file` field (PDF).

**Flow:**
1. Receives PDF bytes (not saved to disk).
2. POSTs to Azure Document Intelligence (`prebuilt-layout` model).
3. Polls the operation until `succeeded` (2 s interval, 120 s timeout).
4. Returns `analyzeResult`.

### `POST /api/process-json`

**Input JSON:**
```json
{
  "existing_json": { "menu_sections": [ ... ] },
  "azure_json": [ ... ]
}
```

**Flow:**
1. For each menu item `name`, fuzzy-searches the Azure OCR data for the best matching text block.
2. Computes the page quadrant (Top-Left=1, Top-Right=2, Bottom-Left=3, Bottom-Right=4) from the bounding box centroid.
3. Returns the enriched JSON with `text_anchors` populated on each item.

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
