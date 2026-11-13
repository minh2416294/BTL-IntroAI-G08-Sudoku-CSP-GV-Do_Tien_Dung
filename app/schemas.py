"""Model Pydantic của API: kiểm tra input ở biên trước khi gọi thuật toán."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sudoku_csp.board import PuzzleFormatError, board_format, board_parse

Algorithm = Literal["backtracking", "min_conflicts", "simulated_annealing"]


class PuzzleRequest(BaseModel):
    puzzle: str = Field(
        max_length=400, description="81 ký tự: 1-9 là ô cho sẵn, '.' hoặc '0' là ô trống"
    )

    @field_validator("puzzle")
    @classmethod
    def normalize_puzzle(cls, value: str) -> str:
        try:
            return board_format(board_parse(value))
        except PuzzleFormatError as err:
            raise ValueError(str(err)) from err


class BacktrackingSettings(BaseModel):
    var_order: Literal["static", "mrv"] = "mrv"
    value_order: Literal["static", "lcv"] = "static"
    inference: Literal["none", "fc", "ac3"] = "ac3"
    backjump: Literal["chronological", "cbj"] = "chronological"


class LocalSettings(BaseModel):
    representation: Literal["cell", "box"] = "box"
    max_steps: int = Field(default=20_000, ge=1, le=200_000)
    seed: int | None = None


class SolveRequest(PuzzleRequest):
    algorithm: Algorithm = "backtracking"
    backtracking: BacktrackingSettings = Field(default_factory=BacktrackingSettings)
    local: LocalSettings = Field(default_factory=LocalSettings)
    trace: bool = True


class SolveResponse(BaseModel):
    algorithm: Algorithm
    label: str
    status: str
    puzzle: str
    grid: str | None
    stats: dict[str, float]
    events: list[dict[str, object]]
    trace_truncated: bool


class AnalyzeResponse(BaseModel):
    clues: int
    conflicts: list[tuple[int, int]]
    solution_count: int | None = Field(
        description="0, 1, 2 (nghĩa là từ 2 trở lên), hoặc null nếu chưa kết luận"
    )
    solution: str | None


class GenerateRequest(BaseModel):
    clues: int = Field(default=32, ge=22, le=70)
    seed: int | None = Field(default=None, ge=0, le=2**31)


class GenerateResponse(BaseModel):
    puzzle: str
    solution: str
    clues: int
    seed: int


class Sample(BaseModel):
    name: str
    source: str
    clues: int
    puzzle: str
