"""Sinh bộ đề có kiểm soát cho phần thí nghiệm và kiểm tra lại bộ đề top95.

Mỗi mức số ô cho sẵn có `--per-level` đề, mọi đề đều có đúng một lời giải. Seed cố định nên chạy
lại sẽ ra đúng bộ đề cũ.

    uv run python -m experiments.make_dataset
"""

from __future__ import annotations

import argparse
import csv
import time
from collections.abc import Sequence
from pathlib import Path

from experiments import console_use_utf8
from sudoku_csp.board import SudokuError, board_format
from sudoku_csp.datasets import GENERATED_CSV, dataset_load_top95
from sudoku_csp.generator import GeneratedPuzzle, generator_count_solutions, generator_make_puzzle

DEFAULT_LEVELS = (24, 28, 32, 36, 40, 45, 50)


def dataset_generate_level(
    clues: int, count: int, base_seed: int, max_attempts: int
) -> tuple[list[GeneratedPuzzle], int]:
    """Thử các seed liên tiếp, chỉ giữ đề đạt đúng `clues` ô. Trả (các đề, số lần thử)."""
    puzzles: list[GeneratedPuzzle] = []
    attempts = 0
    while len(puzzles) < count:
        if attempts >= max_attempts:
            raise SudokuError(f"Mức {clues} ô: chỉ được {len(puzzles)} đề sau {attempts} lần thử.")
        generated = generator_make_puzzle(clues, base_seed + attempts)
        attempts += 1
        if generated.clues == clues:
            puzzles.append(generated)
    return puzzles, attempts


def dataset_write_generated(path: Path, levels: dict[int, list[GeneratedPuzzle]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "clues", "seed", "puzzle", "solution"])
        for clues, puzzles in levels.items():
            for index, generated in enumerate(puzzles):
                writer.writerow(
                    [
                        f"g{clues:02d}_{index:02d}",
                        clues,
                        generated.seed,
                        board_format(generated.puzzle),
                        board_format(generated.solution),
                    ]
                )


def dataset_check_top95() -> None:
    puzzles = dataset_load_top95()
    started = time.perf_counter()
    non_unique = [p.puzzle_id for p in puzzles if generator_count_solutions(p.puzzle) != 1]
    elapsed = time.perf_counter() - started
    clue_counts = [p.clues for p in puzzles]
    print(
        f"top95: {len(puzzles)} đề, {min(clue_counts)}..{max(clue_counts)} ô cho sẵn, "
        f"không duy nhất: {non_unique or 'không có'} ({elapsed:.1f} s)"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels", type=int, nargs="+", default=list(DEFAULT_LEVELS))
    parser.add_argument("--per-level", type=int, default=30)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-attempts", type=int, default=2_000)
    parser.add_argument("--out", type=Path, default=GENERATED_CSV)
    parser.add_argument("--skip-top95", action="store_true")
    args = parser.parse_args(argv)
    console_use_utf8()

    levels: dict[int, list[GeneratedPuzzle]] = {}
    for clues in args.levels:
        started = time.perf_counter()
        base_seed = args.seed * 100_000 + clues * 1_000
        puzzles, attempts = dataset_generate_level(
            clues, args.per_level, base_seed, args.max_attempts
        )
        levels[clues] = puzzles
        print(
            f"mức {clues:2d} ô: {len(puzzles)} đề sau {attempts} lần thử "
            f"({time.perf_counter() - started:.1f} s)"
        )
    dataset_write_generated(args.out, levels)
    print(f"đã ghi {args.out}")
    if not args.skip_top95:
        dataset_check_top95()


if __name__ == "__main__":
    main()
