"""Các script thí nghiệm: sinh bộ đề, chạy benchmark, vẽ biểu đồ, gắn hình vào báo cáo."""

from __future__ import annotations

import io
import sys


def console_use_utf8() -> None:
    """Console Windows mặc định dùng cp1252, không in được tiếng Việt."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
