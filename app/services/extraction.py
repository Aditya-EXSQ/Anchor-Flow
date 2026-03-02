"""
Azure Form Recognizer SDK-based text extraction.

Ported from Scripts/AzureTextExtraction.py.
"""

import json

import aiofiles
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from app.core.config import settings


async def extract_text_from_pdf(
    file_path: str,
    model_id: str = "prebuilt-document",
) -> dict:
    """
    Read a PDF and extract text + bounding boxes via Azure Form Recognizer.

    Args:
        file_path: Path to the input PDF file.
        model_id: Azure model to use (e.g. ``"prebuilt-document"``).

    Returns:
        JSON-serializable dict of the full OCR result.
    """
    client = DocumentAnalysisClient(
        endpoint=settings.AZURE_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_KEY),
    )
    async with client:
        async with aiofiles.open(file_path, "rb") as f:
            data = await f.read()

        poller = await client.begin_analyze_document(
            model_id=model_id,
            document=data,
        )
        result = await poller.result()

    return result.to_dict()


async def save_response_to_json(
    response_data: dict,
    output_path: str,
) -> None:
    """Persist OCR response data as a formatted JSON file."""
    async with aiofiles.open(output_path, "w") as f:
        await f.write(json.dumps(response_data, indent=4, default=str))
