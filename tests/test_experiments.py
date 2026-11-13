from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from experiments import notebook_attach_figures, plot_results, run_benchmark

FIGURES = [
    "h1_cau_hinh_top95.png",
    "h2_so_o_cho_san.png",
    "h3_nut_va_thoi_gian.png",
    "h4_local_search.png",
]


@pytest.fixture(scope="module")
def quick_results(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("results")
    run_benchmark.main(["--quick", "--out", str(out)])
    plot_results.main(["--results", str(out)])
    return out


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_quick_benchmark_runs_all_24_configurations(quick_results: Path) -> None:
    rows = _rows(quick_results / "backtracking_runs.csv")
    assert len({row["label"] for row in rows}) == 24
    assert len(rows) == 24 * (7 + 2)


def test_quick_benchmark_runs_every_local_method(quick_results: Path) -> None:
    rows = _rows(quick_results / "local_runs.csv")
    assert {row["method"] for row in rows} == {"mc_cell", "mc_box", "sa"}
    assert len(rows) == 3 * (7 + 1)


def test_budget_is_recorded_for_reproducibility(quick_results: Path) -> None:
    env = json.loads((quick_results / "env.json").read_text(encoding="utf-8"))
    assert (env["mode"], env["config"]["max_nodes"]) == ("quick", 5_000)


def test_figures_and_tables_are_written(quick_results: Path) -> None:
    assert all((quick_results / "figures" / name).stat().st_size > 10_000 for name in FIGURES)
    assert "| MAC+MRV |" in (quick_results / "tables.md").read_text(encoding="utf-8")


def test_attachments_are_embedded_for_referenced_images() -> None:
    notebook: dict[str, Any] = {
        "cells": [
            {"cell_type": "markdown", "source": ["![H](attachment:so_sanh_mac_fc.jpg)"]},
            {"cell_type": "markdown", "source": ["chữ thường"], "attachments": {"x": {}}},
        ]
    }
    attached = notebook_attach_figures.notebook_attach(notebook)
    cells = notebook["cells"]
    assert attached == ["so_sanh_mac_fc.jpg"]
    assert "image/jpeg" in cells[0]["attachments"]["so_sanh_mac_fc.jpg"]
    assert "attachments" not in cells[1]
