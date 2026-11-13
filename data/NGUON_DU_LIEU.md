# Nguồn dữ liệu

## `puzzles_generated.csv`: bộ đề tự sinh

Sinh bằng `uv run python -m experiments.make_dataset` (seed gốc 2026). Có 7 mức số ô cho sẵn
(24, 28, 32, 36, 40, 45, 50), mỗi mức 30 đề, tổng 210 đề.

Cách sinh: tạo một lưới đầy bằng quay lui với thứ tự giá trị ngẫu nhiên, rồi xóa dần các ô theo thứ tự
ngẫu nhiên; ô nào mà xóa đi làm đề có từ 2 lời giải trở lên thì được trả lại. Mọi đề trong file đều có
đúng một lời giải (đếm bằng quay lui MAC + MRV, dừng ở 2). Một lượt xóa thường dừng ở khoảng 25 ô, nên
mức 24 ô cần thử nhiều seed: lần sinh hiện tại cần 48 lần thử cho 30 đề.

Cột: `id`, `clues` (số ô cho sẵn), `seed`, `puzzle` (81 ký tự, `.` là ô trống), `solution`.

## `top95.txt`: 95 đề khó của Peter Norvig

Tải ngày 2026-11-13 từ https://www.norvig.com/top95.txt, là bộ đề khó mà Peter Norvig dùng trong bài
"Solving Every Sudoku Puzzle" (https://norvig.com/sudoku.html). Mỗi dòng là một đề 81 ký tự.

Đã kiểm tra lại bằng chính solver của repo: cả 95 đề có đúng một lời giải, số ô cho sẵn từ 17 đến 26.
