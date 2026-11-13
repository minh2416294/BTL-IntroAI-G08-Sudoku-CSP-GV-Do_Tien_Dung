# Kiến trúc

Tài liệu này là bản ghi kiến trúc duy nhất của repo. Diff nào làm thay đổi một thành phần, một ranh giới
hay một bất biến dưới đây thì cập nhật luôn file này trong cùng diff đó.

## Thành phần

| Thành phần | Vai trò | Trạng thái |
|---|---|---|
| `sudoku_csp/` | Thư viện thuật toán, chỉ dùng thư viện chuẩn Python, không biết gì về web | Đã có: `board`, `csp`, `backtracking`, `local_search`, `generator`, `datasets` |
| `app/` | Backend FastAPI (`main.py`, `schemas.py`) và giao diện HTML/CSS/JS thuần trong `app/static/` | Đã có |
| `experiments/` | Sinh bộ đề, chạy benchmark, vẽ biểu đồ, gắn hình vào báo cáo | Đã có: `make_dataset`, `run_benchmark`, `plot_results`, `notebook_attach_figures` |
| `data/` | Bộ đề tự sinh và top95, được commit để thí nghiệm tái lập được | Đã có (xem `data/NGUON_DU_LIEU.md`) |
| `results/` | CSV kết quả thô, `env.json` (tham số và máy), `tables.md`, bảng tổng hợp, `figures/` | Đã có, sinh lại bằng `run_benchmark` rồi `plot_results` |

`run_benchmark` ghi số liệu thô rồi gọi `plot_results`, nên một lệnh tái lập đủ `results/`.
`plot_results` chỉ đọc CSV trong `results/`, nên có thể vẽ lại hình mà không phải chạy lại benchmark.
Đường dẫn `RESULTS_DIR` nằm trong `experiments/__init__.py` để hai module không import vòng. `notebook_attach_figures` nhúng ảnh từ `results/figures/` và
`docs/screenshots/` vào các cell markdown của báo cáo dưới dạng attachment.

`sudoku_csp/datasets.py` đọc file trong `data/` bằng đường dẫn tương đối với package, nên chỉ dùng
được khi chạy từ repo (cài kiểu editable), không dùng được khi cài package ở nơi khác.

Luồng phụ thuộc chỉ đi một chiều: `app/` và `experiments/` gọi `sudoku_csp/`, còn `sudoku_csp/` không
import ngược lại.

## Luồng minh họa

1. Trình duyệt gửi `POST /api/solve` (đề + cấu hình). `app/schemas.py` kiểm tra input; server tự đặt
   trần 200 000 nút, 200 000 bước, 10 giây và 60 000 sự kiện cho mỗi yêu cầu.
2. Solver chạy với tracer bật và trả về chuỗi sự kiện nhỏ (`assign`, `prune`, `unassign`, `backjump`,
   `swap`, ...), không gửi ảnh chụp bàn cờ ở từng bước.
3. `app/static/replay.js` dựng lại trạng thái từ chuỗi sự kiện: mỗi phép gán ghi một mốc, mỗi lần bỏ
   gán khôi phục các giá trị bị cắt sau mốc đó, đúng cơ chế trail của solver. Với mỗi sự kiện, engine
   lưu các thao tác kèm giá trị trước/sau nên tua tới hoặc lùi đều chính xác.
4. `tests/test_replay_consistency.py` chạy vết thật của solver qua engine JS (bằng Node) và kiểm tra
   trạng thái cuối trùng với lời giải, để hai phía không lệch nhau.

Thời gian hiển thị trên giao diện được đo khi có ghi vết, nên không dùng để so sánh hiệu năng; số liệu
hiệu năng lấy từ `experiments/` với tracer tắt.

## Bất biến

1. `sudoku_csp/` không import FastAPI, pandas, matplotlib hay module nào trong `app/`, `experiments/`.
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
