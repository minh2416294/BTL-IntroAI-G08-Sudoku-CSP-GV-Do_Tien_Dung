from __future__ import annotations

from sudoku_csp.board import DIGITS
from sudoku_csp.csp import SudokuCSP, Tracer
from tests.puzzles import WIKI_PUZZLE

EMPTY_CELL = 2
GIVEN_CELL = 0


def test_givens_start_with_singleton_domains() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    assert csp.domains[GIVEN_CELL] == {5}
    assert csp.domains[EMPTY_CELL] == set(DIGITS)


def test_undo_restores_domains_and_reasons_exactly() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    before = [set(domain) for domain in csp.domains]
    mark = csp.mark()
    csp.prune(EMPTY_CELL, 4, frozenset({10}), "fc")
    csp.assign(3, 6, depth=1)
    csp.undo_to(mark)
    assert csp.domains == before
    assert all(not reasons for reasons in csp.pruned_by)


def test_prune_reports_wipeout_only_on_last_value() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    results = [csp.prune(EMPTY_CELL, value, frozenset(), "ac3") for value in sorted(DIGITS)]
    assert results == [False] * 8 + [True]


def test_assign_shrinks_domain_to_the_value() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    csp.assign(EMPTY_CELL, 4, depth=1)
    assert csp.domains[EMPTY_CELL] == {4}
    assert csp.stats.nodes == 1


def test_explanation_is_union_of_prune_causes() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    csp.prune(EMPTY_CELL, 1, frozenset({10}), "fc")
    csp.prune(EMPTY_CELL, 2, frozenset({11, 12}), "ac3")
    assert csp.explanation(EMPTY_CELL) == {10, 11, 12}


def test_singleton_reason_of_given_is_empty() -> None:
    assert SudokuCSP(WIKI_PUZZLE).singleton_reason(GIVEN_CELL) == frozenset()


def test_singleton_reason_of_assigned_cell_is_itself() -> None:
    csp = SudokuCSP(WIKI_PUZZLE)
    csp.prune(EMPTY_CELL, 1, frozenset({40}), "fc")
    csp.assign(EMPTY_CELL, 4, depth=1)
    assert csp.singleton_reason(EMPTY_CELL) == frozenset({EMPTY_CELL})


def test_tracer_records_events_until_cap_then_marks_truncated() -> None:
    tracer = Tracer(max_events=2)
    csp = SudokuCSP(WIKI_PUZZLE, tracer)
    for value in (1, 2, 3):
        csp.prune(EMPTY_CELL, value, frozenset(), "fc")
    assert len(tracer.events) == 2
    assert tracer.truncated
