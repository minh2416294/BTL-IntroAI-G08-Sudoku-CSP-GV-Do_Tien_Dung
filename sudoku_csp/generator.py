"""Sinh đề Sudoku có đúng một lời giải và đếm số lời giải của một đề.

Cả hai việc đều dựa trên tìm kiếm quay lui với MAC + MRV, nên đây cũng là một ứng dụng của
chính các kỹ thuật L6: kiểm tra một cấu hình người dùng nhập có hợp lệ (0, 1 hay nhiều lời giải)
và tạo bộ đề có kiểm soát cho phần thí nghiệm.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sudoku_csp.backtracking import BacktrackingOptions, backtracking_solve
from sudoku_csp.board import CELL_COUNT, Grid, SudokuError

EMPTY_GRID: Grid = (0,) * CELL_COUNT
_COUNT_OPTIONS = BacktrackingOptions(
    var_order="mrv", inference="ac3", max_nodes=5_000_000, time_limit_s=300.0
)


@dataclass(frozen=True, slots=True)
class GeneratedPuzzle:
    puzzle: Grid
    solution: Grid
    clues: int
    seed: int


def generator_count_solutions(puzzle: Grid, limit: int = 2) -> int:
    """Số lời giải của đề, dừng khi đạt `limit` (mặc định 2: đủ để biết có duy nhất hay không)."""
    result = backtracking_solve(puzzle, _COUNT_OPTIONS, solution_limit=limit)
    if result.status == "limit":
        raise SudokuError("Hết ngân sách khi đếm lời giải, chưa kết luận được.")
    return result.solutions_found


def generator_full_grid(seed: int) -> Grid:
    """Một lưới đầy hợp lệ: quay lui trên lưới rỗng với thứ tự giá trị ngẫu nhiên theo `seed`."""
    options = BacktrackingOptions(var_order="mrv", value_order="random", inference="fc", seed=seed)
    result = backtracking_solve(EMPTY_GRID, options)
    if result.solution is None:
        raise SudokuError(f"Không sinh được lưới đầy với seed {seed}.")
    return result.solution


def generator_make_puzzle(target_clues: int, seed: int) -> GeneratedPuzzle:
    """Xóa dần các ô của một lưới đầy theo thứ tự ngẫu nhiên, giữ lại ô nào mà xóa đi sẽ làm đề
    có nhiều hơn một lời giải. Dừng khi còn `target_clues` ô cho sẵn hoặc không xóa được thêm;
    số ô thực tế đạt được nằm trong `clues` và có thể lớn hơn `target_clues`.
    """
    rng = random.Random(seed)
    solution = generator_full_grid(seed)
    grid = list(solution)
    order = list(range(CELL_COUNT))
    rng.shuffle(order)
    clues = CELL_COUNT
    for cell in order:
        if clues <= target_clues:
            break
        value, grid[cell] = grid[cell], 0
        if generator_count_solutions(tuple(grid)) == 1:
            clues -= 1
        else:
            grid[cell] = value
    return GeneratedPuzzle(puzzle=tuple(grid), solution=solution, clues=clues, seed=seed)
