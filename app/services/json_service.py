"""
JSON enrichment orchestration.

Combines menu extraction data with Azure OCR output to produce
spatially enriched JSON (bounding boxes + quadrant positions).
"""

import logging
from typing import Any

from app.services.enrichment import generate_text_anchors

logger = logging.getLogger(__name__)


def enrich_json(
    existing_json: dict[str, Any],
    azure_json: Any,
) -> dict[str, Any]:
    """
    Generate text_anchor data for each menu item.

    Args:
        existing_json: Menu extraction data (``extract.json`` structure).
        azure_json: Merged Azure OCR data (list of documents or single dict).

    Returns:
        A dict mapping each item name to its generated ``text_anchors``.
    """
    azure_data: list[dict[str, Any]] = (
        azure_json if isinstance(azure_json, list) else [azure_json]
    )

    result: dict[str, Any] = {}

    for section in existing_json.get("menu_sections", []):
        for item in section.get("menu_items", []):
            item_name: str | None = item.get("name")
            if item_name:
                anchors = generate_text_anchors(item_name, azure_data)
                if anchors:
                    result[item_name] = anchors

    return result
