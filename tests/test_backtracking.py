from __future__ import annotations

import random
from dataclasses import replace

import pytest

from sudoku_csp.backtracking import (
    Backjump,
    BacktrackingOptions,
    Inference,
    VarOrder,
    backtracking_label,
    backtracking_option_grid,
    backtracking_solve,
)
from sudoku_csp.board import ROW_OF, Grid, board_is_solution
from tests.puzzles import (
    DEAD_CELL_PUZZLE,
    WIKI_PUZZLE,
    WIKI_SOLUTION,
    puzzle_from_solution,
    puzzle_with_wrong_clue,
)

ALL_OPTIONS = backtracking_option_grid(max_nodes=300_000)
INFERENCES: tuple[Inference, ...] = ("none", "fc", "ac3")
VAR_ORDERS: tuple[VarOrder, ...] = ("static", "mrv")
WRONG_CLUE_PUZZLES = [
    puzzle_with_wrong_clue(WIKI_PUZZLE, WIKI_SOLUTION, skip) for skip in (0, 7, 50)
]


def static(inference: Inference, backjump: Backjump = "chronological") -> BacktrackingOptions:
    return BacktrackingOptions(
        var_order="static",
        value_order="static",
        inference=inference,
        backjump=backjump,
        max_nodes=300_000,
    )


def two_solution_puzzle(solution: Grid) -> Grid:
    """Xóa 4 ô tạo thành một "hình chữ nhật chết" (2 hàng, 2 cột, 2 khối, giá trị a b / b a).

    Mọi ô khác đều cho sẵn nên 4 ô chỉ nhận được {a, b}, và đổi chéo a với b vẫn hợp lệ:
    đề có đúng 2 lời giải.
    """
    for r1 in range(9):
        for r2 in range(r1 + 1, 9):
            if r1 // 3 != r2 // 3:
                continue
            for c1 in range(9):
                for c2 in range(c1 + 1, 9):
                    if c1 // 3 == c2 // 3:
                        continue
                    a, b = solution[r1 * 9 + c1], solution[r1 * 9 + c2]
                    if solution[r2 * 9 + c1] == b and solution[r2 * 9 + c2] == a:
                        blanks = {r1 * 9 + c1, r1 * 9 + c2, r2 * 9 + c1, r2 * 9 + c2}
                        keep = [cell for cell in range(81) if cell not in blanks]
                        return puzzle_from_solution(solution, keep)
    raise AssertionError("Không tìm thấy hình chữ nhật chết trong lời giải mẫu.")


def random_puzzles(count: int) -> list[Grid]:
    """Xen kẽ đề chắc chắn có nghiệm (giữ 24 ô của lời giải) và đề chắc chắn vô nghiệm."""
    rng = random.Random(2026)
    puzzles: list[Grid] = []
    for index in range(count):
        if index % 2 == 0:
            puzzles.append(puzzle_from_solution(WIKI_SOLUTION, rng.sample(range(81), 24)))
        else:
            puzzles.append(puzzle_with_wrong_clue(WIKI_PUZZLE, WIKI_SOLUTION, rng.randrange(60)))
    return puzzles


@pytest.mark.parametrize("options", ALL_OPTIONS, ids=backtracking_label)
def test_every_configuration_finds_the_unique_solution(options: BacktrackingOptions) -> None:
    result = backtracking_solve(WIKI_PUZZLE, options)
    assert result.status == "solved"
    assert result.solution == WIKI_SOLUTION


@pytest.mark.parametrize("options", ALL_OPTIONS, ids=backtracking_label)
def test_every_configuration_proves_dead_cell_puzzle_unsolvable(
    options: BacktrackingOptions,
) -> None:
    assert backtracking_solve(DEAD_CELL_PUZZLE, options).status == "unsolvable"


@pytest.mark.parametrize("options", ALL_OPTIONS, ids=backtracking_label)
@pytest.mark.parametrize("puzzle", WRONG_CLUE_PUZZLES, ids=["skip0", "skip7", "skip50"])
def test_every_configuration_proves_wrong_clue_puzzle_unsolvable(
    options: BacktrackingOptions, puzzle: Grid
) -> None:
    assert backtracking_solve(puzzle, options).status == "unsolvable"


def test_conflicting_givens_are_unsolvable_without_search() -> None:
    grid = (5,) + (0,) * 7 + (5,) + (0,) * 72
    result = backtracking_solve(grid)
    assert (result.status, result.stats.nodes) == ("unsolvable", 0)


