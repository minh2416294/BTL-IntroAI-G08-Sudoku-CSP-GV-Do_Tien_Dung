# Câu hỏi ôn vấn đáp

Bộ câu hỏi để nhóm ôn trước buổi vấn đáp. Cách dùng: tự trả lời thành tiếng bằng lời của mình, rồi
mới mở đáp án để so. Đáp án ghi kèm slide (L6, L4) và chỗ trong code để tra lại khi chưa chắc.
Giải thích chi tiết từng kỹ thuật nằm ở [THUAT_TOAN.md](THUAT_TOAN.md).

## A. Mô hình hóa

**1. Biến, miền và ràng buộc của Sudoku khi mô hình thành CSP là gì? Có bao nhiêu ràng buộc nhị phân?**

<details><summary>Đáp án</summary>

81 biến (một biến cho mỗi ô), miền {1..9}, ô cho sẵn có miền một phần tử (L6 tr.4). Mỗi hàng, cột,
khối là một ràng buộc AllDifferent trên 9 biến (L6 tr.9). Phân rã thành ràng buộc Xi != Xj thì mỗi
đơn vị cho C(9,2) = 36 cặp, 27 đơn vị cho 972 cặp. Nhưng hai ô cùng hàng và cùng khối bị đếm hai lần
(tương tự cùng cột và cùng khối): có 81 + 81 = 162 cặp như vậy. Số ràng buộc khác nhau là
972 - 162 = 810 = 81 x 20 / 2, tương ứng 1620 cung có hướng.

Code: `sudoku_csp/board.py`, test `TestConstraintGraph.test_there_are_1620_directed_arcs`.
</details>

**2. Vì sao mỗi ô có đúng 20 láng giềng?**

<details><summary>Đáp án</summary>

8 ô khác cùng hàng, 8 ô khác cùng cột, và 8 ô khác cùng khối. Trong 8 ô cùng khối có 2 ô cùng hàng
và 2 ô cùng cột đã đếm, nên khối chỉ thêm 4 ô mới. Tổng 8 + 8 + 4 = 20.
</details>

**3. Phân rã AllDifferent thành các ràng buộc != nhị phân thì mất gì?**

<details><summary>Đáp án</summary>

Mất sức suy diễn. Phù hợp cung trên X != Y chỉ xóa v khỏi X khi D(Y) = {v} (ô đơn, "naked single").
Nó không thấy được trường hợp "hidden single": trong một hàng, số 5 chỉ còn đặt được ở đúng một ô,
nên ô đó phải là 5 dù miền của nó còn nhiều giá trị. Muốn thấy điều này cần xét cả ràng buộc
AllDifferent một lúc (phù hợp cung tổng quát, GAC). Vì vậy MAC trong repo vẫn phải đoán ở một số
đề mà người chơi giải được chỉ bằng suy luận. Nhóm chọn phân rã vì L6 trình bày AC-3 cho ràng buộc
nhị phân (tr.35-39).
</details>

**4. Không gian tìm kiếm lớn cỡ nào? Vì sao không "sinh rồi thử"?**

<details><summary>Đáp án</summary>

Có d^n phép gán đầy đủ, với n là số ô trống (L6 tr.8). Đề Wikipedia có 51 ô trống, tức
9^51, khoảng 4.6 x 10^48 phép gán. Sinh rồi thử (L6 tr.12-14) phải sinh trọn từng phép gán rồi mới
kiểm tra, nên không khả thi. Quay lui kiểm tra ngay sau mỗi phép gán và cắt cả cây con khi vi phạm.
</details>

## B. Quay lui và heuristic

**5. Trong số liệu, một "nút" được đếm thế nào? "backtracks" đếm gì?**

<details><summary>Đáp án</summary>

Mỗi lần gán thử một giá trị cho một biến (`SudokuCSP.assign`) là một nút. `backtracks` tăng mỗi lần
một phép gán thử bị rút lại, dù vì suy diễn làm rỗng miền hay vì cây con thất bại
(`_BacktrackingSearch._retract`). Số nút không phụ thuộc máy nên dùng để so sánh thuật toán; thời gian
được báo kèm để thấy chi phí mỗi nút.
</details>

