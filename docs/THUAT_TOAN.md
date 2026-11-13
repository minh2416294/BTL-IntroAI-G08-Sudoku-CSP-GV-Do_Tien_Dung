# Giải thích thuật toán

Tài liệu này giải thích từng kỹ thuật trong repo theo đúng thứ tự của bài giảng L6 (Thỏa mãn ràng
buộc) và L4 (Tìm kiếm cục bộ), kèm chỗ cài đặt trong code và test kiểm chứng. Số trang ghi theo bản
PDF của môn học (ví dụ "L6 tr.39" là slide 39 của bài L6).

## 1. Sudoku là một CSP (L6 tr.4-9)

Một CSP gồm tập biến X, miền giá trị D của mỗi biến và tập ràng buộc C (L6 tr.4).

- **Biến:** 81 ô, đánh số 0..80 theo hàng (ô hàng r, cột c có chỉ số 9r + c).
- **Miền:** {1, ..., 9} cho ô trống; ô cho sẵn có miền một phần tử.
- **Ràng buộc:** mỗi hàng, cột và khối 3x3 là một ràng buộc AllDifferent 9 biến (ràng buộc bậc cao,
  L6 tr.9). Ta phân rã nó thành các ràng buộc nhị phân Xi != Xj giữa mọi cặp ô cùng đơn vị. Hai ô là
  "láng giềng" khi cùng hàng, cùng cột hoặc cùng khối.

Mỗi ô có 8 láng giềng cùng hàng, 8 cùng cột và 4 cùng khối mà chưa đếm ở trên, tổng 20. Đồ thị ràng
buộc (L6 tr.7) vì vậy có 81 đỉnh, 81 x 20 / 2 = 810 cạnh, tức 1620 cung có hướng khi xét phù hợp cung.

Không gian các phép gán đầy đủ có kích thước d^n (L6 tr.8). Đề minh họa trên Wikipedia có 51 ô trống,
tức 9^51, khoảng 4.6 x 10^48 phép gán: "sinh rồi thử" (L6 tr.12-14) là bất khả thi.

Code: `sudoku_csp/board.py` (`PEERS`, `UNITS`, `board_find_conflicts`). Test:
`tests/test_board.py::TestConstraintGraph`.

## 2. Tìm kiếm quay lui (L6 tr.15-17)

Quay lui là tìm kiếm theo chiều sâu, mỗi tầng gán một biến và kiểm tra ràng buộc ngay sau phép gán
thay vì chờ gán đủ mọi biến (L6 tr.15). Repo dùng **một khung duy nhất**, các kỹ thuật cải tiến chỉ là
các điểm cắm vào khung đó:

```text
function SEARCH(depth):
    var <- SELECT-VARIABLE()                   # thứ tự cố định hoặc MRV + Degree
    if var = rỗng: return THÀNH CÔNG           # mọi ô đã được gán
    for value in ORDER-VALUES(var):            # tăng dần hoặc LCV
        mark <- vị trí hiện tại của trail
        gán var = value
        if INFERENCE(var) không làm miền nào rỗng:     # không có, FC hoặc AC-3
            if SEARCH(depth + 1) = THÀNH CÔNG: return THÀNH CÔNG
        khôi phục trail về mark, bỏ gán var    # quay lui
    return THẤT BẠI
```

Code: `_BacktrackingSearch._search` trong `sudoku_csp/backtracking.py`.

**Trail thay cho sao chép.** Mỗi lần một giá trị bị xóa khỏi miền, `SudokuCSP` ghi cặp (ô, giá trị)
vào trail. Quay lui chỉ cần pop trail về mốc đã ghi trước phép gán. Chi phí khôi phục tỷ lệ với số
giá trị thực sự bị xóa ở nhánh đó, thay vì sao chép cả 81 miền (81 x 9 giá trị) ở mỗi nút như bản
trước của nhóm. Bộ nhớ thêm vào cũng chỉ O(n·d) cho cả cây.

**Ba trạng thái kết thúc.** `solved` (tìm thấy lời giải), `unsolvable` (đã duyệt hết, chứng minh vô
nghiệm) và `limit` (hết ngân sách số nút hoặc thời gian, chưa kết luận). `limit` không bao giờ được
báo là vô nghiệm.

## 3. Chọn biến: MRV và Degree (L6 tr.26-27)

**MRV** (Minimum Remaining Values) chọn ô có ít giá trị hợp lệ nhất. Đây là nguyên lý "thất bại sớm":
nếu một ô chỉ còn 0 giá trị thì nhánh hiện tại chắc chắn sai, và chọn nó ngay sẽ cắt nhánh sớm nhất;
nếu còn 1 giá trị thì gán nó không tốn lựa chọn nào. Khi hòa, **Degree** chọn ô có nhiều láng giềng
chưa gán nhất (ô "ràng buộc các biến khác nhiều nhất", tr.27); hòa tiếp thì chọn ô có chỉ số nhỏ hơn
để kết quả tất định.

