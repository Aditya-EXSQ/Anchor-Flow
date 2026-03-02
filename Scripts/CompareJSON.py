"""
compare_json.py — Visual diff of two extract.json (menu extraction) files.

Comparison hierarchy (waterfall):
  1. Section existence  (matched by section_name, case-insensitive)
  2. Section properties (section_name, section_preamble, section_type)
  3. Item existence     (matched by item name, case-insensitive)
  4. Item properties    (name, description, type, availability, sizes, text_anchors)
     └─ text_anchors → compared field-by-field, EXCLUDING bounding_box

Usage:
  python Scripts/compare_json.py <file_a.json> <file_b.json>
  python Scripts/compare_json.py <file_a.json> <file_b.json> --summary
  python Scripts/compare_json.py <file_a.json> <file_b.json> --output report.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.rule import Rule

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SECTION_COMPARE_KEYS = ["section_name", "section_preamble", "section_type"]
ITEM_COMPARE_KEYS = [
    "name",
    "description",
    "text_anchors",
    "type",
    "availability",
    "sizes",
]
TEXT_ANCHOR_EXCLUDE = {"bounding_box"}  # excluded inside each text_anchor object

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def norm(s: Any) -> str:
    """Normalise a section/item name for lookup."""
    return str(s).strip().lower() if s is not None else ""


def strip_bounding_box(anchor: dict) -> dict:
    """Return a copy of a text_anchor dict without the bounding_box field."""
    return {k: v for k, v in anchor.items() if k not in TEXT_ANCHOR_EXCLUDE}


def compare_text_anchors(anchors_a: list, anchors_b: list) -> list[str]:
    """
    Compare two text_anchor lists field-by-field (bounding_box excluded).
    Returns a list of human-readable difference strings.
    """
    diffs: list[str] = []

    map_a = {norm(a.get("anchor", "")): strip_bounding_box(a) for a in anchors_a}
    map_b = {norm(b.get("anchor", "")): strip_bounding_box(b) for b in anchors_b}

    only_a = sorted(set(map_a) - set(map_b))
    only_b = sorted(set(map_b) - set(map_a))
    common = sorted(set(map_a) & set(map_b))

    for key in only_a:
        diffs.append(f'  text_anchor removed: "{map_a[key].get("anchor", key)}"')
    for key in only_b:
        diffs.append(f'  text_anchor added:   "{map_b[key].get("anchor", key)}"')

    for key in common:
        a_anc = map_a[key]
        b_anc = map_b[key]
        for field in sorted(set(a_anc) | set(b_anc)):
            if field in TEXT_ANCHOR_EXCLUDE:
                continue
            va = a_anc.get(field)
            vb = b_anc.get(field)
            if va != vb:
                diffs.append(
                    f'  text_anchor["{a_anc.get("anchor", key)}"].{field}: '
                    f"{json.dumps(va)} → {json.dumps(vb)}"
                )

    return diffs


def compare_values(key: str, va: Any, vb: Any) -> list[str]:
    """
    Recursively compare two values for a given key.
    Returns list of diff strings; empty if identical.
    """
    if key == "text_anchors":
        # text_anchors can be a single dict OR a list of dicts
        if isinstance(va, dict):
            va = [va]
        elif not isinstance(va, list):
            va = []
        if isinstance(vb, dict):
            vb = [vb]
        elif not isinstance(vb, list):
            vb = []
        return compare_text_anchors(va, vb)

    if va == vb:
        return []

    # For nested dicts, recurse one level
    if isinstance(va, dict) and isinstance(vb, dict):
        diffs = []
        all_keys = sorted(set(va) | set(vb))
        for subkey in all_keys:
            sub_diffs = compare_values(
                f"{key}.{subkey}", va.get(subkey), vb.get(subkey)
            )
            diffs.extend(sub_diffs)
        return diffs

    # For lists (e.g. sizes), compare as JSON strings for brevity
    return [f"  {key}: {json.dumps(va)} → {json.dumps(vb)}"]


def compare_items(items_a: list, items_b: list) -> dict:
    """
    Compare two item lists. Returns a dict with keys:
      added, removed, changed (list of (item_name, [diff_str]))
    """
    map_a = {norm(i.get("name", "")): i for i in items_a}
    map_b = {norm(i.get("name", "")): i for i in items_b}

    only_a = sorted(set(map_a) - set(map_b))
    only_b = sorted(set(map_b) - set(map_a))
    common = sorted(set(map_a) & set(map_b))

    added = [map_b[k].get("name", k) for k in only_b]
    removed = [map_a[k].get("name", k) for k in only_a]
    changed = []

    for key in common:
        ia = map_a[key]
        ib = map_b[key]
        diffs = []
        for field in ITEM_COMPARE_KEYS:
            field_diffs = compare_values(field, ia.get(field), ib.get(field))
            diffs.extend(field_diffs)
        if diffs:
            changed.append((ia.get("name", key), diffs))

    return {"added": added, "removed": removed, "changed": changed}


def compare_section_props(sec_a: dict, sec_b: dict) -> list[str]:
    """Compare section-level properties (excluding menu_items)."""
    diffs = []
    for field in SECTION_COMPARE_KEYS:
        va = sec_a.get(field)
        vb = sec_b.get(field)
        if va != vb:
            diffs.append(f"  {field}: {json.dumps(va)} → {json.dumps(vb)}")
    return diffs


# ──────────────────────────────────────────────────────────────────────────────
# Rich rendering
# ──────────────────────────────────────────────────────────────────────────────


def render_section_panel(
    console: Console,
    section_name: str,
    prop_diffs: list[str],
    item_result: dict,
    status: str,  # "match" | "diff" | "only_a" | "only_b"
) -> None:
    """Render one section as a rich Panel."""

    # Panel border colour
    colour_map = {
        "match": "green",
        "diff": "yellow",
        "only_a": "red",
        "only_b": "blue",
    }
    border = colour_map.get(status, "white")

    # Build panel body
    body = Text()

    # Section existence
    if status == "only_a":
        body.append("➖ Section only in FILE A (removed)\n", style="bold red")
    elif status == "only_b":
        body.append("➕ Section only in FILE B (added)\n", style="bold blue")
    else:
        # Section properties
        if prop_diffs:
            body.append("⚠️  Section properties differ:\n", style="bold yellow")
            for d in prop_diffs:
                body.append(f"{d}\n", style="yellow")
        else:
            body.append("✅ Section properties match\n", style="green")

        # Items
        body.append("\n", style="default")

        added = item_result.get("added", [])
        removed = item_result.get("removed", [])
        changed = item_result.get("changed", [])

        if not added and not removed and not changed:
            body.append("✅ All items match\n", style="green")
        else:
            # Changed items
            for item_name, diffs in changed:
                body.append(
                    f"⚠️  {item_name}  ({len(diffs)} difference(s))\n",
                    style="bold yellow",
                )
                for d in diffs:
                    body.append(f"{d}\n", style="yellow")

            # Removed items
            for name in removed:
                body.append(f"➖ REMOVED item: {name}\n", style="bold red")

            # Added items
            for name in added:
                body.append(f"➕ ADDED item:   {name}\n", style="bold blue")

    console.print(
        Panel(
            body,
            title=f"[bold]SECTION: {section_name}[/bold]",
            border_style=border,
            padding=(0, 2),
        )
    )


def render_summary_table(console: Console, results: list[dict]) -> None:
    """Print a compact summary table."""
    table = Table(
        title="Comparison Summary",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("Section", style="bold", no_wrap=True, min_width=22)
    table.add_column("Status", justify="center", min_width=11)
    table.add_column("Prop Diffs", justify="center", min_width=10)
    table.add_column("Items Added", justify="center", style="blue", min_width=11)
    table.add_column("Items Removed", justify="center", style="red", min_width=13)
    table.add_column("Items Changed", justify="center", style="yellow", min_width=13)

    for r in results:
        status = r["status"]
        if status == "only_a":
            status_display = "[red]Removed[/red]"
        elif status == "only_b":
            status_display = "[blue]Added[/blue]"
        elif status == "diff":
            status_display = "[yellow]Different[/yellow]"
        else:
            status_display = "[green]Match[/green]"

        ir = r.get("item_result", {})
        table.add_row(
            r["section_name"],
            status_display,
            str(len(r.get("prop_diffs", []))),
            str(len(ir.get("added", []))),
            str(len(ir.get("removed", []))),
            str(len(ir.get("changed", []))),
        )

    console.print(table)


# ──────────────────────────────────────────────────────────────────────────────
# Main comparison entry
# ──────────────────────────────────────────────────────────────────────────────


def run_comparison(
    file_a: str, file_b: str, summary_only: bool, output_file: str | None
) -> None:
    data_a = load_json(file_a)
    data_b = load_json(file_b)

    # Support both a raw list of sections OR the full extract.json dict
    sections_a: list = (
        data_a.get("menu_sections", []) if isinstance(data_a, dict) else data_a
    )
    sections_b: list = (
        data_b.get("menu_sections", []) if isinstance(data_b, dict) else data_b
    )

    map_a = {norm(s.get("section_name", "")): s for s in sections_a}
    map_b = {norm(s.get("section_name", "")): s for s in sections_b}

    # Preserve original order from file_a, then append sections only in B
    ordered_a_keys = [norm(s.get("section_name", "")) for s in sections_a]
    ordered_b_keys = [norm(s.get("section_name", "")) for s in sections_b]

    results: list[dict] = []

    seen_a: set[str] = set()
    for key in ordered_a_keys:
        if key in seen_a:
            continue
        seen_a.add(key)
        sec_a = map_a[key]
        sec_name = sec_a.get("section_name", key)
        if key in map_b:
            sec_b = map_b[key]
            prop_diffs = compare_section_props(sec_a, sec_b)
            item_result = compare_items(
                sec_a.get("menu_items", []),
                sec_b.get("menu_items", []),
            )
            has_diff = bool(
                prop_diffs
                or item_result["added"]
                or item_result["removed"]
                or item_result["changed"]
            )
            results.append(
                {
                    "section_name": sec_name,
                    "status": "diff" if has_diff else "match",
                    "prop_diffs": prop_diffs,
                    "item_result": item_result,
                }
            )
        else:
            results.append(
                {
                    "section_name": sec_name,
                    "status": "only_a",
                    "prop_diffs": [],
                    "item_result": {},
                }
            )

    # Sections only in B (added)
    for key in ordered_b_keys:
        if key not in map_a:
            sec_b = map_b[key]
            results.append(
                {
                    "section_name": sec_b.get("section_name", key),
                    "status": "only_b",
                    "prop_diffs": [],
                    "item_result": {},
                }
            )

    # Determine output targets
    consoles = [Console()]
    file_console = None
    if output_file:
        file_console = Console(
            file=open(output_file, "w", encoding="utf-8"), highlight=False
        )
        consoles.append(file_console)

    for console in consoles:
        console.print()
        console.print(Rule("[bold cyan]JSON Comparison[/bold cyan]", style="cyan"))
        console.print(f"  [bold]FILE A:[/bold] {file_a}")
        console.print(f"  [bold]FILE B:[/bold] {file_b}")
        console.print()

        if summary_only:
            render_summary_table(console, results)
        else:
            for r in results:
                render_section_panel(
                    console,
                    r["section_name"],
                    r.get("prop_diffs", []),
                    r.get("item_result", {}),
                    r["status"],
                )
            console.print()
            render_summary_table(console, results)

        console.print()

    if file_console:
        file_console.file.close()
        print(f"\nReport also saved to: {output_file}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two extract.json menu files and show differences.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file_a", help="Path to the first JSON file (baseline)")
    parser.add_argument(
        "file_b", help="Path to the second JSON file (to compare against)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print only the summary table, not per-section detail",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save output to a plain-text file as well as the terminal",
    )
    args = parser.parse_args()

    run_comparison(args.file_a, args.file_b, args.summary, args.output)


if __name__ == "__main__":
    main()