**6. MRV hoạt động thế nào và vì sao hiệu quả?**

<details><summary>Đáp án</summary>

Chọn ô còn ít giá trị hợp lệ nhất (L6 tr.26). Đây là nguyên lý thất bại sớm: ô còn 0 giá trị báo
nhánh hiện tại sai ngay lập tức; ô còn 1 giá trị được gán mà không phải phân nhánh. Hệ số phân nhánh
ở các tầng trên giảm mạnh, nên cây nhỏ đi nhiều bậc. Khi hòa, Degree (tr.27) chọn ô có nhiều láng
giềng chưa gán nhất; hòa nữa thì chọn ô có chỉ số nhỏ nhất để kết quả tất định.

Code: `_select_variable`.
</details>

**7. Vì sao chọn biến "khó nhất" (MRV) nhưng lại chọn giá trị "dễ nhất" (LCV)?**

<details><summary>Đáp án</summary>

Mọi biến rồi cũng phải được gán, nên gặp biến khó sớm chỉ làm lộ ngõ cụt sớm hơn, không mất gì. Còn
giá trị thì chỉ cần MỘT giá trị đúng cho mỗi biến, nên thử trước giá trị có nhiều khả năng dẫn tới
lời giải nhất, tức giá trị để lại nhiều lựa chọn nhất cho láng giềng (L6 tr.28).
</details>

**8. Khi nào LCV không giúp gì?**

<details><summary>Đáp án</summary>

Khi nhánh hiện tại là ngõ cụt, mọi giá trị đều phải thử hết nên thứ tự không đổi số nút. LCV cũng
không giúp khi cần đếm hay liệt kê mọi lời giải. Ngoài ra LCV tốn thêm chi phí: với mỗi giá trị phải
đếm số láng giềng chưa gán còn giá trị đó (`_lcv_score`).
</details>

## C. Suy diễn: Forward Checking và AC-3

**9. Forward Checking làm gì sau phép gán X = v?**

<details><summary>Đáp án</summary>

Xóa v khỏi miền của mọi láng giềng chưa gán của X. Nếu có miền rỗng thì nhánh thất bại ngay, không cần
gán tiếp (L6 tr.29-33). Lý do của mỗi giá trị bị xóa được ghi là {X}.

Code: `_forward_check`.
</details>

**10. Cho một ví dụ mà FC không phát hiện thất bại nhưng AC-3 phát hiện.**

<details><summary>Đáp án</summary>

Hai ô chưa gán A, B cùng một hàng, miền đều chỉ còn {5}. FC chỉ xét láng giềng của biến vừa gán nên
không nhìn quan hệ giữa A và B. AC-3 xét cung (A -> B): giá trị 5 của A không có hỗ trợ ở B, xóa đi,
D(A) rỗng, nhánh bị cắt trước khi gán A hay B. Đây đúng là ví dụ NT và SA cùng chỉ còn màu xanh ở
L6 tr.34.
</details>

**11. Vì sao REVISE cho ràng buộc != chỉ cần kiểm tra trường hợp miền của Y còn một giá trị?**

<details><summary>Đáp án</summary>

x thuộc D(X) có hỗ trợ ở Y khi tồn tại y thuộc D(Y) với y != x. Nếu D(Y) có từ 2 giá trị trở lên thì
luôn có một giá trị khác x, nên x luôn có hỗ trợ. Chỉ khi D(Y) = {x} thì x mất hỗ trợ. REVISE vì vậy
chạy O(1) thay vì O(d^2) như bản tổng quát ở L6 tr.36.

Code: `_revise`.
</details>

**12. Sau khi REVISE(X, Y) xóa giá trị khỏi D(X), những cung nào phải xét lại? Vì sao không cần đưa lại cung (Y -> X)?**

