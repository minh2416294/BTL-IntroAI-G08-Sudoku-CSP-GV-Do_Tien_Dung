from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from sudoku_csp.board import board_format
from tests.puzzles import WIKI_PUZZLE, WIKI_SOLUTION, puzzle_from_solution
from tests.test_backtracking import two_solution_puzzle

client = TestClient(app)
WIKI = board_format(WIKI_PUZZLE)


def test_solve_with_mac_returns_unique_solution_and_trace() -> None:
    response = client.post("/api/solve", json={"puzzle": WIKI})
    body = response.json()
    assert response.status_code == 200
    assert (body["status"], body["label"]) == ("solved", "MAC+MRV")
    assert body["grid"] == board_format(WIKI_SOLUTION)
    assert body["events"][-1] == {"type": "end", "status": "solved"}


def test_solve_accepts_zeros_and_nine_line_layout() -> None:
    nine_lines = "\n".join(WIKI.replace(".", "0")[i : i + 9] for i in range(0, 81, 9))
    body = client.post("/api/solve", json={"puzzle": nine_lines}).json()
    assert body["puzzle"] == WIKI


@pytest.mark.parametrize("puzzle", ["123", "x" * 81])
def test_malformed_puzzle_is_rejected_with_422(puzzle: str) -> None:
    assert client.post("/api/solve", json={"puzzle": puzzle}).status_code == 422


def test_unknown_option_value_is_rejected_with_422() -> None:
    payload = {"puzzle": WIKI, "backtracking": {"inference": "magic"}}
    assert client.post("/api/solve", json=payload).status_code == 422


def test_conflicting_givens_are_unsolvable() -> None:
    puzzle = "5" + "." * 7 + "5" + "." * 72
    assert client.post("/api/solve", json={"puzzle": puzzle}).json()["status"] == "unsolvable"


@pytest.mark.parametrize("algorithm", ["min_conflicts", "simulated_annealing"])
def test_local_search_endpoints_solve_an_easy_puzzle(algorithm: str) -> None:
    easy = board_format(puzzle_from_solution(WIKI_SOLUTION, [*range(0, 81, 2), 1, 3]))
    payload = {"puzzle": easy, "algorithm": algorithm, "local": {"max_steps": 50_000, "seed": 1}}
    body = client.post("/api/solve", json=payload).json()
    assert body["status"] == "solved"
    assert body["stats"]["final_cost"] == 0


def test_step_budget_above_server_cap_is_rejected() -> None:
    payload = {"puzzle": WIKI, "algorithm": "min_conflicts", "local": {"max_steps": 10**7}}
    assert client.post("/api/solve", json=payload).status_code == 422


def test_analyze_counts_unique_and_multiple_solutions() -> None:
    unique = client.post("/api/analyze", json={"puzzle": WIKI}).json()
    double = board_format(two_solution_puzzle(WIKI_SOLUTION))
    multiple = client.post("/api/analyze", json={"puzzle": double}).json()
    assert (unique["clues"], unique["solution_count"]) == (30, 1)
    assert multiple["solution_count"] == 2


def test_analyze_reports_conflicting_pairs() -> None:
    puzzle = "5" + "." * 7 + "5" + "." * 72
    body = client.post("/api/analyze", json={"puzzle": puzzle}).json()
    assert (body["conflicts"], body["solution_count"]) == ([[0, 8]], 0)


def test_generate_returns_unique_puzzle_with_requested_clues() -> None:
    body = client.post("/api/generate", json={"clues": 40, "seed": 7}).json()
    assert (body["clues"], body["seed"]) == (40, 7)
    assert (
        client.post("/api/analyze", json={"puzzle": body["puzzle"]}).json()["solution_count"] == 1
    )


def test_samples_start_with_wikipedia_example() -> None:
    samples = client.get("/api/samples").json()
    assert samples[0]["puzzle"] == WIKI
    assert {sample["source"] for sample in samples} == {"wikipedia", "generated", "top95"}


def test_index_page_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Sudoku" in response.text


def test_static_files_are_revalidated_but_api_is_not_marked() -> None:
    assert client.get("/styles.css").headers["cache-control"] == "no-cache"
    assert "cache-control" not in client.get("/api/samples").headers
