"""Họ thuật toán tìm kiếm quay lui cho CSP Sudoku.

Một khung quay lui duy nhất, cắm được từng kỹ thuật cải tiến của bài giảng:

- chọn biến: thứ tự cố định, hoặc MRV và phá hòa bằng Degree;
- chọn giá trị: thứ tự tăng dần, LCV, hoặc ngẫu nhiên (dùng khi sinh lưới đầy);
- suy diễn sau mỗi phép gán: không có, Forward Checking, hoặc AC-3 duy trì phù hợp
  cung, tức MAC;
- khi thất bại: quay lui theo thứ tự thời gian, hoặc Conflict-Directed Backjumping.
"""

from __future__ import annotations

import itertools
import random
from collections import deque
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from sudoku_csp.board import CELL_COUNT, PEER_LISTS, Grid, SudokuError, board_find_conflicts
from sudoku_csp.csp import SearchStats, SudokuCSP, TraceEvent, Tracer

VarOrder = Literal["static", "mrv"]
ValueOrder = Literal["static", "lcv", "random"]
Inference = Literal["none", "fc", "ac3"]
Backjump = Literal["chronological", "cbj"]
SearchStatus = Literal["solved", "unsolvable", "limit"]


@dataclass(frozen=True, slots=True)
class BacktrackingOptions:
    var_order: VarOrder = "mrv"
    value_order: ValueOrder = "static"
    inference: Inference = "ac3"
    backjump: Backjump = "chronological"
    seed: int | None = None
    max_nodes: int = 1_000_000
    time_limit_s: float = 60.0


@dataclass(frozen=True, slots=True)
class SolveResult:
    """`limit` nghĩa là hết ngân sách trước khi kết luận, KHÔNG có nghĩa là vô nghiệm."""

    status: SearchStatus
    solution: Grid | None
    solutions_found: int
    stats: SearchStats
    events: list[TraceEvent] | None
    trace_truncated: bool


class SearchLimitReached(SudokuError):
    """Hết số nút hoặc thời gian cho phép."""


def backtracking_label(options: BacktrackingOptions) -> str:
    """Tên ngắn của cấu hình, ví dụ "MAC+MRV+LCV+CBJ"."""
    parts = [{"none": "BT", "fc": "FC", "ac3": "MAC"}[options.inference]]
    if options.var_order == "mrv":
        parts.append("MRV")
    if options.value_order == "lcv":
        parts.append("LCV")
    elif options.value_order == "random":
        parts.append("RND")
    if options.backjump == "cbj":
        parts.append("CBJ")
    return "+".join(parts)


def backtracking_option_grid(
    max_nodes: int = 1_000_000, time_limit_s: float = 60.0
) -> list[BacktrackingOptions]:
    """Đủ 24 tổ hợp: 3 kiểu suy diễn x 2 cách chọn biến x 2 cách chọn giá trị x 2 kiểu quay lui."""
    inferences: tuple[Inference, ...] = ("none", "fc", "ac3")
    var_orders: tuple[VarOrder, ...] = ("static", "mrv")
    value_orders: tuple[ValueOrder, ...] = ("static", "lcv")
    backjumps: tuple[Backjump, ...] = ("chronological", "cbj")
    return [
        BacktrackingOptions(
            var_order=var_order,
            value_order=value_order,
            inference=inference,
            backjump=backjump,
            max_nodes=max_nodes,
            time_limit_s=time_limit_s,
        )
        for inference, var_order, value_order, backjump in itertools.product(
            inferences, var_orders, value_orders, backjumps
        )
    ]


def backtracking_solve(
    puzzle: Grid,
    options: BacktrackingOptions | None = None,
    *,
    trace: bool = False,
    max_events: int = 50_000,
    solution_limit: int = 1,
) -> SolveResult:
    """Giải (hoặc đếm tối đa `solution_limit` lời giải của) một đề Sudoku.

    Thời gian trong `stats.time_ms` chỉ có ý nghĩa so sánh khi `trace=False`.
    """
    options = options or BacktrackingOptions()
    if solution_limit < 1:
        raise ValueError("solution_limit phải >= 1.")
    if solution_limit > 1 and options.backjump == "cbj":
        raise ValueError("Đếm nhiều lời giải chỉ hỗ trợ quay lui theo thứ tự thời gian.")
    tracer = Tracer(max_events) if trace else None
    csp = SudokuCSP(puzzle, tracer)
    started = perf_counter()
    search = _BacktrackingSearch(csp, options, solution_limit)
    if board_find_conflicts(puzzle):
        status: SearchStatus = "unsolvable"
    else:
        try:
            status = search.run()
        except SearchLimitReached:
            status = "limit"
    csp.stats.time_ms = (perf_counter() - started) * 1000
    if tracer is not None:
        tracer.finish({"type": "end", "status": status})
    return SolveResult(
        status=status,
        solution=search.solutions[0] if search.solutions else None,
        solutions_found=len(search.solutions),
        stats=csp.stats,
        events=tracer.events if tracer is not None else None,
        trace_truncated=tracer.truncated if tracer is not None else False,
    )