<details><summary>Đáp án</summary>

Mọi cung (Z -> X) với Z là láng giềng của X, Z khác Y (L6 tr.37), vì giá trị z của Z có thể vừa mất
giá trị hỗ trợ duy nhất ở X. Không cần (Y -> X): giá trị x bị xóa vì không có hỗ trợ ở Y, mà ràng
buộc đối xứng nên x cũng không hỗ trợ giá trị nào của Y. Xóa x không làm giá trị nào của Y mất hỗ trợ.

Code: vòng `for z in PEER_LISTS[x]` trong `_ac3`.
</details>

**13. Độ phức tạp của AC-3? Trên Sudoku trong code này thì sao?**

<details><summary>Đáp án</summary>

Tổng quát O(e·d^3): mỗi cung vào hàng đợi tối đa d lần (mỗi lần miền đầu kia mất một giá trị), mỗi
lần REVISE tốn O(d^2). Trong code, REVISE là O(1) nên một lần chạy AC-3 tốn O(e·d), với e = 1620 và
d = 9 là khoảng 14 580 lần REVISE trong trường hợp xấu nhất.
</details>

**14. MAC là gì? Khác gì so với chạy AC-3 một lần trước khi tìm kiếm?**

<details><summary>Đáp án</summary>

MAC (Maintaining Arc Consistency) chạy AC-3 toàn cục trước khi tìm kiếm, rồi chạy lại sau MỖI phép
gán, bắt đầu từ các cung (Z -> X) với X là biến vừa gán (L6 tr.38-39). Chạy một lần ở đầu chỉ là
tiền xử lý; MAC giữ phù hợp cung ở mọi nút nên phát hiện ngõ cụt sớm hơn FC.

Code: `_initial_propagation`, `_propagate`.
</details>

**15. Nếu MAC duyệt ít nút hơn FC, tại sao không phải lúc nào MAC cũng nhanh hơn?**

<details><summary>Đáp án</summary>

Mỗi nút của MAC đắt hơn: FC chỉ chạm 20 láng giềng, MAC lan truyền dây chuyền qua hàng đợi cung. Thời
gian = số nút x chi phí mỗi nút. Trên đề dễ, FC + MRV đã gần như không phải quay lui, nên MAC tốn thêm
chi phí lan truyền mà không bớt được nút nào. Trên đề khó, số nút của FC tăng rất nhanh còn MAC thì
không, nên MAC thắng. Hình H3 trong báo cáo đo đúng sự đánh đổi này.
</details>

## D. Conflict-Directed Backjumping

**16. Quay lui thường lùi về đâu? CBJ lùi về đâu?**

<details><summary>Đáp án</summary>

Quay lui thường (chronological) lùi về biến gán ngay trước đó. Nếu biến đó không liên quan tới mâu
thuẫn, mọi giá trị khác của nó đều dẫn lại đúng mâu thuẫn cũ (thrashing). CBJ lùi thẳng về biến
gần nhất trong tập xung đột, tức biến thực sự góp phần gây ra mâu thuẫn (L6 tr.22; Prosser 1993).
</details>

**17. Tập xung đột của một biến được xây thế nào trong code?**

<details><summary>Đáp án</summary>

Khi mọi giá trị của biến V đều thất bại, tập xung đột của V là hợp của: lý do các miền rỗng gặp
phải khi thử từng giá trị của V; tập xung đột trả về từ các tầng con; và lý do đã xóa các giá trị
khỏi D(V) từ trước (`_domain_conflict`). Bỏ chính V ra rồi trả lên tầng cha. Tầng cha U thấy U không
có trong tập thì bỏ gán và trả tiếp tập đó lên, không thử giá trị khác (`_jump_over`).
</details>

**18. Vì sao lý do phải ghi theo từng giá trị bị xóa chứ không theo từng biến?**

<details><summary>Đáp án</summary>