@pytest.mark.parametrize("puzzle", [WIKI_PUZZLE, *WRONG_CLUE_PUZZLES])
def test_stronger_inference_never_visits_more_nodes(puzzle: Grid) -> None:
    """Cùng thứ tự tĩnh: cây của FC là tập con cây của BT, cây của MAC là tập con cây của FC."""
    bt, fc, mac = (backtracking_solve(puzzle, static(i)).stats.nodes for i in INFERENCES)
    assert mac <= fc <= bt


@pytest.mark.parametrize("inference", INFERENCES)
@pytest.mark.parametrize("puzzle", [WIKI_PUZZLE, *WRONG_CLUE_PUZZLES])
def test_cbj_never_visits_more_nodes_than_chronological(inference: Inference, puzzle: Grid) -> None:
    chrono = backtracking_solve(puzzle, static(inference)).stats.nodes
    cbj = backtracking_solve(puzzle, static(inference, "cbj")).stats.nodes
    assert cbj <= chrono


@pytest.mark.parametrize("inference", INFERENCES)
@pytest.mark.parametrize("var_order", VAR_ORDERS)
def test_cbj_reaches_the_same_verdict_as_chronological(
    inference: Inference, var_order: VarOrder
) -> None:
    """Một lượt mà quay lui thường chạm ngân sách thì không kết luận được gì nên bị bỏ qua,
    nhưng phải còn ít nhất 45/50 lượt có kết luận để phép so sánh có nghĩa."""
    base = BacktrackingOptions(var_order=var_order, inference=inference, max_nodes=300_000)
    decided = 0
    for puzzle in random_puzzles(50):
        chrono = backtracking_solve(puzzle, base)
        if chrono.status == "limit":
            continue
        cbj = backtracking_solve(puzzle, replace(base, backjump="cbj"))
        assert cbj.status == chrono.status
        if cbj.solution is not None:
            assert board_is_solution(cbj.solution, puzzle)
        decided += 1
    assert decided >= 45


def test_count_stops_at_one_for_unique_puzzle() -> None:
    result = backtracking_solve(WIKI_PUZZLE, BacktrackingOptions(), solution_limit=2)
    assert result.solutions_found == 1


def test_count_finds_both_solutions_of_deadly_rectangle() -> None:
    result = backtracking_solve(two_solution_puzzle(WIKI_SOLUTION), solution_limit=5)
    assert result.solutions_found == 2


def test_count_on_empty_grid_stops_at_limit() -> None:
    result = backtracking_solve((0,) * 81, solution_limit=2)
    assert result.solutions_found == 2


def test_counting_with_cbj_is_rejected() -> None:
    with pytest.raises(ValueError):
        backtracking_solve(WIKI_PUZZLE, BacktrackingOptions(backjump="cbj"), solution_limit=2)


def test_node_budget_yields_limit_not_unsolvable() -> None:
    tiny = backtracking_solve(WIKI_PUZZLE, replace(static("none"), max_nodes=5))
    assert tiny.status == "limit"


def test_solution_depth_equals_number_of_empty_cells() -> None:
    result = backtracking_solve(WIKI_PUZZLE, static("fc"))
    assert result.stats.max_depth == 81 - 30


def test_trace_is_off_by_default() -> None:
    assert backtracking_solve(WIKI_PUZZLE).events is None


def test_trace_records_every_assignment_and_ends_with_status() -> None:
    result = backtracking_solve(WIKI_PUZZLE, static("fc"), trace=True)
    assert result.events is not None
    assigns = [event for event in result.events if event["type"] == "assign"]
    assert len(assigns) == result.stats.nodes
    assert result.events[-1] == {"type": "end", "status": "solved"}


def test_random_value_order_is_reproducible_with_seed() -> None:
    options = BacktrackingOptions(value_order="random", seed=7)
    first = backtracking_solve((0,) * 81, options).solution
    second = backtracking_solve((0,) * 81, options).solution
    assert first is not None
    assert first == second
    assert [first[c] for c in range(9)] != [first[c] for c in range(81) if ROW_OF[c] == 1]


def test_labels_name_the_lecture_techniques() -> None:
    options = BacktrackingOptions(
        var_order="mrv", value_order="lcv", inference="ac3", backjump="cbj"
    )
    assert backtracking_label(options) == "MAC+MRV+LCV+CBJ"
    assert backtracking_label(static("none")) == "BT"
