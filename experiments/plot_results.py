"""Tổng hợp `results/*.csv` thành bảng và biểu đồ cho báo cáo.

    uv run python -m experiments.plot_results

Quy ước thống kê: dùng trung vị (median) vì số nút trải dài nhiều bậc độ lớn. Lượt chạm trần được
tính bằng đúng trần (một cận dưới), nên khi hơn nửa số lượt chạm trần, trung vị chỉ là cận dưới và
được đánh dấu "≥". Tỷ lệ giải được luôn được báo kèm.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from experiments import console_use_utf8
from experiments.run_benchmark import RESULTS_DIR

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARKERS = ["o", "s", "^", "D", "v", "P"]
MAIN_CONFIGS = ["BT", "BT+MRV", "FC", "FC+MRV", "MAC", "MAC+MRV"]
LOCAL_NAMES = {
    "mc_cell": "Min-Conflicts, biểu diễn ô",
    "mc_box": "Min-Conflicts, biểu diễn khối",
    "sa": "Simulated Annealing, biểu diễn khối",
}


def plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.labelsize": 9.5,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "legend.frameon": False,
            "font.size": 9.5,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
        }
    )


def plot_clean_axes(ax: Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_axisbelow(True)


def plot_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], frame.to_dict("records"))


def summarize_backtracking(runs: pd.DataFrame) -> pd.DataFrame:
    """Mỗi (nguồn đề, cấu hình): tỷ lệ giải được, trung vị số nút/thời gian, µs mỗi nút."""
    grouped = runs.groupby(["source", "label"], sort=False)
    summary = grouped.agg(
        puzzles=("puzzle_id", "count"),
        decided=("status", lambda s: (s != "limit").mean() * 100),
        median_nodes=("nodes", "median"),
        median_time_ms=("time_ms", "median"),
        total_nodes=("nodes", "sum"),
        total_time_ms=("time_ms", "sum"),
    ).reset_index()
    summary["us_per_node"] = summary["total_time_ms"] * 1000 / summary["total_nodes"].clip(lower=1)
    censored = grouped["status"].apply(lambda s: (s == "limit").mean() > 0.5).reset_index(drop=True)
    summary["median_is_lower_bound"] = censored
    return summary.drop(columns=["total_nodes", "total_time_ms"])


def summarize_local(runs: pd.DataFrame) -> pd.DataFrame:
    runs = runs.assign(level=runs["clues"].where(runs["source"] == "generated", -1))
    grouped = runs.groupby(["method", "level"])
    return grouped.agg(
        runs=("status", "count"),
        solved=("status", lambda s: (s == "solved").mean() * 100),
        median_steps=("steps", "median"),
        median_time_ms=("time_ms", "median"),
    ).reset_index()


def plot_configs_on_top95(summary: pd.DataFrame, budget: int, path: Path) -> None:
    """H1: trung vị số nút của 24 cấu hình trên top95, xếp tăng dần."""
    data = summary.loc[summary["source"] == "top95"].sort_values(by="median_nodes", ascending=False)
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    colors = [SERIES[0] if "MRV" in label else SERIES[1] for label in data["label"]]
    y = range(len(data))
    ax.barh(list(y), data["median_nodes"], color=colors, height=0.72, edgecolor=SURFACE)
    ax.set_xscale("log")
    ax.set_yticks(list(y), data["label"])
    ax.axvline(budget, color=INK_2, linewidth=1)
    ax.text(
        budget,
        len(data) - 0.2,
        f" trần {budget:,} nút".replace(",", " "),
        color=INK_2,
        fontsize=8,
        va="bottom",
    )
    for row, item in zip(y, plot_records(data), strict=True):
        prefix = "≥ " if item["median_is_lower_bound"] else ""
        ax.text(
            item["median_nodes"] * 1.08,
            row,
            f"{prefix}{item['median_nodes']:,.0f}  ({item['decided']:.0f}% giải được)".replace(
                ",", " "
            ),
            va="center",
            fontsize=7.5,
            color=INK_2,
        )
    ax.set_xlim(right=budget * 25)
    ax.set_xlabel("Trung vị số nút (phép gán) trên 95 đề top95, thang log")
    ax.set_title("Số nút cần để giải đề khó theo từng tổ hợp kỹ thuật")
    handles = [
        Rectangle((0, 0), 1, 1, color=SERIES[0]),
        Rectangle((0, 0), 1, 1, color=SERIES[1]),
    ]
    ax.legend(
        handles,
        ["chọn biến bằng MRV + Degree", "chọn biến theo thứ tự cố định"],
        loc="center right",
    )
    ax.grid(axis="y", visible=False)
    plot_clean_axes(ax)
    fig.savefig(path)
    plt.close(fig)


def plot_nodes_by_clues(runs: pd.DataFrame, budget: int, path: Path) -> None:
    """H2: trung vị số nút theo số ô cho sẵn, 6 cấu hình chính, trên bộ đề tự sinh."""
    data = runs[(runs["source"] == "generated") & runs["label"].isin(MAIN_CONFIGS)]
    medians = plot_records(data.groupby(["label", "clues"])["nodes"].median().reset_index())
    levels = sorted({int(item["clues"]) for item in medians})
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for index, label in enumerate(MAIN_CONFIGS):
        points = [(int(m["clues"]), float(m["nodes"])) for m in medians if m["label"] == label]
        if not points:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        ax.plot(
            xs,
            ys,
            marker=MARKERS[index],
            markersize=5,
            linewidth=2,
            color=SERIES[index],
            label=label,
        )
    ax.axhline(budget, color=INK_2, linewidth=1)
    ax.text(levels[0], budget * 1.15, "trần số nút", fontsize=8, color=INK_2)
    ax.set_yscale("log")
    ax.set_xticks(levels)
    ax.set_xlabel("Số ô cho sẵn của đề (30 đề mỗi mức)")
    ax.set_ylabel("Trung vị số nút, thang log")
    ax.set_title("Đề càng ít ô cho sẵn càng khó, và MRV quyết định mức tăng")
    ax.legend(ncols=6, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    plot_clean_axes(ax)
    fig.savefig(path)
    plt.close(fig)


def plot_nodes_and_time(summary: pd.DataFrame, path: Path) -> None:
    """H3: số nút, chi phí mỗi nút và thời gian của các cấu hình MRV trên top95."""
    labels = ["BT+MRV", "FC+MRV", "MAC+MRV", "MAC+MRV+LCV", "MAC+MRV+CBJ", "MAC+MRV+LCV+CBJ"]
    data = summary[(summary["source"] == "top95") & summary["label"].isin(labels)]
    data = data.set_index("label").loc[[label for label in labels if label in set(data["label"])]]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True, layout="constrained")
    y = list(range(len(data)))
    for ax, column, title, unit, decimals in (
        (axes[0], "median_nodes", "Trung vị số nút", "", 0),
        (axes[1], "us_per_node", "Thời gian mỗi nút (µs)", " µs", 1),
        (axes[2], "median_time_ms", "Trung vị thời gian (ms)", " ms", 0),
    ):
        ax.barh(y, data[column], color=SERIES[0], height=0.65, edgecolor=SURFACE)
        for row, value in zip(y, data[column], strict=True):
            ax.text(
                value * 1.02,
                row,
                f"{value:,.{decimals}f}{unit}".replace(",", " "),
                va="center",
                fontsize=8,
                color=INK_2,
            )
        ax.set_title(title, fontsize=10)
        ax.set_xlim(right=data[column].max() * 1.35)
        ax.grid(axis="y", visible=False)
        plot_clean_axes(ax)
    axes[0].set_yticks(y, list(data.index))
    axes[0].invert_yaxis()
    fig.suptitle(
        "Thời gian = số nút x chi phí mỗi nút (các cấu hình có MRV, 95 đề top95)",
        fontsize=11,
        color=INK,
    )
    fig.savefig(path)
    plt.close(fig)


def plot_local_search(
    local: pd.DataFrame, curves: pd.DataFrame, max_steps: int, path: Path
) -> None:
    """H4: (a) tỷ lệ giải được theo số ô cho sẵn, (b) h theo số bước trên một đề 32 ô."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 3.8), layout="constrained")
    for index, method in enumerate(LOCAL_NAMES):
        rows = local.loc[(local["method"] == method) & (local["level"] > 0)].sort_values(by="level")
        left.plot(
            rows["level"],
            rows["solved"],
            marker=MARKERS[index],
            markersize=5,
            linewidth=2,
            color=SERIES[index],
            label=LOCAL_NAMES[method],
        )
        curve = curves[curves["method"] == method]
        right.plot(
            curve["step"],
            curve["cost"],
            linewidth=1.4,
            color=SERIES[index],
            label=LOCAL_NAMES[method],
        )
    left.set_ylim(-3, 103)
    left.set_xlabel("Số ô cho sẵn")
    left.set_ylabel("% lượt giải được")
    steps_text = f"{max_steps:,}".replace(",", " ")
    left.set_title(f"(a) Tỷ lệ giải được trong {steps_text} bước", fontsize=10)
    left.legend(loc="lower right")
    right.set_xlabel("Bước")
    right.set_ylabel("h (số vi phạm ràng buộc)")
    right.set_title(f"(b) h theo bước trên đề {curves['puzzle_id'].iloc[0]}", fontsize=10)
    for ax in (left, right):
        plot_clean_axes(ax)
    fig.suptitle(
        "Tìm kiếm cục bộ: cách biểu diễn trạng thái quyết định kết quả", fontsize=11, color=INK
    )
    fig.savefig(path)
    plt.close(fig)