Các giá trị khác nhau của cùng một ô bị xóa bởi các phép gán khác nhau. Khi một miền rỗng, lý do
của mâu thuẫn là hợp các lý do của TỪNG giá trị đã mất. Khi quay lui một phần, chỉ những giá trị gắn
với phép gán bị rút mới được trả lại, nên lý do phải đi cùng giá trị để được gỡ cùng lúc qua trail.
Ghi theo biến thì hoặc mất thông tin (tập xung đột thiếu, nhảy sai), hoặc phải lấy dư (nhảy ngắn).

Code: `SudokuCSP.pruned_by`, `SudokuCSP.explanation`.
</details>

**19. Lấy dư lý do có sao không? Lấy thiếu thì sao?**

<details><summary>Đáp án</summary>

Lấy dư vẫn đúng, chỉ nhảy ngắn hơn: tệ nhất là thành quay lui thường. Lấy thiếu thì có thể nhảy qua
một biến thực ra có liên quan, bỏ sót nhánh chứa lời giải và báo sai là vô nghiệm. Vì lỗi này âm
thầm, repo có test vi sai: CBJ phải cho cùng kết luận với quay lui thường trên 50 đề (nửa có nghiệm,
nửa vô nghiệm) ở mọi tổ hợp suy diễn và thứ tự biến.

Test: `test_cbj_reaches_the_same_verdict_as_chronological`.
</details>

**20. Lý do của một giá trị bị AC-3 xóa được tính thế nào?**

<details><summary>Đáp án</summary>

AC-3 xóa v khỏi X vì D(Y) = {v}. Nếu Y đã gán thì lý do là {Y}. Nếu Y chưa gán, lý do là hợp các lý
do đã xóa 8 giá trị kia khỏi D(Y), vì chính chúng khiến D(Y) chỉ còn v. Ô cho sẵn là hằng số nên lý
do rỗng.

Code: `SudokuCSP.singleton_reason`, test `test_singleton_reason_of_given_is_empty`.
</details>

**21. Vì sao chế độ đếm lời giải không cho dùng CBJ?**

<details><summary>Đáp án</summary>

Khi đếm, sau khi gặp một lời giải ta tiếp tục tìm. Nhánh vừa tìm ra lời giải không có "mâu thuẫn"
nào, nên tập xung đột không xác định. Nếu vẫn nhảy theo tập rỗng thì sẽ bỏ qua các lời giải khác.
Muốn đếm bằng CBJ phải sửa thuật toán (coi mọi biến đã gán là lý do sau một lời giải); repo chọn
cách đơn giản là chặn tổ hợp này (`ValueError`), và bộ đếm dùng MAC + MRV quay lui thường.
</details>

**22. Khi đã có MAC, CBJ còn giúp nhiều không?**

<details><summary>Đáp án</summary>

Lý thuyết chỉ bảo đảm một điều: với cùng thứ tự tĩnh, CBJ không duyệt nhiều nút hơn quay lui thường
(Kondrak và van Beek 1997). Repo kiểm chứng điều này bằng test
(`test_cbj_never_visits_more_nodes_than_chronological`), và trong benchmark không có lượt kết luận
được nào mà CBJ tốn nhiều nút hơn. Có thể kỳ vọng suy diễn càng mạnh thì CBJ càng ít lợi, vì ngõ cụt
bị phát hiện gần chỗ gây ra nó hơn (Chen và van Beek 2001). Số liệu chỉ khớp một phần. Với thứ tự cố
định trên bộ tự sinh, tổng số nút giảm 41% với FC nhưng chỉ 7% với MAC. Còn khi có MRV, trên top95
MAC+MRV vẫn giảm 17%, nhiều hơn BT+MRV (5%).

BT được lợi ít vì tập xung đột của nó thô hơn: khi một ô hết giá trị, BT lấy mọi láng giềng đã gán
đang giữ một giá trị trong miền của ô đó. FC thì chỉ ghi láng giềng đã xóa giá trị đó trước tiên.
Tập xung đột lớn hơn thì khoảng nhảy ngắn hơn (`_domain_conflict`).
</details>

