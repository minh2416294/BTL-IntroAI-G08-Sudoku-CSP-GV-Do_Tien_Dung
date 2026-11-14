"""Backend FastAPI: giải đề kèm vết từng bước cho giao diện phát lại, kiểm tra đề, sinh đề.

    uv run python -m uvicorn app.main:app --reload

rồi mở http://127.0.0.1:8000. Các trần ngân sách bên dưới giữ cho một yêu cầu không làm treo
server.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    AnalyzeResponse,
    GenerateRequest,
    GenerateResponse,
    PuzzleRequest,
    Sample,
    SolveRequest,
    SolveResponse,
)
from sudoku_csp.backtracking import BacktrackingOptions, backtracking_label, backtracking_solve
from sudoku_csp.board import (
    board_clue_count,
    board_find_conflicts,
    board_format,
    board_parse,
)
from sudoku_csp.datasets import dataset_load_generated, dataset_load_top95
from sudoku_csp.generator import generator_make_puzzle
from sudoku_csp.local_search import (
    LocalSearchResult,
    min_conflicts_solve,
    simulated_annealing_solve,
)

MAX_NODES = 200_000
MAX_EVENTS = 60_000
TIME_LIMIT_S = 10.0
STATIC_DIR = Path(__file__).resolve().parent / "static"
WIKI_PUZZLE = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"

app = FastAPI(title="Sudoku CSP - BTL IT3160 nhóm 8")


@app.middleware("http")
async def revalidate_static_files(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Không có Cache-Control thì trình duyệt tự cache file tĩnh, nên sửa CSS/JS xong vẫn thấy
    bản cũ. `no-cache` bắt trình duyệt hỏi lại server (rẻ, vì có ETag) ở mỗi lần tải trang."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.post("/api/solve")
def api_solve(request: SolveRequest) -> SolveResponse:
    puzzle = board_parse(request.puzzle)
    if request.algorithm == "backtracking":
        return _solve_backtracking(request, puzzle)
    if request.algorithm == "min_conflicts":
        result = min_conflicts_solve(
            puzzle,
            request.local.representation,
            max_steps=request.local.max_steps,
            seed=request.local.seed,
            time_limit_s=TIME_LIMIT_S,
            trace=request.trace,
            max_events=MAX_EVENTS,
        )
        label = f"Min-Conflicts ({request.local.representation})"
    else:
        result = simulated_annealing_solve(
            puzzle,
            max_steps=request.local.max_steps,
            seed=request.local.seed,
            time_limit_s=TIME_LIMIT_S,
            trace=request.trace,
            max_events=MAX_EVENTS,
        )
        label = "Simulated Annealing (box)"
    return _local_response(request, label, result)


def _solve_backtracking(request: SolveRequest, puzzle: tuple[int, ...]) -> SolveResponse:
    settings = request.backtracking
    options = BacktrackingOptions(
        var_order=settings.var_order,
        value_order=settings.value_order,
        inference=settings.inference,
        backjump=settings.backjump,
        max_nodes=MAX_NODES,
        time_limit_s=TIME_LIMIT_S,
    )
    result = backtracking_solve(puzzle, options, trace=request.trace, max_events=MAX_EVENTS)
    return SolveResponse(
        algorithm="backtracking",
        label=backtracking_label(options),
        status=result.status,
        puzzle=request.puzzle,
        grid=board_format(result.solution) if result.solution else None,
        stats=result.stats.as_dict(),
        events=result.events or [],
        trace_truncated=result.trace_truncated,
    )


def _local_response(request: SolveRequest, label: str, result: LocalSearchResult) -> SolveResponse:
    return SolveResponse(
        algorithm=request.algorithm,
        label=label,
        status=result.status,
        puzzle=request.puzzle,
        grid=board_format(result.grid),
        stats={
            "steps": result.steps,
            "restarts": result.restarts,
            "final_cost": result.final_cost,
            "time_ms": result.time_ms,
        },
        events=result.events or [],
        trace_truncated=result.trace_truncated,
    )


@app.post("/api/analyze")
def api_analyze(request: PuzzleRequest) -> AnalyzeResponse:
    """Kiểm tra đề: các cặp ô cho sẵn trùng số, và đề có 0, 1 hay từ 2 lời giải trở lên."""
    puzzle = board_parse(request.puzzle)
    options = BacktrackingOptions(
        var_order="mrv", inference="ac3", max_nodes=MAX_NODES, time_limit_s=TIME_LIMIT_S
    )
    result = backtracking_solve(puzzle, options, solution_limit=2)
    return AnalyzeResponse(
        clues=board_clue_count(puzzle),
        conflicts=board_find_conflicts(puzzle),
        solution_count=None if result.status == "limit" else result.solutions_found,
        solution=board_format(result.solution) if result.solution else None,
    )


@app.post("/api/generate")
def api_generate(request: GenerateRequest) -> GenerateResponse:
    seed = request.seed if request.seed is not None else random.randrange(2**31)
    generated = generator_make_puzzle(request.clues, seed)
    return GenerateResponse(
        puzzle=board_format(generated.puzzle),
        solution=board_format(generated.solution),
        clues=generated.clues,
        seed=seed,
    )


@app.get("/api/samples")
def api_samples() -> list[Sample]:
    samples = [
        Sample(name="Ví dụ trên Wikipedia", source="wikipedia", clues=30, puzzle=WIKI_PUZZLE)
    ]
    seen_levels: set[int] = set()
    for item in dataset_load_generated():
        if item.clues in seen_levels:
            continue
        seen_levels.add(item.clues)
        samples.append(
            Sample(
                name=f"Đề tự sinh {item.clues} ô ({item.puzzle_id})",
                source="generated",
                clues=item.clues,
                puzzle=board_format(item.puzzle),
            )
        )
    samples.extend(
        Sample(
            name=f"top95 #{index} ({item.clues} ô)",
            source="top95",
            clues=item.clues,
            puzzle=board_format(item.puzzle),
        )
        for index, item in enumerate(dataset_load_top95()[:5], start=1)
    )
    return samples


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
