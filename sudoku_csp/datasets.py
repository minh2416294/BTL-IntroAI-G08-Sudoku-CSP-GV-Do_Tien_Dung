"""Đọc các bộ đề trong thư mục `data/` của repo."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sudoku_csp.board import Grid, board_clue_count, board_parse

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GENERATED_CSV = DATA_DIR / "puzzles_generated.csv"
TOP95_TXT = DATA_DIR / "top95.txt"


@dataclass(frozen=True, slots=True)
class DatasetPuzzle:
    puzzle_id: str
    source: str
    clues: int
    puzzle: Grid
    solution: Grid | None


def dataset_load_generated(path: Path = GENERATED_CSV) -> list[DatasetPuzzle]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            DatasetPuzzle(
                puzzle_id=row["id"],
                source="generated",
                clues=int(row["clues"]),
                puzzle=board_parse(row["puzzle"]),
                solution=board_parse(row["solution"]),
            )
            for row in csv.DictReader(handle)
        ]


def dataset_load_top95(path: Path = TOP95_TXT) -> list[DatasetPuzzle]:
    lines = path.read_text(encoding="utf-8").split()
    puzzles: list[DatasetPuzzle] = []
    for index, line in enumerate(lines, start=1):
        puzzle = board_parse(line)
        puzzles.append(
            DatasetPuzzle(
                puzzle_id=f"top95_{index:02d}",
                source="top95",
                clues=board_clue_count(puzzle),
                puzzle=puzzle,
                solution=None,
            )
        )
    return puzzles