## E. Tìm kiếm cục bộ

**23. Vì sao tìm kiếm cục bộ không chứng minh được một đề vô nghiệm?**

<details><summary>Đáp án</summary>

Nó chỉ đi qua một phần nhỏ không gian trạng thái và không ghi nhớ đã đi đâu, nên không đầy đủ. Hết
ngân sách mà chưa thấy lời giải chỉ nói "chưa tìm thấy". Repo vì vậy trả `not_found`, không bao giờ
trả `unsolvable` cho local search (test `test_exhausted_budget_is_not_found_not_unsolvable`).
</details>

**24. Hàm chi phí h của hai cách biểu diễn là gì? Tính tay một ví dụ.**

<details><summary>Đáp án</summary>

"cell": h là số cặp láng giềng trùng số. "box": mỗi khối luôn là hoán vị 1..9, h là tổng số chữ số
còn thiếu trên 9 hàng và 9 cột. Ví dụ: lấy lời giải đúng rồi đổi chỗ (1,1) = 5 và (2,2) = 7. Hàng 1
thiếu 5, hàng 2 thiếu 7, cột 1 thiếu 5, cột 2 thiếu 7: h(box) = 4. Có 4 cặp láng giềng trùng số:
h(cell) = 4. Test `test_swap_inside_a_box_costs_four_in_both_representations` ghim đúng hai số này.
</details>

**25. Vì sao biểu diễn "box" thường tốt hơn "cell"?**

<details><summary>Đáp án</summary>

Ràng buộc khối luôn được thỏa nên thuật toán chỉ phải sửa hàng và cột. Không gian nhỏ hơn hẳn: thay
vì 9^n trạng thái, chỉ còn tích k! trên các khối, với k là số ô trống của khối (ví dụ một khối có 5 ô
trống chỉ có 5! = 120 cách điền thay vì 9^5 = 59 049). Đây là quyết định về cách mô hình hóa, không
phải về thuật toán.
</details>

**26. Min-Conflicts chọn bước đi thế nào? Vì sao "giữ nguyên" cũng là một lựa chọn và hòa thì chọn ngẫu nhiên?**

<details><summary>Đáp án</summary>

Chọn ngẫu nhiên một ô đang vi phạm, rồi chọn giá trị (hoặc ô cùng khối để đổi chỗ) cho h nhỏ nhất
(L6 tr.41). Cho phép giữ nguyên để không bị ép đi bước xấu khi mọi thay đổi đều làm h tăng. Hòa thì
chọn ngẫu nhiên để có thể đi ngang trên vùng bằng phẳng (plateau) thay vì lặp đi lặp lại cùng một
trạng thái.
</details>

**27. Min-Conflicts bị kẹt thì xử lý thế nào?**

<details><summary>Đáp án</summary>

Min-Conflicts là leo đồi nên có thể kẹt ở cực trị địa phương hoặc plateau (L4 tr.31). Sau 2 000
bước không cải thiện được h tốt nhất, thuật toán khởi động lại từ một trạng thái ngẫu nhiên mới
(`restart_after` trong `min_conflicts_solve`).
</details>

**28. Simulated Annealing nhận bước xấu với xác suất bao nhiêu? T ảnh hưởng thế nào?**

<details><summary>Đáp án</summary>

Bước làm h tăng delta được nhận với xác suất exp(-delta / T) (L4 tr.37-38). T lớn thì gần như bước
nào cũng nhận, thuật toán đi ngẫu nhiên để khám phá. T nhỏ thì gần như chỉ nhận bước tốt, thành leo
đồi. Ví dụ delta = 2: T = 2 cho xác suất e^-1, khoảng 0.37; T = 0.5 cho e^-4, khoảng 0.018.
</details>

**29. Lịch giảm nhiệt trong repo được chọn thế nào?**

<details><summary>Đáp án</summary>

