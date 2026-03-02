import json
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.azure_service import analyze_document
from app.services.json_service import enrich_json
from app.services.merge import merge_json_data

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


@router.post("/merge-jsons")
async def merge_jsons(
    file1: UploadFile = File(..., description="JSON file 1 (required)"),
    file2: UploadFile | None = File(None, description="JSON file 2 (optional)"),
    file3: UploadFile | None = File(None, description="JSON file 3 (optional)"),
    file4: UploadFile | None = File(None, description="JSON file 4 (optional)"),
    file5: UploadFile | None = File(None, description="JSON file 5 (optional)"),
) -> dict:
    """
    Accept up to **5** JSON files and return a single merged list.

    Each entry is tagged with a ``_source_file`` field containing the
    original filename.

    - **file1** (required) – **file5** (optional): ``.json`` upload files
    """
    uploads = [f for f in (file1, file2, file3, file4, file5) if f is not None]

    parsed: list = []
    for upload in uploads:
        raw = await upload.read()
        try:
            parsed.append((json.loads(raw), upload.filename or "unknown.json"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in '{upload.filename}': {exc}",
            ) from exc

    merged = merge_json_data(parsed)
    return {"merged": merged, "file_count": len(uploads)}
