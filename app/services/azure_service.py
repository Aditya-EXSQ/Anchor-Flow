import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ANALYZE_URL = (
    "{endpoint}/formrecognizer/documentModels/prebuilt-layout"
    ":analyze?api-version=2023-07-31"
)

POLL_INTERVAL_SECONDS: float = 2.0
MAX_POLL_TIMEOUT_SECONDS: float = 120.0
MAX_RETRIES: int = 3


async def analyze_document(pdf_bytes: bytes) -> dict:
    """
    Submit a PDF to Azure Document Intelligence, poll until completion,
    and return the ``analyzeResult`` dictionary.

    Raises:
        httpx.HTTPStatusError: on non-2xx responses from Azure.
        TimeoutError: if polling exceeds the configured timeout.
        RuntimeError: if the Azure analysis reports a failure status.
    """
    url = ANALYZE_URL.format(endpoint=settings.AZURE_ENDPOINT.rstrip("/"))

    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_KEY,
        "Content-Type": "application/pdf",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # ---------- Submit the document ----------
        response = await client.post(url, headers=headers, content=pdf_bytes)
        response.raise_for_status()

        operation_url: str = response.headers["operation-location"]
        logger.info("Azure operation started: %s", operation_url)

        # ---------- Poll for result ----------
        poll_headers = {"Ocp-Apim-Subscription-Key": settings.AZURE_KEY}
        elapsed: float = 0.0
        retries: int = 0

        while elapsed < MAX_POLL_TIMEOUT_SECONDS:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

            try:
                poll_response = await client.get(operation_url, headers=poll_headers)
                poll_response.raise_for_status()
                retries = 0  # reset on success
            except httpx.HTTPStatusError:
                retries += 1
                logger.warning(
                    "Poll attempt failed (retry %d/%d)", retries, MAX_RETRIES
                )
                if retries >= MAX_RETRIES:
                    raise
                continue

            result: dict = poll_response.json()
            status: str = result.get("status", "")

            if status == "succeeded":
                logger.info("Azure analysis succeeded after %.1fs", elapsed)
                return result["analyzeResult"]

            if status == "failed":
                raise RuntimeError(f"Azure analysis failed: {result}")

            logger.debug("Azure status: %s (%.1fs elapsed)", status, elapsed)

        raise TimeoutError(f"Azure polling timed out after {MAX_POLL_TIMEOUT_SECONDS}s")