T0 là độ lệch chuẩn của h trên 200 trạng thái lân cận ngẫu nhiên của trạng thái đầu (Lewis 2007), để
T0 tự co giãn theo đề. Sau mỗi chuỗi bước dài bằng số ô trống thì T nhân 0.99. Khi T < 0.05 mà 20
chuỗi liền không cải thiện được h tốt nhất thì nâng T về T0 (reheat).

Code: `simulated_annealing_solve`, `_initial_temperature`.
</details>

**30. Bản SA đầu tiên của nhóm sai ở đâu?**

<details><summary>Đáp án</summary>

Bản đầu nâng nhiệt sau một số bước cố định không cải thiện. Vì T còn cao nên h không giảm, nên lần
nâng nhiệt sau tới rất nhanh, và T không bao giờ xuống thấp. SA chỉ đi ngẫu nhiên quanh mức h cao và
thất bại ở mọi đề 32 và 40 ô trong lượt chạy thử. Sửa lại để chỉ nâng nhiệt khi T đã "đông cứng"
(dưới 0.05) thì SA giải được 6/6 lượt chạy thử ở 40 ô. Bài học: tính chất "giảm T đủ chậm thì tới
được tối ưu toàn cục" (L4 tr.39) chỉ có tác dụng khi T thực sự giảm.
</details>

**31. Min-Conflicts và SA khác nhau về bản chất ở đâu?**

<details><summary>Đáp án</summary>

Min-Conflicts tham lam: chọn bước tốt nhất trong lân cận của một ô đang xung đột, và thoát kẹt bằng
khởi động lại. SA chọn một bước ngẫu nhiên rồi quyết định nhận hay không theo xác suất, và thoát kẹt
bằng cách nhận bước xấu khi T còn cao. Một bước của Min-Conflicts đắt hơn (phải thử mọi lựa chọn của
một ô), một bước của SA rẻ (chỉ tính delta của một phép đổi chỗ).
</details>

## F. Sinh đề và nghiệm duy nhất

**32. Kiểm tra một đề có đúng một lời giải bằng cách nào? Vì sao dừng ở 2?**

<details><summary>Đáp án</summary>

Chạy quay lui MAC + MRV nhưng không dừng ở lời giải đầu tiên mà tìm tiếp. Chỉ cần biết có 0, đúng 1
hay từ 2 lời giải trở lên, nên thấy lời giải thứ hai là dừng. Đếm hết thì vô ích và có thể rất lâu
(lưới rỗng có khoảng 6.67 x 10^21 lời giải).

Code: `generator_count_solutions`, test `test_count_on_empty_grid_stops_at_limit`.
</details>

**33. Sinh đề có nghiệm duy nhất thế nào? Vì sao bộ dữ liệu không có đề dưới 24 ô?**

<details><summary>Đáp án</summary>

Sinh một lưới đầy ngẫu nhiên, rồi xóa từng ô theo thứ tự ngẫu nhiên; nếu xóa làm đề có từ 2 lời giải
thì trả ô đó lại. Kết quả luôn có đúng một lời giải. Quá trình dừng khi đạt số ô mục tiêu hoặc khi
không ô nào xóa thêm được mà vẫn giữ nghiệm duy nhất. Với mục tiêu 24 ô, 30 trong 48 lần sinh đạt
mục tiêu; 18 lần còn lại kẹt ở 25 ô trở lên. Mục tiêu càng thấp thì tỷ lệ này càng giảm, và xuống tới
17 ô (giới hạn đã được chứng minh, McGuire và cộng sự 2012) cần tìm kiếm có chủ đích chứ không xóa
ngẫu nhiên được. Đề khó hơn lấy từ bộ top95 (17 đến 26 ô).
</details>

**34. Đề trong test có đúng 2 lời giải được dựng thế nào?**

<details><summary>Đáp án</summary>