class _BacktrackingSearch:
    def __init__(self, csp: SudokuCSP, options: BacktrackingOptions, solution_limit: int) -> None:
        self.csp = csp
        self.options = options
        self.solution_limit = solution_limit
        self.cbj = options.backjump == "cbj"
        self.rng = random.Random(options.seed)
        self.deadline = perf_counter() + options.time_limit_s
        self.solutions: list[Grid] = []

    def run(self) -> SearchStatus:
        if self._initial_propagation() is not None:
            return "unsolvable"
        self._search(depth=1)
        return "solved" if self.solutions else "unsolvable"

    def _search(self, depth: int) -> tuple[bool, set[int]]:
        """Một tầng của cây quay lui. Trả (đã xong, tập xung đột cho CBJ)."""
        self._check_budget()
        var = self._select_variable()
        if var is None:
            return self._record_solution()
        csp = self.csp
        conflict: set[int] = set()
        for value in self._order_values(var):
            mark = csp.mark()
            csp.assign(var, value, depth)
            wiped = self._propagate(var)
            if wiped is None:
                solved, child_conflict = self._search(depth + 1)
                if solved:
                    return True, set()
                if self.cbj and var not in child_conflict:
                    self._retract(var, mark)
                    self._jump_over(var, child_conflict)
                    return False, child_conflict
                conflict |= child_conflict
            elif self.cbj:
                conflict |= csp.explanation(wiped)
            self._retract(var, mark)
        if self.cbj:
            conflict |= self._domain_conflict(var)
            conflict.discard(var)
        return False, conflict

    def _record_solution(self) -> tuple[bool, set[int]]:
        self.solutions.append(tuple(self.csp.values))
        return len(self.solutions) >= self.solution_limit, set()

    def _retract(self, var: int, mark: int) -> None:
        self.csp.undo_to(mark)
        self.csp.unassign(var)
        self.csp.stats.backtracks += 1

    def _jump_over(self, var: int, conflict: set[int]) -> None:
        """CBJ: `var` không nằm trong tập xung đột nên thử giá trị khác của nó là vô ích."""
        self.csp.stats.backjumps += 1
        if self.csp.tracer is not None:
            self.csp.tracer.emit({"type": "backjump", "cell": var, "conflict": sorted(conflict)})

    def _domain_conflict(self, var: int) -> set[int]:
        """Các biến đã gán chịu trách nhiệm cho việc `var` hết giá trị thử được."""
        csp = self.csp
        if self.options.inference != "none":
            return csp.explanation(var)
        domain = csp.domains[var]
        return {
            peer
            for peer in PEER_LISTS[var]
            if csp.values[peer] in domain and not csp.is_given(peer)
        }

    def _check_budget(self) -> None:
        if self.csp.stats.nodes >= self.options.max_nodes or perf_counter() > self.deadline:
            raise SearchLimitReached

    def _legal_values(self, cell: int) -> list[int]:
        """Các giá trị còn hợp lệ. Khi có suy diễn, miền đã được thu hẹp sẵn; khi không có,
        phải loại trừ giá trị của các láng giềng đã gán (kiểm tra ràng buộc)."""
        domain = self.csp.domains[cell]
        if self.options.inference != "none":
            return sorted(domain)
        values = self.csp.values
        taken = {values[peer] for peer in PEER_LISTS[cell]}
        return sorted(domain - taken)

    def _select_variable(self) -> int | None:
        """Thứ tự cố định, hoặc MRV: ít giá trị hợp lệ nhất, hòa thì chọn ô có
        nhiều láng giềng chưa gán nhất, tức Degree, hòa tiếp thì chọn ô đứng trước."""
        values = self.csp.values
        if self.options.var_order == "static":
            return next((cell for cell in range(CELL_COUNT) if values[cell] == 0), None)
        best: int | None = None
        best_key: tuple[int, int] = (10, 0)
        for cell in range(CELL_COUNT):
            if values[cell]:
                continue
            remaining = len(self._legal_values(cell))
            degree = sum(1 for peer in PEER_LISTS[cell] if values[peer] == 0)
            key = (remaining, -degree)
            if key < best_key:
                best, best_key = cell, key
        return best

    def _order_values(self, cell: int) -> list[int]:
        """Tăng dần, ngẫu nhiên, hoặc LCV: ưu tiên giá trị loại bỏ ít lựa chọn nhất của các
        láng giềng chưa gán."""
        legal = self._legal_values(cell)
        if self.options.value_order == "random":
            self.rng.shuffle(legal)
            return legal
        if self.options.value_order == "lcv":
            return sorted(legal, key=lambda value: (self._lcv_score(cell, value), value))
        return legal

    def _lcv_score(self, cell: int, value: int) -> int:
        """Số láng giềng chưa gán sẽ mất `value` nếu gán cell = value."""
        csp = self.csp
        values = csp.values
        score = 0
        for peer in PEER_LISTS[cell]:
            if values[peer] or value not in csp.domains[peer]:
                continue
            if self.options.inference == "none" and any(
                values[other] == value for other in PEER_LISTS[peer]
            ):
                continue
            score += 1
        return score

    def _initial_propagation(self) -> int | None:
        """Lan truyền từ các ô cho sẵn trước khi tìm kiếm. Trả ô bị rỗng miền nếu có."""
        inference = self.options.inference
        if inference == "fc":
            for cell in range(CELL_COUNT):
                if self.csp.is_given(cell):
                    wiped = self._forward_check(cell, frozenset())
                    if wiped is not None:
                        return wiped
        elif inference == "ac3":
            values = self.csp.values
            return self._ac3(
                deque((x, y) for x in range(CELL_COUNT) if values[x] == 0 for y in PEER_LISTS[x])
            )
        return None

    def _propagate(self, var: int) -> int | None:
        """Suy diễn sau phép gán var. Trả ô bị rỗng miền (thất bại) hoặc None."""
        inference = self.options.inference
        if inference == "fc":
            return self._forward_check(var, frozenset((var,)))
        if inference == "ac3":
            values = self.csp.values
            return self._ac3(deque((peer, var) for peer in PEER_LISTS[var] if values[peer] == 0))
        return None

    def _forward_check(self, var: int, causes: frozenset[int]) -> int | None:
        """Forward Checking: xóa giá trị của var khỏi miền các láng giềng chưa gán."""
        csp = self.csp
        value = csp.values[var]
        for peer in PEER_LISTS[var]:
            if csp.values[peer] != 0 or value not in csp.domains[peer]:
                continue
            if csp.prune(peer, value, causes, "fc"):
                return peer
        return None

    def _ac3(self, queue: deque[tuple[int, int]]) -> int | None:
        """AC-3: duyệt hàng đợi cung (X -> Y) cho tới khi mọi cung đều phù hợp.

        Khi D(X) bị thu hẹp, mọi cung (Z -> X) với Z != Y được xét lại.
        """
        csp = self.csp
        values = csp.values
        queued = set(queue)
        while queue:
            arc = queue.popleft()
            queued.discard(arc)
            x, y = arc
            if not self._revise(x, y):
                continue
            if not csp.domains[x]:
                return x
            for z in PEER_LISTS[x]:
                if z != y and values[z] == 0 and (z, x) not in queued:
                    queue.append((z, x))
                    queued.add((z, x))
        return None

    def _revise(self, x: int, y: int) -> bool:
        """Làm cung (X -> Y) phù hợp cho ràng buộc X != Y.

        Giá trị v của X mất "giá trị hỗ trợ" ở Y khi và chỉ khi D(Y) = {v}, nên chỉ cần kiểm tra
        trường hợp D(Y) còn đúng một giá trị.
        """
        csp = self.csp
        csp.stats.revisions += 1
        domain_y = csp.domains[y]
        if len(domain_y) != 1:
            return False
        (value,) = domain_y
        if value not in csp.domains[x]:
            return False
        csp.prune(x, value, csp.singleton_reason(y), "ac3")
        return True