Khi không có suy diễn, "giá trị hợp lệ" được tính bằng cách loại các số mà láng giềng đã gán đang
dùng; khi có FC hoặc AC-3 thì miền đã được thu hẹp sẵn.

Code: `_select_variable`, `_legal_values`.

## 4. Chọn giá trị: LCV (L6 tr.28)

**LCV** (Least Constraining Value) thử trước giá trị làm mất ít lựa chọn nhất của các láng giềng
chưa gán: với mỗi giá trị v của ô đang xét, đếm số láng giềng chưa gán còn v trong miền, sắp tăng
dần. Ý tưởng là giữ cho các biến sau nhiều đường đi nhất, nên có ích khi chỉ cần MỘT lời giải. Nếu
nhánh hiện tại là ngõ cụt thì mọi giá trị đều phải thử, khi đó LCV không giảm số nút mà chỉ tốn thêm
chi phí sắp xếp.

Code: `_order_values`, `_lcv_score`.

## 5. Forward Checking (L6 tr.29-33)

Ngay sau khi gán X = v, FC xóa v khỏi miền của mọi láng giềng chưa gán của X. Nếu một miền trở thành
rỗng thì nhánh này chắc chắn thất bại và được cắt ngay, không cần gán thêm biến nào. FC chỉ nhìn các
láng giềng trực tiếp của biến vừa gán, nên không phát hiện được mâu thuẫn giữa hai biến chưa gán (ví
dụ NT và SA cùng chỉ còn màu xanh ở L6 tr.34).

Trước khi tìm kiếm, FC cũng được chạy từ mọi ô cho sẵn để thu hẹp miền ban đầu.

Code: `_forward_check`. Lý do của mỗi giá trị bị xóa là `{X}` (dùng cho CBJ, mục 7).

## 6. Phù hợp cung, AC-3 và MAC (L6 tr.34-39)

Cung (X -> Y) **phù hợp** khi mọi giá trị x trong D(X) đều có một y trong D(Y) thỏa ràng buộc (tr.35).
`REVISE(X, Y)` xóa khỏi D(X) những x không có "giá trị hỗ trợ" nào ở Y (tr.36). Sau khi D(X) bị thu
hẹp, mọi cung (Z -> X) với Z khác Y phải được xét lại (tr.37). AC-3 (tr.39) duyệt một hàng đợi cung
cho tới khi rỗng.

**REVISE cho ràng buộc khác nhau.** Với X != Y, giá trị x của X chỉ mất hỗ trợ khi D(Y) = {x}: chỉ
cần Y còn một giá trị khác x là x đã có hỗ trợ. Vì vậy `_revise` chỉ kiểm tra trường hợp D(Y) còn đúng
một giá trị, chi phí O(1) thay vì O(d^2) của REVISE tổng quát.

**MAC** (Maintaining Arc Consistency) chạy AC-3 trên toàn bộ 1620 cung một lần trước khi tìm kiếm,
rồi sau mỗi phép gán X = v chạy lại AC-3 bắt đầu từ các cung (Z -> X) với Z là láng giềng chưa gán.
AC-3 phát hiện thất bại sớm hơn FC (tr.38) vì lan truyền dây chuyền: một ô bị thu về một giá trị lại
cắt tiếp các láng giềng của nó.

Độ phức tạp của AC-3 tổng quát là O(e·d^3) với e là số cung (Mackworth và Freuder, 1985). Cái giá phải
trả: mỗi nút của MAC đắt hơn nút của FC nhiều lần; thí nghiệm H3 đo đúng sự đánh đổi này.

Code: `_ac3`, `_revise`, `_initial_propagation`, `_propagate`.

## 7. Conflict-Directed Backjumping (L6 tr.22)

Quay lui thường luôn lùi về biến gán ngay trước đó, kể cả khi biến đó không liên quan gì tới mâu thuẫn,
nên lặp đi lặp lại cùng một lỗi (tr.22, ví dụ A > E). **Backjumping** lùi thẳng về biến thực sự gây ra
mâu thuẫn. Repo cài **CBJ** của Prosser (1993):

- Mỗi giá trị v bị xóa khỏi D(X) được ghi kèm **lý do**: tập các biến đã gán gây ra việc xóa.
  FC xóa vì gán Y thì lý do là {Y}. AC-3 xóa v khỏi X vì D(Y) = {v}: lý do là {Y} nếu Y đã gán, còn
  nếu chưa gán thì là hợp các lý do đã khiến D(Y) chỉ còn v. Ô cho sẵn là hằng số nên không bao giờ
  nằm trong tập lý do.
