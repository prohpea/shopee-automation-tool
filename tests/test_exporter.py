"""
Unit tests for data exporter (JSON & CSV).
"""

import json
from pathlib import Path
from shopee_tool.utils.exporter import export_data, export_to_json, export_to_csv


def test_export_to_json(tmp_path: Path):
    sample_data = [
        {"item_id": 1001, "name": "Áo thun nam", "price": 120000},
        {"item_id": 1002, "name": "Quần jean", "price": 250000},
    ]
    file_path = export_to_json(sample_data, filename="test_items", output_dir=tmp_path)
    assert file_path.exists()
    assert file_path.suffix == ".json"

    with open(file_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert loaded[0]["name"] == "Áo thun nam"


def test_export_to_csv(tmp_path: Path):
    sample_data = [
        {"item_id": 1001, "name": "Áo thun nam", "tags": ["cotton", "nam"]},
        {"item_id": 1002, "name": "Quần jean", "tags": ["denim"]},
    ]
    file_path = export_to_csv(sample_data, filename="test_items", output_dir=tmp_path)
    assert file_path.exists()
    assert file_path.suffix == ".csv"

    content = file_path.read_text(encoding="utf-8-sig")
    assert "Áo thun nam" in content
    assert "item_id" in content


def test_export_data_dispatch(tmp_path: Path):
    sample = [{"test": 123}]
    p1 = export_data(sample, fmt="json", filename="disp_json", output_dir=tmp_path)
    p2 = export_data(sample, fmt="csv", filename="disp_csv", output_dir=tmp_path)
    assert p1.suffix == ".json"
    assert p2.suffix == ".csv"


def test_export_empty_data(tmp_path: Path):
    p = export_to_csv([], filename="empty", output_dir=tmp_path)
    assert p.exists()
