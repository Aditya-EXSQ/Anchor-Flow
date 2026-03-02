"""
Quadrant calculation and text-anchor generation.

Ported from Scripts/TweakedCalculateQuadrant.py — refactored for clarity.
"""

import difflib
from typing import Any


# ── Polygon helpers ─────────────────────────────────────────────────────────


def normalize_polygon(polygon: list) -> list[float]:
    """Normalize a polygon to a flat ``[x1, y1, x2, y2, …, x4, y4]`` list."""
    if len(polygon) == 8 and isinstance(polygon[0], (int, float)):
        return polygon
    if len(polygon) == 4 and isinstance(polygon[0], dict):
        coords: list[float] = []
        for pt in polygon:
            coords.extend([pt.get("x", 0), pt.get("y", 0)])
        return coords
    return polygon


def calculate_quadrant(bounding_box: list, width: float, height: float) -> int:
    """
    Return the quadrant (1-4) of a bounding-box centroid on a page.

    Quadrant map::

        1 (Top-Left)  │  2 (Top-Right)
        ──────────────┼───────────────
        3 (Bot-Left)  │  4 (Bot-Right)
    """
    normalized = normalize_polygon(bounding_box)
    xs = normalized[0::2]
    ys = normalized[1::2]

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    if cx < width / 2.0:
        return 1 if cy < height / 2.0 else 3
    return 2 if cy < height / 2.0 else 4


# ── Text-anchor generation ─────────────────────────────────────────────────


def generate_text_anchors(
    item_name: str,
    azure_data: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Search Azure OCR data for the best match to *item_name* and return
    anchor metadata (bounding box, quadrant, page index).

    Returns ``None`` when no match scores ≥ 0.6.
    """
    if not item_name:
        return None

    query = item_name.strip().lower()

    best_ratio: float = 0.0
    best_match: dict[str, Any] | None = None

    for doc in azure_data:
        doc_name = _source_pdf_name(doc)

        for content, polygon, page_number in _collect_candidates(doc):
            if not content or not polygon or not page_number:
                continue

            ratio = _match_ratio(query, content.strip().lower())

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = {
                    "content": content,
                    "polygon": polygon,
                    "page_number": page_number,
                    "doc_name": doc_name,
                    "doc": doc,
                }

            if best_ratio == 1.0:
                break

        if best_ratio == 1.0:
            break

    if not best_match or best_ratio < 0.6:
        return None

    return _build_anchor(best_match)


# ── Private helpers ─────────────────────────────────────────────────────────


def _source_pdf_name(doc: dict[str, Any]) -> str:
    """Derive the original PDF filename from the ``_source_file`` field."""
    source = doc.get("_source_file", "")
    return source.replace(".json", ".pdf") if source.endswith(".json") else source


def _collect_candidates(
    doc: dict[str, Any],
) -> list[tuple[str, list | None, int | None]]:
    """Extract (text, polygon, page_number) tuples from paragraphs and lines."""
    candidates: list[tuple[str, list | None, int | None]] = []

    for para in doc.get("paragraphs", []):
        for region in para.get("bounding_regions", []):
            candidates.append(
                (
                    para.get("content", ""),
                    region.get("polygon"),
                    region.get("pageNumber"),
                )
            )

    for page in doc.get("pages", []):
        page_num = page.get("page_number")
        for line in page.get("lines", []):
            candidates.append((line.get("content", ""), line.get("polygon"), page_num))

    return candidates


def _match_ratio(query: str, candidate: str) -> float:
    """Score how well *candidate* matches *query* (0.0 – 1.0)."""
    if candidate == query:
        return 1.0
    if query in candidate:
        return 0.9 + (len(query) / max(len(candidate), 1)) * 0.1
    return difflib.SequenceMatcher(None, query, candidate).ratio()


def _build_anchor(match: dict[str, Any]) -> dict[str, Any]:
    """Construct the anchor dict from a resolved match."""
    doc = match["doc"]
    page_number = match["page_number"]
    polygon = match["polygon"]

    width = height = None
    for page in doc.get("pages", []):
        if page.get("page_number") == page_number:
            width = page.get("width")
            height = page.get("height")
            break

    quadrant = None
    if width is not None and height is not None and polygon:
        quadrant = calculate_quadrant(polygon, width, height)

    return {
        "anchor": match["content"],
        "page_index": page_number,
        "quadrant": quadrant,
        "bounding_box": normalize_polygon(polygon),
        "meta_page_idx": {
            "page_index": page_number,
            "document": match["doc_name"],
        },
    }
