"""Đề mẫu dùng chung cho test, kèm lời giải công bố để kiểm tra độc lập với solver."""

from __future__ import annotations

from sudoku_csp.board import PEER_LISTS, Grid, board_parse

# Đề minh họa trong bài "Sudoku" trên Wikipedia tiếng Anh, có đúng một lời giải (in kèm bên dưới).
WIKI_PUZZLE = board_parse(
    "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
)
WIKI_SOLUTION = board_parse(
    "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
)

# Hàng 1 có 1..8, còn ô (1,9) cần số 9 nhưng cột 9 đã có 9 ở ô (2,9): vô nghiệm ngay từ đầu,
# dù không có hai ô cho sẵn nào trùng số.
DEAD_CELL_PUZZLE = board_parse("12345678." + "........9" + "." * 63)


def puzzle_with_wrong_clue(puzzle: Grid, solution: Grid, skip: int = 0) -> Grid:
    """Thêm một số sai vào một ô trống mà không trùng trực tiếp với ô cho sẵn nào.

    Đề gốc có đúng một lời giải, nên đề mới vô nghiệm: mọi lời giải của đề mới cũng là lời giải
    của đề gốc, tức là chính `solution`, mà `solution` lại khác số vừa thêm.
    """
    candidates: list[tuple[int, int]] = []
    for cell, value in enumerate(puzzle):
        if value:
            continue
        taken = {puzzle[peer] for peer in PEER_LISTS[cell]}
        candidates.extend(
            (cell, digit)
            for digit in range(1, 10)
            if digit != solution[cell] and digit not in taken
        )
    cell, digit = candidates[skip]
    grid = list(puzzle)
    grid[cell] = digit
    return tuple(grid)


def puzzle_from_solution(solution: Grid, keep: list[int]) -> Grid:
    """Giữ lại các ô trong `keep`, xóa phần còn lại. Đề tạo ra luôn có ít nhất một nghiệm."""
    kept = set(keep)
    return tuple(value if cell in kept else 0 for cell, value in enumerate(solution))
