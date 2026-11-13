# Kiến trúc

Tài liệu này là bản ghi kiến trúc duy nhất của repo. Diff nào làm thay đổi một thành phần, một ranh giới
hay một bất biến dưới đây thì cập nhật luôn file này trong cùng diff đó.

## Thành phần

| Thành phần | Vai trò | Trạng thái |
|---|---|---|
| `sudoku_csp/` | Thư viện thuật toán, chỉ dùng thư viện chuẩn Python, không biết gì về web | Đã có: `board`, `csp`, `backtracking`, `local_search`, `generator`, `datasets` |
| `app/` | Backend FastAPI và giao diện HTML/CSS/JS thuần, gọi vào `sudoku_csp/` | Phase 3 |
| `experiments/` | Sinh bộ đề, chạy benchmark, vẽ biểu đồ, gắn hình vào báo cáo | Đã có `make_dataset`; benchmark ở Phase 4 |
| `data/` | Bộ đề tự sinh và top95, được commit để thí nghiệm tái lập được | Đã có (xem `data/NGUON_DU_LIEU.md`) |
| `results/` | Kết quả đo và biểu đồ | Phase 4 |

`sudoku_csp/datasets.py` đọc file trong `data/` bằng đường dẫn tương đối với package, nên chỉ dùng
được khi chạy từ repo (cài kiểu editable), không dùng được khi cài package ở nơi khác.

Luồng phụ thuộc chỉ đi một chiều: `app/` và `experiments/` gọi `sudoku_csp/`, còn `sudoku_csp/` không
import ngược lại.

## Bất biến

1. `sudoku_csp/` không import FastAPI, pandas, matplotlib hay bất kỳ module nào trong `app/`, `experiments/`.
2. Việc ghi vết (tracer) là tùy chọn. Benchmark chạy với tracer tắt, nên thời gian đo không bao gồm chi
   phí ghi vết.
3. Trạng thái tìm kiếm được khôi phục bằng trail (nhật ký các giá trị đã xóa), không sao chép toàn bộ
   miền giá trị ở mỗi nút.
4. Tìm kiếm hệ thống trả về `solved`, `unsolvable` hoặc `limit`. Tìm kiếm cục bộ trả về `solved` hoặc
   `not_found`. `limit` và `not_found` không bao giờ được báo là vô nghiệm.
5. Mỗi hàm thuật toán ghi rõ slide bài giảng tương ứng trong docstring.

## Lý do chọn kiến trúc

Repo trước của nhóm ghi lại snapshot toàn bộ bàn cờ ở mọi bước và sao chép toàn bộ miền giá trị ở mọi nút,
và đo thời gian ngay trong lúc ghi. Số đo khi đó phản ánh chi phí ghi log nhiều hơn chi phí của thuật toán.
Tách thư viện thuần khỏi phần web và tách tracer khỏi phép đo là để số liệu trong báo cáo đo đúng thứ cần đo.
