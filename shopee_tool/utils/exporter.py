"""
Shopee Automation Tool - Data Exporter.
Exports scraped data to JSON and CSV.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .logger import logger

DEFAULT_EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"


def _resolve_path(filename: Optional[str], fmt: str, output_dir: Optional[Path]) -> Path:
    """Builds '<output_dir>/<filename or timestamp>.json|csv' and creates the directory."""
    directory = output_dir or DEFAULT_EXPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    name = filename or f"shopee_export_{datetime.now():%Y%m%d_%H%M%S}"
    if not name.endswith(f".{fmt}"):
        name = f"{name}.{fmt}"
    return directory / name


def export_to_json(
    data: List[Dict[str, Any]],
    filename: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Exports a list of dictionaries to a JSON file."""
    path = _resolve_path(filename, "json", output_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[green]Data successfully exported to JSON: {path}[/green]")
    return path


def export_to_csv(
    data: List[Dict[str, Any]],
    filename: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Exports a list of dictionaries to a UTF-8-BOM CSV file (opens cleanly in Excel)."""
    path = _resolve_path(filename, "csv", output_dir)

    # Union of keys across all rows, preserving first-seen order.
    fieldnames = list(dict.fromkeys(k for item in data for k in item))

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if fieldnames:
            writer.writeheader()
        for item in data:
            writer.writerow({
                k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                for k, v in item.items()
            })

    logger.info(f"[green]Data successfully exported to CSV: {path}[/green]")
    return path


def export_data(
    data: List[Dict[str, Any]],
    fmt: str = "json",
    filename: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Exports to 'json' or 'csv'."""
    fmt = fmt.lower()
    if fmt == "csv":
        return export_to_csv(data, filename, output_dir)
    if fmt == "json":
        return export_to_json(data, filename, output_dir)
    raise ValueError(f"Unsupported export format: {fmt}. Use 'csv' or 'json'.")
