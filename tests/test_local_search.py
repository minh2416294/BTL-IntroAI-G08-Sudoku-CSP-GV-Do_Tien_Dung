from __future__ import annotations

import random

import pytest

from sudoku_csp.board import BOXES, DIGITS, Grid, board_is_solution
from sudoku_csp.local_search import (
    LocalSearchResult,
    Representation,
    local_conflict_pairs,
    local_rowcol_cost,
    min_conflicts_solve,
    simulated_annealing_solve,
)
from tests.puzzles import WIKI_PUZZLE, WIKI_SOLUTION, puzzle_from_solution

EASY_PUZZLE = puzzle_from_solution(WIKI_SOLUTION, random.Random(50).sample(range(81), 50))


def swapped_solution() -> Grid:
    """Lời giải mẫu với hai ô (1,1)=5 và (2,2)=7 cùng khối bị đổi chỗ.

    Tính tay: hàng 1 thừa một số 7 và thiếu 5, hàng 2 thừa 5 và thiếu 7, cột 1 thiếu 5, cột 2
    thiếu 7, nên h(box) = 4. Các cặp láng giềng trùng số: (1,1)-(1,5) và (1,1)-(6,1) cùng là 7,
    (2,2)-(2,6) và (2,2)-(4,2) cùng là 5, nên h(cell) = 4. Khối 1 vẫn là một hoán vị.
    """
    grid = list(WIKI_SOLUTION)
    grid[0], grid[10] = grid[10], grid[0]
    return tuple(grid)


def boxes_are_permutations(grid: Grid) -> bool:
    return all({grid[cell] for cell in box} == DIGITS for box in BOXES)


def test_published_solution_has_zero_cost_in_both_representations() -> None:
    assert (local_conflict_pairs(WIKI_SOLUTION), local_rowcol_cost(WIKI_SOLUTION)) == (0, 0)


def test_swap_inside_a_box_costs_four_in_both_representations() -> None:
    grid = swapped_solution()
    assert (local_conflict_pairs(grid), local_rowcol_cost(grid)) == (4, 4)


@pytest.mark.parametrize("seed", range(5))
def test_box_representation_keeps_every_box_a_permutation(seed: int) -> None:
    for result in (
        min_conflicts_solve(WIKI_PUZZLE, "box", max_steps=300, seed=seed),
        simulated_annealing_solve(WIKI_PUZZLE, max_steps=3_000, seed=seed),
    ):
        assert boxes_are_permutations(result.grid)
        pairs = zip(WIKI_PUZZLE, result.grid, strict=True)
        assert all(given in (0, value) for given, value in pairs)


def _run(method: str, puzzle: Grid, max_steps: int) -> LocalSearchResult:
    if method == "sa":
        return simulated_annealing_solve(puzzle, seed=1, max_steps=max_steps)
    representation: Representation = "cell" if method == "mc_cell" else "box"
    return min_conflicts_solve(puzzle, representation, seed=1, max_steps=max_steps)


@pytest.mark.parametrize("method", ["mc_cell", "mc_box", "sa"])
def test_each_method_solves_an_easy_puzzle(method: str) -> None:
    result = _run(method, EASY_PUZZLE, max_steps=100_000)
    assert result.status == "solved"
    assert result.final_cost == 0
    assert board_is_solution(result.grid, EASY_PUZZLE)


@pytest.mark.parametrize("method", ["mc_cell", "mc_box", "sa"])
def test_exhausted_budget_is_not_found_not_unsolvable(method: str) -> None:
    result = _run(method, WIKI_PUZZLE, max_steps=1)
    assert result.status == "not_found"
    assert result.steps == 1


def test_same_seed_gives_same_run() -> None:
    first = simulated_annealing_solve(WIKI_PUZZLE, max_steps=2_000, seed=3)
    second = simulated_annealing_solve(WIKI_PUZZLE, max_steps=2_000, seed=3)
    assert first.grid == second.grid
    assert first.cost_history == second.cost_history


def test_trace_starts_with_full_state_and_ends_with_status() -> None:
    result = min_conflicts_solve(EASY_PUZZLE, "box", seed=1, trace=True)
    assert result.events is not None
    first = result.events[0]
    assert first["type"] == "init"
    assert isinstance(first["values"], list)
    assert len(first["values"]) == 81
    assert result.events[-1] == {"type": "end", "status": "solved"}


def test_cost_history_ends_at_final_step() -> None:
    result = min_conflicts_solve(EASY_PUZZLE, "box", seed=1)
    assert result.cost_history[-1] == (result.steps, result.final_cost)
