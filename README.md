# Sudoku CSP: giải, sinh đề và minh họa thuật toán thỏa mãn ràng buộc

Bài tập lớn môn Nhập môn Trí tuệ nhân tạo (IT3160), lớp TTNT-162297, nhóm G08.
Giảng viên: Đỗ Tiến Dũng.

Đề tài: mô hình hóa Sudoku 9x9 thành bài toán thỏa mãn ràng buộc (CSP), cài đặt các kỹ thuật trong bài
giảng L6 (quay lui, MRV/Degree, LCV, Forward Checking, AC-3/MAC, Conflict-Directed Backjumping, tìm kiếm
cục bộ Min-Conflicts) cùng Simulated Annealing của bài giảng L4, sinh đề có nghiệm duy nhất, minh họa
từng bước trên giao diện web và đo đạc, so sánh các kỹ thuật trên bộ đề có kiểm soát.

## Thành viên

| Họ tên | MSSV |
|---|---|
| Nguyễn Thái An | 202416110 |
| Trần Bình Minh | 202416294 |
| Nguyễn Thanh Hải | 202416192 |
| Bùi Hoàng Tú | 202416378 |

## Trạng thái

Repo đang được xây dựng theo từng phase. Hiện mới có bộ khung (cấu hình, CI, báo cáo). Các phần solver,
giao diện và thí nghiệm sẽ được bổ sung lần lượt, kèm hướng dẫn chạy ở mục dưới.

## Chạy thử

Cần Python 3.11 trở lên. Cách khuyến nghị dùng [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras
uv run python -m pytest
```

Nếu chưa có uv, dùng pip trong một môi trường ảo:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[analysis,dev]"
python -m pytest
```

Các lệnh đều gọi qua `python -m` vì trên Windows bật Smart App Control, các file `pytest.exe`, `ruff.exe`
trong `.venv` có thể bị chặn chạy trực tiếp.

## Tài liệu

- [Báo cáo project](Project_report_G08.ipynb)
- [Kiến trúc](docs/KIEN_TRUC.md)
