"""
Batch PDF processing — send every PDF under a directory to Azure OCR.

Ported from Scripts/ProcessPDF's.py.
"""

import logging
from pathlib import Path

from app.services.extraction import extract_text_from_pdf, save_response_to_json

logger = logging.getLogger(__name__)


async def process_single_pdf(
    pdf_path: Path,
    output_base_dir: Path,
    tickets_dir: Path = Path("Data/Tickets"),
) -> bool:
    """
    Run OCR on *pdf_path* and save the JSON result, mirroring the ticket
    folder structure under *output_base_dir*.

    Returns ``True`` on success, ``False`` on failure.
    """
    try:
        relative_path = pdf_path.relative_to(tickets_dir)
    except ValueError:
        logger.warning("Skipping %s — not inside %s", pdf_path, tickets_dir)
        return False

    output_path = output_base_dir / relative_path.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Processing: %s → %s", pdf_path, output_path)

    try:
        response = await extract_text_from_pdf(str(pdf_path))
        await save_response_to_json(response, str(output_path))
        logger.info("✅ %s", pdf_path.name)
        return True
    except Exception:
        logger.exception("❌ %s", pdf_path.name)
        return False


async def process_all_pdfs(
    tickets_dir: Path = Path("Data/Tickets"),
    output_dir: Path = Path("Data/Output"),
) -> int:
    """
    Process every PDF under *tickets_dir* sequentially (avoids Azure rate
    limits) and return the number of files successfully processed.
    """
    if not tickets_dir.is_dir():
        logger.error("Directory does not exist: %s", tickets_dir)
        return 0

    pdf_files = sorted(tickets_dir.rglob("*.pdf"))
    if not pdf_files:
        logger.info("No PDF files found in %s", tickets_dir)
        return 0

    logger.info("Found %d PDF file(s) — starting batch …", len(pdf_files))

    successes = 0
    for pdf_path in pdf_files:
        if await process_single_pdf(pdf_path, output_dir, tickets_dir):
            successes += 1

    logger.info("Batch complete: %d/%d succeeded", successes, len(pdf_files))
    return successes
