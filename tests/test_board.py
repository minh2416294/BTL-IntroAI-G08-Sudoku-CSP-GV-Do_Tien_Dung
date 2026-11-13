from __future__ import annotations

import pytest

from sudoku_csp.board import (
    BOXES,
    PEERS,
    UNITS,
    PuzzleFormatError,
    board_cell_name,
    board_clue_count,
    board_find_conflicts,
    board_format,
    board_is_solution,
    board_parse,
)
from tests.puzzles import WIKI_PUZZLE, WIKI_SOLUTION


class TestConstraintGraph:
    def test_every_cell_has_twenty_peers(self) -> None:
        assert {len(peers) for peers in PEERS} == {20}

    def test_peer_relation_is_symmetric(self) -> None:
        assert all(cell in PEERS[peer] for cell in range(81) for peer in PEERS[cell])

    def test_there_are_1620_directed_arcs(self) -> None:
        assert sum(len(peers) for peers in PEERS) == 1620

    def test_27_units_of_nine_cells(self) -> None:
        assert len(UNITS) == 27
        assert all(len(set(unit)) == 9 for unit in UNITS)

    def test_first_box_is_top_left_three_by_three(self) -> None:
        assert BOXES[0] == (0, 1, 2, 9, 10, 11, 18, 19, 20)


class TestParseAndFormat:
    def test_dots_and_zeros_are_empty_cells(self) -> None:
        assert board_parse("0." * 40 + "5")[:3] == (0, 0, 0)

    def test_whitespace_is_ignored(self) -> None:
        nine_lines = "\n".join(board_format(WIKI_PUZZLE)[i : i + 9] for i in range(0, 81, 9))
        assert board_parse(nine_lines) == WIKI_PUZZLE

    def test_format_round_trips(self) -> None:
        assert board_parse(board_format(WIKI_PUZZLE)) == WIKI_PUZZLE

    def test_wrong_length_is_rejected(self) -> None:
        with pytest.raises(PuzzleFormatError):
            board_parse("." * 80)

    def test_unknown_character_is_rejected(self) -> None:
        with pytest.raises(PuzzleFormatError):
            board_parse("x" + "." * 80)

    def test_wiki_puzzle_has_30_clues(self) -> None:
        assert board_clue_count(WIKI_PUZZLE) == 30


class TestValidity:
    def test_duplicate_in_a_row_is_reported_once(self) -> None:
        grid = (5,) + (0,) * 7 + (5,) + (0,) * 72
        assert board_find_conflicts(grid) == [(0, 8)]

    def test_published_solution_is_valid(self) -> None:
        assert board_is_solution(WIKI_SOLUTION, WIKI_PUZZLE)

    def test_solution_that_changes_a_clue_is_invalid(self) -> None:
        swapped = list(WIKI_SOLUTION)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        assert not board_is_solution(tuple(swapped), WIKI_PUZZLE)

    def test_incomplete_grid_is_not_a_solution(self) -> None:
        assert not board_is_solution(WIKI_PUZZLE, WIKI_PUZZLE)

    def test_cell_name_is_one_based(self) -> None:
        assert board_cell_name(80) == "(9,9)"
