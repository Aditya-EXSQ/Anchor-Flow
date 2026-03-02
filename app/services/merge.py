"""
Merge per-PDF JSON outputs into a single file per ticket.

Ported from Scripts/MergeJSON.py.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def merge_json_outputs(
    output_dir: Path = Path("Data/Output"),
    json_dir: Path = Path("Data/JSON"),
) -> list[str]:
    """
    For each subfolder in *output_dir*, merge its JSON files into one array
    and write it to ``{json_dir}/{folder_name}.json``.

    A ``_source_file`` field is injected into every entry for traceability.

    Returns the list of merged file paths.
    """
    json_dir.mkdir(parents=True, exist_ok=True)

    if not output_dir.exists():
        logger.error("Directory not found: %s", output_dir)
        return []

    merged_paths: list[str] = []

    for folder in sorted(output_dir.iterdir()):
        if not folder.is_dir():
            continue

        json_files = sorted(folder.glob("*.json"))
        if not json_files:
            continue

        merged_data: list[Any] = []

        for file_path in json_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    file_data = json.load(f)

                _tag_source(file_data, file_path.name)
                merged_data.append(file_data)

            except json.JSONDecodeError:
                logger.warning("Could not decode %s — skipping", file_path)
            except Exception:
                logger.exception("Error reading %s", file_path)

        merged_path = json_dir / f"{folder.name}.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=4)

        logger.info("Merged %d files → %s", len(json_files), merged_path)
        merged_paths.append(str(merged_path))

    return merged_paths


def _tag_source(data: Any, filename: str) -> None:
    """Inject ``_source_file`` for provenance tracking."""
    if isinstance(data, dict):
        data["_source_file"] = filename
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                item["_source_file"] = filename
