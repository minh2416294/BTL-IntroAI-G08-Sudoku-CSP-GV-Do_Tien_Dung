"""Trạng thái tìm kiếm của CSP Sudoku: phép gán, miền giá trị và trail để quay lui.

Bám theo L6 tr.15-17 (quay lui gán từng biến) và tr.29 (theo dõi các giá trị còn hợp lệ của
biến chưa gán). Mọi thay đổi trên miền giá trị đi qua trail, nên quay lui chỉ cần pop trail
về một mốc: chi phí tỷ lệ với số thay đổi thật, không phải sao chép cả 81 miền ở mỗi nút.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from sudoku_csp.board import CELL_COUNT, DIGITS, Grid

TraceEvent = dict[str, object]
PruneSource = Literal["fc", "ac3"]


@dataclass(slots=True)
class SearchStats:
    """Các bộ đếm không phụ thuộc máy, cộng thời gian chạy (đo khi tắt ghi vết)."""

    nodes: int = 0
    backtracks: int = 0
    backjumps: int = 0
    prunes: int = 0
    revisions: int = 0
    max_depth: int = 0
    time_ms: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class Tracer:
    """Ghi sự kiện cho giao diện phát lại. Chỉ bật khi minh họa, không bao giờ bật khi đo."""

    max_events: int = 50_000
    events: list[TraceEvent] = field(default_factory=list)
    truncated: bool = False

    def emit(self, event: TraceEvent) -> None:
        if len(self.events) >= self.max_events:
            self.truncated = True
            return
        self.events.append(event)

    def finish(self, event: TraceEvent) -> None:
        """Sự kiện kết thúc luôn được ghi, kể cả khi vết đã bị cắt."""
        self.events.append(event)


class SudokuCSP:
    """Phép gán hiện tại, miền giá trị D(X) của từng ô và trail để hoàn tác.

    pruned_by[X][v] là tập các biến đã gán gây ra việc xóa v khỏi D(X). Conflict-Directed
    Backjumping dùng thông tin này để biết vì sao một miền bị thu hẹp (L6 tr.22). Ô cho sẵn là
    hằng số của đề nên không bao giờ xuất hiện trong các tập lý do.
    """

    def __init__(self, puzzle: Grid, tracer: Tracer | None = None) -> None:
        self.puzzle = puzzle
        self.values: list[int] = list(puzzle)
        self.domains: list[set[int]] = [{value} if value else set(DIGITS) for value in puzzle]
        self.pruned_by: list[dict[int, frozenset[int]]] = [{} for _ in range(CELL_COUNT)]
        self.trail: list[tuple[int, int]] = []
        self.stats = SearchStats()
        self.tracer = tracer

    def is_given(self, cell: int) -> bool:
        return self.puzzle[cell] != 0

    def mark(self) -> int:
        return len(self.trail)

    def undo_to(self, mark: int) -> None:
        """Khôi phục mọi giá trị đã xóa sau mốc `mark`, theo thứ tự ngược."""
        trail = self.trail
        while len(trail) > mark:
            cell, value = trail.pop()
            self.domains[cell].add(value)
            del self.pruned_by[cell][value]

    def prune(self, cell: int, value: int, causes: frozenset[int], source: PruneSource) -> bool:
        """Suy diễn xóa `value` khỏi D(cell). Trả True nếu miền trở thành rỗng."""
        self._remove(cell, value, causes)
        self.stats.prunes += 1
        if self.tracer is not None:
            self.tracer.emit({"type": "prune", "cell": cell, "value": value, "by": source})
        if self.domains[cell]:
            return False
        if self.tracer is not None:
            self.tracer.emit({"type": "wipeout", "cell": cell})
        return True

    def assign(self, cell: int, value: int, depth: int) -> None:
        """Gán cell = value và thu D(cell) về {value}; phần bị xóa được ghi lý do là chính cell."""
        self.values[cell] = value
        own = frozenset((cell,))
        for other in [v for v in self.domains[cell] if v != value]:
            self._remove(cell, other, own)
        self.stats.nodes += 1
        self.stats.max_depth = max(self.stats.max_depth, depth)
        if self.tracer is not None:
            self.tracer.emit({"type": "assign", "cell": cell, "value": value, "depth": depth})

    def unassign(self, cell: int) -> None:
        value = self.values[cell]
        self.values[cell] = 0
        if self.tracer is not None:
            self.tracer.emit({"type": "unassign", "cell": cell, "value": value})

    def explanation(self, cell: int) -> set[int]:
        """Hợp các lý do đã thu hẹp D(cell): các biến đã gán chịu trách nhiệm cho miền hiện tại."""
        result: set[int] = set()
        for causes in self.pruned_by[cell].values():
            result |= causes
        return result

    def singleton_reason(self, cell: int) -> frozenset[int]:
        """Vì sao D(cell) chỉ còn một giá trị: ô cho sẵn (không lý do), chính phép gán của cell,
        hoặc các lý do đã xóa những giá trị còn lại của nó."""
        if self.is_given(cell):
            return frozenset()
        if self.values[cell]:
            return frozenset((cell,))
        return frozenset(self.explanation(cell))

    def _remove(self, cell: int, value: int, causes: frozenset[int]) -> None:
        self.domains[cell].discard(value)
        self.pruned_by[cell][value] = causes
        self.trail.append((cell, value))
