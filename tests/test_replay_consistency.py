"""Vết do solver Python sinh ra, khi phát lại bằng engine JS của giao diện, phải ra đúng kết quả.

Test này chạy `node`, nên bị bỏ qua nếu máy không có Node.js.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sudoku_csp.backtracking import BacktrackingOptions, backtracking_solve
from sudoku_csp.board import Grid, board_format
from sudoku_csp.csp import TraceEvent
from sudoku_csp.local_search import min_conflicts_solve, simulated_annealing_solve
from tests.puzzles import WIKI_PUZZLE, WIKI_SOLUTION, puzzle_with_wrong_clue

NODE = shutil.which("node")
CHECKER = Path(__file__).resolve().parent / "js" / "replay_check.mjs"
pytestmark = pytest.mark.skipif(NODE is None, reason="cần Node.js để chạy engine phát lại")


def replay_in_node(tmp_path: Path, puzzle: Grid, events: list[TraceEvent]) -> dict[str, Any]:
    payload = tmp_path / "trace.json"
    payload.write_text(json.dumps({"puzzle": board_format(puzzle), "events": events}), "utf-8")
    assert NODE is not None
    completed = subprocess.run(
        [NODE, str(CHECKER), str(payload)], capture_output=True, text=True, check=True
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    "options",
    [
        BacktrackingOptions(var_order="static", inference="fc"),
        BacktrackingOptions(var_order="mrv", inference="ac3", backjump="cbj"),
        BacktrackingOptions(var_order="static", inference="none", backjump="cbj"),
    ],
    ids=["FC", "MAC+MRV+CBJ", "BT+CBJ"],
)
def test_backtracking_trace_replays_to_the_solution(
    tmp_path: Path, options: BacktrackingOptions
) -> None:
    result = backtracking_solve(WIKI_PUZZLE, options, trace=True, max_events=10**7)
    assert result.events is not None
    final = replay_in_node(tmp_path, WIKI_PUZZLE, result.events)
    assert tuple(final["values"]) == WIKI_SOLUTION
    assert final["again"] == final["values"]


def test_unsolvable_trace_replays_back_to_the_puzzle(tmp_path: Path) -> None:
    """Mọi phép gán đều bị gỡ khi đề vô nghiệm, nên bảng cuối chính là đề ban đầu."""
    puzzle = puzzle_with_wrong_clue(WIKI_PUZZLE, WIKI_SOLUTION, 7)
    options = BacktrackingOptions(var_order="mrv", inference="fc", backjump="cbj")
    result = backtracking_solve(puzzle, options, trace=True, max_events=10**7)
    assert result.status == "unsolvable"
    assert result.events is not None
    final = replay_in_node(tmp_path, puzzle, result.events)
    assert tuple(final["values"]) == puzzle


@pytest.mark.parametrize("method", ["mc_cell", "mc_box", "sa"])
def test_local_search_trace_replays_to_the_final_grid(tmp_path: Path, method: str) -> None:
    if method == "sa":
        result = simulated_annealing_solve(WIKI_PUZZLE, max_steps=3_000, seed=2, trace=True)
    else:
        representation = "cell" if method == "mc_cell" else "box"
        result = min_conflicts_solve(
            WIKI_PUZZLE, representation, max_steps=3_000, seed=2, trace=True
        )
    assert result.events is not None
    final = replay_in_node(tmp_path, WIKI_PUZZLE, result.events)
    assert tuple(final["values"]) == result.grid
