import logging

from fastapi import FastAPI

from app.routers import ocr

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)

# ── Application ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="OCR Service",
    description="PDF text extraction via Azure Document Intelligence and JSON enrichment.",
    version="1.0.0",
)

app.include_router(ocr.router)


@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}
