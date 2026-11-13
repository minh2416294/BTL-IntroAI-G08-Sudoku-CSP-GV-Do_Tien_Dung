from __future__ import annotations

from collections import Counter

import pytest

from sudoku_csp.board import board_clue_count, board_is_solution
from sudoku_csp.datasets import DatasetPuzzle, dataset_load_generated, dataset_load_top95
from sudoku_csp.generator import generator_count_solutions

GENERATED = dataset_load_generated()
TOP95 = dataset_load_top95()


def test_generated_set_has_thirty_puzzles_per_level() -> None:
    assert Counter(p.clues for p in GENERATED) == {
        clues: 30 for clues in (24, 28, 32, 36, 40, 45, 50)
    }


@pytest.mark.parametrize("item", GENERATED, ids=lambda p: p.puzzle_id)
def test_generated_puzzle_is_consistent_and_unique(item: DatasetPuzzle) -> None:
    assert item.solution is not None
    assert board_clue_count(item.puzzle) == item.clues
    assert board_is_solution(item.solution, item.puzzle)
    assert generator_count_solutions(item.puzzle) == 1


def test_top95_has_95_hard_puzzles() -> None:
    assert len(TOP95) == 95
    assert {p.clues for p in TOP95} <= set(range(17, 27))


@pytest.mark.parametrize("item", TOP95[:5], ids=lambda p: p.puzzle_id)
def test_first_top95_puzzles_are_unique(item: DatasetPuzzle) -> None:
    """Kiểm tra cả 95 đề mất khoảng 1 phút nên CI chỉ kiểm 5 đề; script dựng dữ liệu kiểm đủ 95."""
    assert generator_count_solutions(item.puzzle) == 1