Dùng "hình chữ nhật chết": bốn ô ở hai hàng, hai cột và nằm trong đúng hai khối, mang hai số a, b
xếp chéo nhau. Xóa bốn ô đó khỏi một lời giải thì đổi chỗ a và b vẫn cho một lời giải hợp lệ, nên đề
có đúng 2 lời giải. Con số 2 suy ra từ lý thuyết, không lấy từ output của code.

Test: `test_count_finds_both_solutions_of_deadly_rectangle`.
</details>

## G. Thí nghiệm, cài đặt và giao diện

**35. Vì sao benchmark luôn tắt ghi vết?**

<details><summary>Đáp án</summary>

Ghi vết (tạo sự kiện cho giao diện) tốn thời gian và bộ nhớ không liên quan tới thuật toán. Bản cũ
của nhóm `deepcopy` cả bàn cờ ở mỗi sự kiện và bật `tracemalloc` suốt, nên thời gian đo được chủ yếu
là chi phí ghi vết. Repo tách tracer thành tham số tùy chọn; benchmark chạy với tracer tắt, giao diện
thì ghi rõ thời gian hiển thị là "đo khi có ghi vết, không dùng để so hiệu năng".
</details>

**36. Vì sao dùng trail thay vì sao chép miền ở mỗi nút?**

<details><summary>Đáp án</summary>

Sao chép tốn 81 x 9 giá trị ở mỗi nút dù chỉ vài giá trị thay đổi. Trail ghi lại đúng các giá trị
vừa bị xóa; quay lui chỉ pop trail về mốc đã đánh dấu trước phép gán, chi phí tỷ lệ với số thay đổi
thật. Test `test_undo_restores_domains_and_reasons_exactly` kiểm tra miền và lý do được trả về đúng
như trước.
</details>

**37. Trạng thái `limit` khác `unsolvable` thế nào trong bảng kết quả?**

<details><summary>Đáp án</summary>

`unsolvable` là đã duyệt hết cây, chứng minh vô nghiệm. `limit` là hết ngân sách (số nút hoặc thời
gian) khi chưa kết luận. Bảng báo tỷ lệ đề được kết luận riêng, và khi quá nửa số lượt chạm ngân sách
thì trung vị số nút chỉ là cận dưới và được đánh dấu như vậy, không bao giờ tính như đã giải.
</details>

**38. Làm sao nhóm biết code đúng, chứ không chỉ "chạy được"?**

<details><summary>Đáp án</summary>

Giá trị mong đợi trong test lấy từ lý thuyết hoặc tính tay, không lấy từ output của code:

- lời giải công bố của đề Wikipedia;
- đề "ô chết" (hàng 1 có 1..8, ô còn lại cần 9 nhưng cột đã có 9) phải vô nghiệm ở cả 24 cấu hình;
- một đề có nghiệm duy nhất thêm một số sai (không trùng trực tiếp) chắc chắn vô nghiệm;
- bất đẳng thức số nút MAC <= FC <= BT và CBJ <= quay lui thường với thứ tự tĩnh (Kondrak và van
  Beek 1997);
- chi phí 4/4 tính tay ở câu 24;
- test so khớp giữa Python và JavaScript: phát lại vết của solver trong `replay.js` phải ra đúng bảng
  cuối.
</details>

**39. Giao diện dựng lại miền giá trị ở từng bước bằng cách nào?**

<details><summary>Đáp án</summary>

Server chỉ gửi danh sách sự kiện (assign, prune, wipeout, backjump, swap...), không gửi ảnh chụp bàn
cờ ở mỗi bước. `app/static/replay.js` áp từng sự kiện lên trạng thái của nó, ghi các thay đổi vào một
ngăn xếp giống trail nên tua lùi được. Test `tests/test_replay_consistency.py` cho Node phát lại vết
thật của solver và so với bàn cờ cuối của Python.
</details>

## Tài liệu tham khảo thêm

- X. Chen, P. van Beek (2001). Conflict-directed backjumping revisited. *Journal of Artificial
  Intelligence Research* 14.
- Các tài liệu khác: xem cuối [THUAT_TOAN.md](THUAT_TOAN.md).