- `_search` trả về cặp (thành công, **tập xung đột**). Khi mọi giá trị của biến V đều thất bại, tập
  xung đột của V gồm lý do của các miền rỗng gặp phải, tập xung đột của các tầng con, và lý do đã thu
  hẹp D(V); bỏ chính V ra.
- Tầng cha U nhận tập này. Nếu U **không** nằm trong tập thì thử giá trị khác của U là vô ích (U không
  góp phần gây mâu thuẫn), nên U bỏ gán và trả tiếp tập đó lên trên: đó là bước "nhảy".

Lấy dư lý do vẫn đúng (chỉ nhảy ngắn hơn), lấy thiếu thì có thể nhảy qua lời giải. Chốt chặn là hai
test: CBJ luôn cho cùng kết luận với quay lui thường trên 50 đề (nửa có nghiệm, nửa vô nghiệm) ở cả 6
tổ hợp, và với cùng thứ tự tĩnh thì số nút của CBJ không vượt số nút của quay lui thường (Kondrak và
van Beek, 1997).

Code: `_search`, `_jump_over`, `_domain_conflict`, `SudokuCSP.pruned_by`, `SudokuCSP.singleton_reason`.

## 8. Tìm kiếm cục bộ (L6 tr.40-42, L4 tr.30-39)

Mỗi trạng thái là một phép gán **đầy đủ** cho mọi ô, kể cả khi còn vi phạm; dịch chuyển là đổi giá trị
một số ô; đích là trạng thái không còn vi phạm nào (L6 tr.40). Tìm kiếm cục bộ chỉ giữ trạng thái hiện
tại nên tốn ít bộ nhớ, nhưng **không đầy đủ**: hết ngân sách mà chưa tìm thấy thì chỉ kết luận
`not_found`, không chứng minh được vô nghiệm.

### Hai cách biểu diễn trạng thái

| | Biểu diễn "cell" (đúng L6 tr.41) | Biểu diễn "box" |
|---|---|---|
| Khởi tạo | Mỗi ô trống nhận ngẫu nhiên 1..9 | Mỗi khối được điền bằng hoán vị các số còn thiếu |
| Bước đi | Đổi giá trị một ô | Đổi chỗ hai ô không cho sẵn trong cùng khối |
| h | Số cặp láng giềng trùng số | Tổng số chữ số còn thiếu trên 9 hàng và 9 cột |
| Ràng buộc luôn thỏa | Không có | Ràng buộc khối |

Ví dụ tính tay (test `test_swap_inside_a_box_costs_four_in_both_representations`): lấy lời giải đúng,
đổi chỗ hai ô (1,1) = 5 và (2,2) = 7 của khối đầu. Hàng 1 thừa 7 thiếu 5, hàng 2 thừa 5 thiếu 7, cột 1
thiếu 5, cột 2 thiếu 7, nên h(box) = 4; có 4 cặp láng giềng trùng số nên h(cell) = 4.

Biểu diễn "box" thu nhỏ không gian tìm kiếm vì loại sẵn mọi trạng thái vi phạm ràng buộc khối. Đây là
một quyết định thiết kế về **cách mô hình hóa**, không phải về thuật toán, và thí nghiệm H4 cho thấy nó
quan trọng hơn việc chọn thuật toán.

### Min-Conflicts (L6 tr.41)

Lặp: chọn ngẫu nhiên một ô đang vi phạm ràng buộc, rồi chọn giá trị (hoặc ô cùng khối để đổi chỗ) làm
h nhỏ nhất. "Giữ nguyên" cũng là một lựa chọn; hòa thì chọn ngẫu nhiên, nên thuật toán đi ngang được
trên vùng bằng phẳng (plateau). Đây là leo đồi (L4 tr.31) nên có thể kẹt ở cực trị địa phương: sau
2 000 bước không cải thiện được h tốt nhất thì khởi động lại từ một trạng thái ngẫu nhiên.

Chỉ các cạnh nối với ô bị đổi mới thay đổi, nên h được cập nhật trong O(20) mỗi bước thay vì tính lại
cả bảng.

Code: `min_conflicts_solve`, `_CellState`, `_BoxState`.

### Simulated Annealing (L4 tr.37-39)

Mỗi bước thử đổi chỗ ngẫu nhiên hai ô trong một khối. Bước làm h giảm hoặc giữ nguyên luôn được nhận;
bước làm h tăng một lượng delta được nhận với xác suất exp(-delta / T). T bắt đầu cao (cho phép đi
xấu để thoát cực trị địa phương) và giảm dần về 0 (tr.37):

- T0 là độ lệch chuẩn của h trên 200 trạng thái lân cận ngẫu nhiên của trạng thái đầu (Lewis, 2007).
- Sau mỗi chuỗi bước dài bằng số ô trống, T nhân với alpha = 0.99.
- Khi T < 0.05 (lúc này gần như không nhận bước xấu nào, thuật toán chỉ còn là leo đồi) mà 20 chuỗi
  liền không cải thiện được h tốt nhất thì nâng T về T0 (reheat).

