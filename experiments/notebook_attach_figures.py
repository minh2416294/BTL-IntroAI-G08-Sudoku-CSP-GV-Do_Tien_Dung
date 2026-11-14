"""Nhúng ảnh vào notebook báo cáo để hiện được trên GitHub, Colab và Jupyter không cần mạng.

Mỗi hình nằm trong một cell markdown riêng, có metadata `figure` (tên file ảnh) và `alt` (chú
thích ngắn). Script tìm file ảnh cùng tên trong `results/figures/` hoặc `docs/screenshots/`, rồi
ghi lại nội dung cell thành `![alt](data:image/...;base64,...)`. Không dùng attachment của cell vì
Colab không hiển thị attachment. Chạy lại bất cứ lúc nào sau khi vẽ lại hình:

    uv run python -m experiments.notebook_attach_figures
"""

from __future__ import annotations

import argparse
import base64
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import console_use_utf8

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "Project_report_G08.ipynb"
IMAGE_DIRS = (ROOT / "results" / "figures", ROOT / "docs" / "screenshots")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def notebook_find_image(name: str) -> Path:
    for directory in IMAGE_DIRS:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Không tìm thấy ảnh {name} trong {[str(d) for d in IMAGE_DIRS]}")


def notebook_embed(notebook: dict[str, Any]) -> list[str]:
    """Điền lại mọi cell hình bằng ảnh hiện tại dạng data URI. Trả danh sách tên ảnh đã nhúng."""
    embedded: list[str] = []
    for cell in notebook["cells"]:
        name = cell.get("metadata", {}).get("figure")
        if cell.get("cell_type") != "markdown" or not name:
            continue
        path = notebook_find_image(name)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        alt = cell["metadata"].get("alt", name)
        cell["source"] = [f"![{alt}](data:{MIME[path.suffix.lower()]};base64,{data})"]
        cell.pop("attachments", None)
        embedded.append(name)
    return embedded


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK)
    args = parser.parse_args(argv)
    console_use_utf8()
    path: Path = args.notebook
    notebook = json.loads(path.read_text(encoding="utf-8"))
    embedded = notebook_embed(notebook)
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã nhúng {len(embedded)} ảnh vào {path.name}: {', '.join(embedded) or 'không có'}")


if __name__ == "__main__":
    main()
