import json
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.azure_service import analyze_document
from app.services.json_service import enrich_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """
    Upload a PDF document, send it to Azure Document Intelligence,
    and return the ``analyzeResult`` JSON.
    """
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    pdf_bytes: bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await analyze_document(pdf_bytes)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Azure analysis failed")
        raise HTTPException(
            status_code=500, detail=f"Azure analysis error: {exc}"
        ) from exc

    return result


@router.post("/process-json")
async def process_json(
    existing_json: UploadFile = File(
        ..., description="Menu extraction JSON (extract.json)"
    ),
    azure_json: UploadFile = File(..., description="Merged Azure OCR JSON"),
) -> dict:
    """
    Accept two JSON files via multipart/form-data and return enriched JSON.

    - **existing_json**: menu extraction data (``extract.json`` structure)
    - **azure_json**: merged Azure OCR output
    """
    try:
        existing_data = json.loads(await existing_json.read())
        azure_data = json.loads(await azure_json.read())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    try:
        enriched = enrich_json(existing_data, azure_data)
    except Exception as exc:
        logger.exception("JSON enrichment failed")
        raise HTTPException(status_code=500, detail=f"Enrichment error: {exc}") from exc

    return enriched
