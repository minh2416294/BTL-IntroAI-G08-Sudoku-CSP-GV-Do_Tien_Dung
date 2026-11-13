from __future__ import annotations

import pytest

from sudoku_csp.board import board_clue_count, board_is_solution
from sudoku_csp.generator import (
    EMPTY_GRID,
    generator_count_solutions,
    generator_full_grid,
    generator_make_puzzle,
)
from tests.puzzles import WIKI_PUZZLE, WIKI_SOLUTION, puzzle_with_wrong_clue
from tests.test_backtracking import two_solution_puzzle


def test_full_grid_is_a_valid_solution_of_the_empty_grid() -> None:
    assert board_is_solution(generator_full_grid(11), EMPTY_GRID)


def test_full_grid_depends_only_on_seed() -> None:
    assert generator_full_grid(5) == generator_full_grid(5)
    assert generator_full_grid(5) != generator_full_grid(6)


@pytest.mark.parametrize(
    ("puzzle", "expected"),
    [
        (WIKI_PUZZLE, 1),
        (two_solution_puzzle(WIKI_SOLUTION), 2),
        (puzzle_with_wrong_clue(WIKI_PUZZLE, WIKI_SOLUTION), 0),
        (EMPTY_GRID, 2),
    ],
    ids=["unique", "deadly-rectangle", "wrong-clue", "empty"],
)
def test_count_solutions_stops_at_two(puzzle: tuple[int, ...], expected: int) -> None:
    assert generator_count_solutions(puzzle) == expected


@pytest.mark.parametrize("target", [30, 45])
def test_generated_puzzle_hits_target_and_has_exactly_one_solution(target: int) -> None:
    generated = generator_make_puzzle(target, seed=target)
    assert generated.clues == target == board_clue_count(generated.puzzle)
    assert generator_count_solutions(generated.puzzle) == 1
    assert board_is_solution(generated.solution, generated.puzzle)


def test_unreachable_target_reports_actual_clue_count() -> None:
    generated = generator_make_puzzle(10, seed=1)
    assert generated.clues > 16
    assert generated.clues == board_clue_count(generated.puzzle)