def write_tables(summary: pd.DataFrame, local: pd.DataFrame, path: Path) -> None:
    """Bảng markdown để dán vào báo cáo."""
    lines = ["# Bảng tổng hợp", "", "## Tìm kiếm hệ thống trên top95", ""]
    lines.append("| Cấu hình | % giải được | Trung vị số nút | Trung vị thời gian (ms) | µs/nút |")
    lines.append("|---|---:|---:|---:|---:|")
    top = summary.loc[summary["source"] == "top95"].sort_values(by="median_nodes")
    for row in plot_records(top):
        prefix = "≥ " if row["median_is_lower_bound"] else ""
        lines.append(
            f"| {row['label']} | {row['decided']:.0f} | {prefix}{row['median_nodes']:.0f} | "
            f"{row['median_time_ms']:.1f} | {row['us_per_node']:.1f} |"
        )
    lines += ["", "## Tìm kiếm cục bộ", "", "Lượt không giải được tính số bước bằng trần.", ""]
    lines.append("| Phương pháp | Số ô cho sẵn | Số lượt | % giải được | Trung vị số bước |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in plot_records(local.sort_values(by=["method", "level"])):
        level = "top95" if row["level"] < 0 else str(int(row["level"]))
        lines.append(
            f"| {LOCAL_NAMES[row['method']]} | {level} | {row['runs']} | {row['solved']:.0f} | "
            f"{row['median_steps']:.0f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)
    console_use_utf8()
    results: Path = args.results
    figures = results / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    plot_style()

    config = json.loads((results / "env.json").read_text(encoding="utf-8"))["config"]
    budget = config["max_nodes"]
    runs = pd.read_csv(results / "backtracking_runs.csv")
    local_runs = pd.read_csv(results / "local_runs.csv")
    curves = pd.read_csv(results / "cost_curves.csv")

    summary = summarize_backtracking(runs)
    local = summarize_local(local_runs)
    summary.round(2).to_csv(results / "summary_backtracking.csv", index=False)
    local.round(2).to_csv(results / "summary_local.csv", index=False)
    write_tables(summary, local, results / "tables.md")

    plot_configs_on_top95(summary, budget, figures / "h1_cau_hinh_top95.png")
    plot_nodes_by_clues(runs, budget, figures / "h2_so_o_cho_san.png")
    plot_nodes_and_time(summary, figures / "h3_nut_va_thoi_gian.png")
    plot_local_search(local, curves, config["local_max_steps"], figures / "h4_local_search.png")
    print(f"Đã ghi bảng và 4 hình vào {results}")


if __name__ == "__main__":
    main()
