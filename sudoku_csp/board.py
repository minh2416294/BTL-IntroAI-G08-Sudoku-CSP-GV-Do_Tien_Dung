"""Mô hình CSP của Sudoku 9x9: biến, miền giá trị và đồ thị ràng buộc.

Mỗi ô là một biến, đánh chỉ số 0..80 theo hàng (ô (r, c) có chỉ số r * 9 + c).
Miền giá trị là {1..9}. Ràng buộc AllDifferent trên mỗi hàng, cột và khối 3x3 được phân
rã thành các ràng buộc nhị phân Xi != Xj giữa hai ô "láng giềng" (cùng hàng, cùng cột hoặc
cùng khối). Mỗi ô có đúng 8 + 8 + 4 = 20 láng giềng, nên đồ thị ràng buộc có
81 * 20 / 2 = 810 cạnh, tức 1620 cung có hướng.
"""

from __future__ import annotations

from typing import Final

Grid = tuple[int, ...]

CELL_COUNT: Final = 81
DIGITS: Final = frozenset(range(1, 10))

ROWS: Final = tuple(tuple(r * 9 + c for c in range(9)) for r in range(9))
COLS: Final = tuple(tuple(r * 9 + c for r in range(9)) for c in range(9))
BOXES: Final = tuple(
    tuple((3 * br + i) * 9 + 3 * bc + j for i in range(3) for j in range(3))
    for br in range(3)
    for bc in range(3)
)
UNITS: Final = ROWS + COLS + BOXES

ROW_OF: Final = tuple(cell // 9 for cell in range(CELL_COUNT))
COL_OF: Final = tuple(cell % 9 for cell in range(CELL_COUNT))
BOX_OF: Final = tuple((cell // 27) * 3 + (cell % 9) // 3 for cell in range(CELL_COUNT))

PEERS: Final = tuple(
    frozenset(other for unit in UNITS if cell in unit for other in unit) - {cell}
    for cell in range(CELL_COUNT)
)
PEER_LISTS: Final = tuple(tuple(sorted(peers)) for peers in PEERS)


class SudokuError(Exception):
    """Lỗi gốc của thư viện."""


class PuzzleFormatError(SudokuError, ValueError):
    """Chuỗi đề không đúng định dạng 81 ký tự."""


def board_parse(text: str) -> Grid:
    """Đọc đề từ chuỗi 81 ký tự: chữ số 1-9 là ô cho sẵn, '0' hoặc '.' là ô trống.

    Khoảng trắng và xuống dòng được bỏ qua để đọc được cả đề viết thành 9 dòng.
    """
    chars = [ch for ch in text if not ch.isspace()]
    if len(chars) != CELL_COUNT:
        raise PuzzleFormatError(f"Đề phải có đúng 81 ô, nhận được {len(chars)} ký tự.")
    grid: list[int] = []
    for index, ch in enumerate(chars):
        if ch in ".0":
            grid.append(0)
        elif ch in "123456789":
            grid.append(int(ch))
        else:
            raise PuzzleFormatError(f"Ký tự không hợp lệ {ch!r} ở vị trí {index}.")
    return tuple(grid)


def board_format(grid: Grid) -> str:
    """Ghi đề thành chuỗi 81 ký tự, ô trống là '.'."""
    return "".join(str(value) if value else "." for value in grid)


def board_clue_count(grid: Grid) -> int:
    return sum(1 for value in grid if value)


def board_find_conflicts(grid: Grid) -> list[tuple[int, int]]:
    """Các cặp ô láng giềng (a < b) đang mang cùng một số, tức các ràng buộc nhị phân bị vi phạm."""
    return [
        (a, b)
        for a in range(CELL_COUNT)
        if grid[a]
        for b in PEER_LISTS[a]
        if b > a and grid[b] == grid[a]
    ]


def board_is_solution(solution: Grid, puzzle: Grid) -> bool:
    """Lời giải hợp lệ: điền đủ 81 ô, không vi phạm ràng buộc nào, giữ nguyên mọi ô cho sẵn."""
    if len(solution) != CELL_COUNT or any(value not in DIGITS for value in solution):
        return False
    if any(given and given != value for given, value in zip(puzzle, solution, strict=True)):
        return False
    return not board_find_conflicts(solution)


def board_cell_name(cell: int) -> str:
    """Tên ô theo kiểu (hàng, cột), đánh số từ 1 như trong báo cáo."""
    return f"({ROW_OF[cell] + 1},{COL_OF[cell] + 1})"
