"""Chạy toàn bộ thí nghiệm và ghi kết quả thô vào `results/`.

    uv run python -m experiments.run_benchmark            # đầy đủ, khoảng 20-30 phút
    uv run python -m experiments.run_benchmark --quick    # bản thu nhỏ để kiểm tra, dưới 1 phút

Chạy xong thì gọi luôn `plot_results`, nên một lệnh tái lập đủ số liệu, bảng và hình.

Thí nghiệm 1 (tìm kiếm hệ thống): đủ 24 tổ hợp kỹ thuật của L6 trên bộ đề tự sinh và top95. Mỗi lượt
giải có trần số nút; lượt chạm trần được ghi `limit`, không bao giờ tính như đã giải. Ghi vết luôn
tắt nên thời gian đo không lẫn chi phí ghi log.

Thí nghiệm 2 (tìm kiếm cục bộ): Min-Conflicts với hai cách biểu diễn và Simulated Annealing, nhiều
seed trên mỗi đề, cùng một trần số bước. Thêm đường cong chi phí theo bước trên một đề đại diện.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments import RESULTS_DIR, console_use_utf8, plot_results
from sudoku_csp.backtracking import (
    BacktrackingOptions,
    backtracking_label,
    backtracking_option_grid,
    backtracking_solve,
)
from sudoku_csp.datasets import DatasetPuzzle, dataset_load_generated, dataset_load_top95
from sudoku_csp.local_search import (
    LocalSearchResult,
    Representation,
    min_conflicts_solve,
    simulated_annealing_solve,
)

LOCAL_METHODS = ("mc_cell", "mc_box", "sa")
BACKTRACKING_FIELDS = [
    "puzzle_id",
    "source",
    "clues",
    "label",
    "inference",
    "var_order",
    "value_order",
    "backjump",
    "status",
    "nodes",
    "backtracks",
    "backjumps",
    "prunes",
    "revisions",
    "max_depth",
    "time_ms",
]
LOCAL_FIELDS = [
    "puzzle_id",
    "source",
    "clues",
    "method",
    "seed",
    "status",
    "steps",
    "restarts",
    "final_cost",
    "time_ms",
]


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    max_nodes: int
    time_limit_s: float
    reps: int
    generated_per_level: int | None
    top95_count: int
    local_per_level: int
    local_top95: int
    local_seeds: int
    local_max_steps: int
    curve_steps: int


FULL = BenchmarkConfig(
    max_nodes=50_000,
    time_limit_s=60.0,
    reps=1,
    generated_per_level=None,
    top95_count=95,
    local_per_level=10,
    local_top95=10,
    local_seeds=5,
    local_max_steps=100_000,
    curve_steps=30_000,
)
QUICK = BenchmarkConfig(
    max_nodes=5_000,
    time_limit_s=5.0,
    reps=1,
    generated_per_level=1,
    top95_count=2,
    local_per_level=1,
    local_top95=1,
    local_seeds=1,
    local_max_steps=3_000,
    curve_steps=2_000,
)


def benchmark_pick(
    generated: list[DatasetPuzzle], per_level: int | None, top95: list[DatasetPuzzle], count: int
) -> list[DatasetPuzzle]:
    """Lấy `per_level` đề đầu tiên của mỗi mức (None = tất cả) và `count` đề top95 đầu tiên."""
    if per_level is None:
        chosen = list(generated)
    else:
        taken: dict[int, int] = {}
        chosen = []
        for item in generated:
            if taken.get(item.clues, 0) < per_level:
                chosen.append(item)
                taken[item.clues] = taken.get(item.clues, 0) + 1
    return chosen + top95[:count]


def benchmark_backtracking_row(
    item: DatasetPuzzle, options: BacktrackingOptions, reps: int
) -> dict[str, Any]:
    """Giải một đề với một cấu hình. Bộ đếm là tất định nên chỉ lặp lại để lấy median thời gian,
    và chỉ lặp khi lượt đầu đã kết luận được (lượt chạm trần luôn tốn đúng bằng trần)."""
    result = backtracking_solve(item.puzzle, options)
    times = [result.stats.time_ms]
    if result.status != "limit":
        times += [backtracking_solve(item.puzzle, options).stats.time_ms for _ in range(reps - 1)]
    stats = result.stats
    return {
        "puzzle_id": item.puzzle_id,
        "source": item.source,
        "clues": item.clues,
        "label": backtracking_label(options),
        "inference": options.inference,
        "var_order": options.var_order,
        "value_order": options.value_order,
        "backjump": options.backjump,
        "status": result.status,
        "nodes": stats.nodes,
        "backtracks": stats.backtracks,
        "backjumps": stats.backjumps,
        "prunes": stats.prunes,
        "revisions": stats.revisions,
        "max_depth": stats.max_depth,
        "time_ms": round(statistics.median(times), 3),
    }


def benchmark_local_solve(
    method: str, item: DatasetPuzzle, seed: int, max_steps: int, sample_every: int = 50
) -> LocalSearchResult:
    if method == "sa":
        return simulated_annealing_solve(
            item.puzzle, max_steps=max_steps, seed=seed, time_limit_s=300, sample_every=sample_every
        )
    representation: Representation = "cell" if method == "mc_cell" else "box"
    return min_conflicts_solve(
        item.puzzle,
        representation,
        max_steps=max_steps,
        seed=seed,
        time_limit_s=300,
        sample_every=sample_every,
    )


def benchmark_run_backtracking(
    puzzles: list[DatasetPuzzle], cfg: BenchmarkConfig, path: Path
) -> int:
    grid = backtracking_option_grid(max_nodes=cfg.max_nodes, time_limit_s=cfg.time_limit_s)
    rows = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, BACKTRACKING_FIELDS, lineterminator="\n")
        writer.writeheader()
        for options in grid:
            started = time.perf_counter()
            for item in puzzles:
                writer.writerow(benchmark_backtracking_row(item, options, cfg.reps))
                rows += 1
            handle.flush()
            print(
                f"  {backtracking_label(options):16s} {len(puzzles)} đề "
                f"({time.perf_counter() - started:.1f} s)"
            )
    return rows


def benchmark_run_local(puzzles: list[DatasetPuzzle], cfg: BenchmarkConfig, path: Path) -> int:
    rows = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, LOCAL_FIELDS, lineterminator="\n")
        writer.writeheader()
        for method in LOCAL_METHODS:
            started = time.perf_counter()
            for item in puzzles:
                for seed in range(cfg.local_seeds):
                    result = benchmark_local_solve(method, item, seed, cfg.local_max_steps)
                    writer.writerow(
                        {
                            "puzzle_id": item.puzzle_id,
                            "source": item.source,
                            "clues": item.clues,
                            "method": method,
                            "seed": seed,
                            "status": result.status,
                            "steps": result.steps,
                            "restarts": result.restarts,
                            "final_cost": result.final_cost,
                            "time_ms": round(result.time_ms, 3),
                        }
                    )
                    rows += 1
            handle.flush()
            elapsed = time.perf_counter() - started
            print(f"  {method:8s} {len(puzzles)} đề x {cfg.local_seeds} seed ({elapsed:.1f} s)")
    return rows


def benchmark_cost_curves(item: DatasetPuzzle, cfg: BenchmarkConfig, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["puzzle_id", "method", "step", "cost"])
        for method in LOCAL_METHODS:
            result = benchmark_local_solve(method, item, seed=0, max_steps=cfg.curve_steps)
            for step, cost in result.cost_history:
                writer.writerow([item.puzzle_id, method, step, cost])


def benchmark_write_env(path: Path, cfg: BenchmarkConfig, mode: str, elapsed_s: float) -> None:
    env = {
        "mode": mode,
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "elapsed_s": round(elapsed_s, 1),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "config": asdict(cfg),
    }
    path.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="bản thu nhỏ để kiểm tra nhanh")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)
    console_use_utf8()
    cfg = QUICK if args.quick else FULL
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    generated = dataset_load_generated()
    top95 = dataset_load_top95()
    systematic = benchmark_pick(generated, cfg.generated_per_level, top95, cfg.top95_count)
    local = benchmark_pick(generated, cfg.local_per_level, top95, cfg.local_top95)

    print(f"Thí nghiệm 1: 24 cấu hình x {len(systematic)} đề, trần {cfg.max_nodes} nút")
    benchmark_run_backtracking(systematic, cfg, out / "backtracking_runs.csv")
    print(
        f"Thí nghiệm 2: {len(LOCAL_METHODS)} phương pháp x {len(local)} đề x {cfg.local_seeds} seed"
    )
    benchmark_run_local(local, cfg, out / "local_runs.csv")
    curve_puzzle = next(item for item in generated if item.clues == 32)
    benchmark_cost_curves(curve_puzzle, cfg, out / "cost_curves.csv")

    elapsed = time.perf_counter() - started
    benchmark_write_env(out / "env.json", cfg, "quick" if args.quick else "full", elapsed)
    print(f"Xong sau {elapsed / 60:.1f} phút, kết quả trong {out}")
    plot_results.main(["--results", str(out)])


if __name__ == "__main__":
    main()
