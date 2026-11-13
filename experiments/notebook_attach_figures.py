"""Nhúng ảnh vào notebook báo cáo dưới dạng attachment của cell markdown.

Cell markdown tham chiếu ảnh bằng `![...](attachment:ten_anh.png)`. Script tìm file ảnh cùng tên
trong `results/figures/` hoặc `docs/screenshots/`, mã hóa base64 và ghi vào trường `attachments`
của cell. Nhờ vậy notebook hiển thị đủ hình khi mở trên GitHub, Jupyter hay Colab mà không phụ thuộc
đường dẫn tương đối.

    uv run python -m experiments.notebook_attach_figures
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import console_use_utf8

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "Project_report_G08.ipynb"
IMAGE_DIRS = (ROOT / "results" / "figures", ROOT / "docs" / "screenshots")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
ATTACHMENT = re.compile(r"\(attachment:([^)\s]+)\)")


def notebook_find_image(name: str) -> Path:
    for directory in IMAGE_DIRS:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Không tìm thấy ảnh {name} trong {[str(d) for d in IMAGE_DIRS]}")


def notebook_attach(notebook: dict[str, Any]) -> list[str]:
    """Gắn ảnh cho mọi cell markdown có tham chiếu attachment. Trả danh sách tên ảnh đã gắn."""
    attached: list[str] = []
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        names = ATTACHMENT.findall("".join(cell.get("source", [])))
        if not names:
            cell.pop("attachments", None)
            continue
        attachments: dict[str, dict[str, str]] = {}
        for name in names:
            path = notebook_find_image(name)
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            attachments[name] = {MIME[path.suffix.lower()]: data}
            attached.append(name)
        cell["attachments"] = attachments
    return attached


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK)
    args = parser.parse_args(argv)
    console_use_utf8()
    path: Path = args.notebook
    notebook = json.loads(path.read_text(encoding="utf-8"))
    attached = notebook_attach(notebook)
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã gắn {len(attached)} ảnh vào {path.name}: {', '.join(attached) or 'không có'}")


if __name__ == "__main__":
    main()