**Một lỗi đã gặp và cách sửa.** Bản đầu nâng nhiệt sau một số bước cố định không cải thiện. T khi đó
chưa bao giờ xuống thấp, SA chỉ đi ngẫu nhiên ở mức h cao và thất bại ở mọi đề 32 và 40 ô. Chỉ nâng
nhiệt khi đã "đông cứng" thì SA giải được 6/6 lượt ở 40 ô. Bài học: định lý "T giảm đủ chậm thì tìm
được tối ưu toàn cục" (tr.39) chỉ có ích khi T thực sự giảm.

Code: `simulated_annealing_solve`, `_initial_temperature`.

## 9. Sinh đề và kiểm tra nghiệm duy nhất

- **Đếm lời giải** (`generator_count_solutions`): chạy quay lui MAC + MRV nhưng không dừng ở lời giải
  đầu tiên; dừng khi đã thấy 2 lời giải (đủ để biết có duy nhất hay không). Dùng cho nút "Kiểm tra đề"
  trên giao diện: 0 nghiệm, đúng 1, hay từ 2 trở lên.
- **Sinh lưới đầy** (`generator_full_grid`): quay lui trên lưới rỗng với thứ tự giá trị ngẫu nhiên.
- **Sinh đề** (`generator_make_puzzle`): xóa dần các ô của lưới đầy theo thứ tự ngẫu nhiên; ô nào xóa
  đi làm đề có từ 2 lời giải trở lên thì được trả lại. Đề luôn có đúng một lời giải. Với mục tiêu
  24 ô, 30 trong 48 lần sinh đạt mục tiêu, các lần còn lại kẹt ở 25 ô trở lên. Số ô tối thiểu để
  Sudoku 9x9 có nghiệm duy nhất là 17 (McGuire, Tugemann và Civario, 2012).

Test: `tests/test_generator.py`, đặc biệt đề "hình chữ nhật chết" có đúng 2 lời giải.

## 10. Bảng tra: slide, hàm, test

| Bài giảng | Kỹ thuật | Hàm | Test chính |
|---|---|---|---|
| L6 tr.4-9 | Mô hình CSP, đồ thị ràng buộc | `board.PEERS`, `board_find_conflicts` | `test_board.py` |
| L6 tr.15-17 | Quay lui | `_BacktrackingSearch._search` | `test_every_configuration_finds_the_unique_solution` |
| L6 tr.22 | Backjumping (CBJ) | `_jump_over`, `_domain_conflict` | `test_cbj_reaches_the_same_verdict_as_chronological` |
| L6 tr.26-27 | MRV, Degree | `_select_variable` | `test_every_configuration_*` |
| L6 tr.28 | LCV | `_order_values`, `_lcv_score` | `test_every_configuration_*` |
| L6 tr.29 | Forward Checking | `_forward_check` | `test_stronger_inference_never_visits_more_nodes` |
| L6 tr.35-39 | Phù hợp cung, AC-3, MAC | `_revise`, `_ac3` | `test_stronger_inference_never_visits_more_nodes` |
| L6 tr.40-41 | Min-Conflicts | `min_conflicts_solve` | `test_local_search.py` |
| L4 tr.31 | Leo đồi, cực trị địa phương | khởi động lại trong `min_conflicts_solve` | `test_each_method_solves_an_easy_puzzle` |
| L4 tr.37-39 | Simulated Annealing | `simulated_annealing_solve` | `test_box_representation_keeps_every_box_a_permutation` |

## Tài liệu tham khảo

- Bài giảng IT3160: L6 "Tìm kiếm dựa trên thỏa mãn ràng buộc", L4 "Tìm kiếm với tri thức bổ sung".
- S. Russell, P. Norvig. *Artificial Intelligence: A Modern Approach*, chương 6 (CSP) và 4 (tìm kiếm cục bộ).
- P. Prosser (1993). Hybrid algorithms for the constraint satisfaction problem. *Computational
  Intelligence* 9(3).
- G. Kondrak, P. van Beek (1997). A theoretical evaluation of selected backtracking algorithms.
  *Artificial Intelligence* 89.
- A. Mackworth, E. Freuder (1985). The complexity of some polynomial network consistency algorithms
  for constraint satisfaction problems. *Artificial Intelligence* 25.
- R. Lewis (2007). Metaheuristics can solve sudoku puzzles. *Journal of Heuristics* 13(4).
- G. McGuire, B. Tugemann, G. Civario (2012). There is no 16-clue Sudoku. arXiv:1201.0749.
- P. Norvig. Solving Every Sudoku Puzzle. https://norvig.com/sudoku.html (nguồn bộ đề top95).
