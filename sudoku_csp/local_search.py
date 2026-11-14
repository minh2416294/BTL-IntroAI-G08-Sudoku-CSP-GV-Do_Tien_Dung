"""Tìm kiếm cục bộ cho CSP Sudoku.

Mỗi trạng thái là một phép gán ĐẦY ĐỦ cho mọi ô, kể cả khi còn vi phạm ràng buộc. Dịch chuyển là
đổi giá trị của một vài ô, và trạng thái đích là trạng thái không còn ràng buộc nào bị vi phạm.
Có hai cách biểu diễn trạng thái:

- "cell" (cách biểu diễn trực tiếp): mỗi ô trống nhận một số bất kỳ 1..9. Hàm đánh giá h là số cặp ô
  láng giềng mang cùng số, tức số ràng buộc nhị phân bị vi phạm.
- "box": mỗi khối 3x3 luôn chứa một hoán vị của 1..9, nên ràng buộc khối luôn thỏa; bước đi là
  đổi chỗ hai ô không cho sẵn trong cùng một khối. h là tổng số chữ số còn thiếu trên các hàng
  và các cột.

Hai thuật toán: Min-Conflicts và Simulated Annealing.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from sudoku_csp.board import (
    BOX_OF,
    BOXES,
    CELL_COUNT,
    COL_OF,
    COLS,
    DIGITS,
    PEER_LISTS,
    ROW_OF,
    ROWS,
    Grid,
    board_find_conflicts,
)
from sudoku_csp.csp import TraceEvent, Tracer

Representation = Literal["cell", "box"]
LocalStatus = Literal["solved", "not_found"]


@dataclass(frozen=True, slots=True)
class LocalSearchResult:
    """`not_found` nghĩa là hết ngân sách bước, KHÔNG chứng minh được đề vô nghiệm."""

    status: LocalStatus
    grid: Grid
    steps: int
    restarts: int
    final_cost: int
    time_ms: float
    cost_history: tuple[tuple[int, int], ...]
    events: list[TraceEvent] | None
    trace_truncated: bool


def local_conflict_pairs(grid: Grid) -> int:
    """h của biểu diễn "cell": số cặp ô láng giềng mang cùng một số."""
    return len(board_find_conflicts(grid))


def local_rowcol_cost(grid: Grid) -> int:
    """h của biểu diễn "box": tổng số chữ số còn thiếu trên 9 hàng và 9 cột."""
    return sum(9 - len({grid[cell] for cell in unit}) for unit in ROWS + COLS)


class _CellState:
    """Biểu diễn "cell": giữ số xung đột của từng ô để cập nhật h trong O(20) mỗi bước."""

    def __init__(self, puzzle: Grid, rng: random.Random) -> None:
        self.puzzle = puzzle
        self.rng = rng
        self.free = [cell for cell in range(CELL_COUNT) if not puzzle[cell]]
        self.values = list(puzzle)
        self.conflicts = [0] * CELL_COUNT
        self.cost = 0

    def randomize(self) -> None:
        for cell in self.free:
            self.values[cell] = self.rng.randint(1, 9)
        values = self.values
        self.conflicts = [
            sum(1 for peer in PEER_LISTS[cell] if values[peer] == values[cell])
            for cell in range(CELL_COUNT)
        ]
        self.cost = sum(self.conflicts) // 2

    def conflicted(self) -> list[int]:
        return [cell for cell in self.free if self.conflicts[cell]]

    def count_with(self, cell: int, value: int) -> int:
        values = self.values
        return sum(1 for peer in PEER_LISTS[cell] if values[peer] == value)

    def set_value(self, cell: int, value: int) -> None:
        old = self.values[cell]
        if old == value:
            return
        for peer in PEER_LISTS[cell]:
            if self.values[peer] == old:
                self.conflicts[peer] -= 1
            elif self.values[peer] == value:
                self.conflicts[peer] += 1
        new_count = self.count_with(cell, value)
        self.cost += new_count - self.conflicts[cell]
        self.conflicts[cell] = new_count
        self.values[cell] = value


class _BoxState:
    """Biểu diễn "box": đếm số lần xuất hiện của từng chữ số trên mỗi hàng, mỗi cột."""

    def __init__(self, puzzle: Grid, rng: random.Random) -> None:
        self.puzzle = puzzle
        self.rng = rng
        self.free_by_box = [[cell for cell in box if not puzzle[cell]] for box in BOXES]
        self.swappable_boxes = [b for b, cells in enumerate(self.free_by_box) if len(cells) >= 2]
        self.free = [cell for cells in self.free_by_box for cell in cells]
        self.values = list(puzzle)
        self.row_count = [[0] * 10 for _ in range(9)]
        self.col_count = [[0] * 10 for _ in range(9)]
        self.cost = 0

    def randomize(self) -> None:
        """Điền mỗi khối bằng một hoán vị ngẫu nhiên của các chữ số khối đó còn thiếu."""
        for box, cells in zip(BOXES, self.free_by_box, strict=True):
            missing = list(DIGITS - {self.puzzle[cell] for cell in box})
            self.rng.shuffle(missing)
            for cell, value in zip(cells, missing, strict=True):
                self.values[cell] = value
        self.row_count = [[0] * 10 for _ in range(9)]
        self.col_count = [[0] * 10 for _ in range(9)]
        for cell, value in enumerate(self.values):
            self.row_count[ROW_OF[cell]][value] += 1
            self.col_count[COL_OF[cell]][value] += 1
        self.cost = local_rowcol_cost(tuple(self.values))

    def conflicted(self) -> list[int]:
        values = self.values
        return [
            cell
            for cell in self.free
            if self.row_count[ROW_OF[cell]][values[cell]] > 1
            or self.col_count[COL_OF[cell]][values[cell]] > 1
        ]

    def swap_delta(self, a: int, b: int) -> int:
        """Độ thay đổi của h nếu đổi chỗ giá trị của hai ô a, b (cùng khối, khác giá trị)."""
        va, vb = self.values[a], self.values[b]
        delta = 0
        for counts, line_a, line_b in (
            (self.row_count, ROW_OF[a], ROW_OF[b]),
            (self.col_count, COL_OF[a], COL_OF[b]),
        ):
            if line_a == line_b:
                continue
            delta += _line_delta(counts[line_a], va, vb) + _line_delta(counts[line_b], vb, va)
        return delta

    def swap(self, a: int, b: int) -> None:
        delta = self.swap_delta(a, b)
        va, vb = self.values[a], self.values[b]
        for cell, old, new in ((a, va, vb), (b, vb, va)):
            self.row_count[ROW_OF[cell]][old] -= 1
            self.row_count[ROW_OF[cell]][new] += 1
            self.col_count[COL_OF[cell]][old] -= 1
            self.col_count[COL_OF[cell]][new] += 1
        self.values[a], self.values[b] = vb, va
        self.cost += delta

    def random_swap(self) -> tuple[int, int]:
        cells = self.free_by_box[self.rng.choice(self.swappable_boxes)]
        a, b = self.rng.sample(cells, 2)
        return a, b


def _line_delta(counts: list[int], removed: int, added: int) -> int:
    """Số chữ số còn thiếu trên một hàng/cột thay đổi bao nhiêu khi bỏ `removed`, thêm `added`."""
    delta = 0
    if counts[removed] == 1:
        delta += 1
    if counts[added] == 0:
        delta -= 1
    return delta


class _Run:
    """Phần dùng chung: ngân sách, lấy mẫu chi phí, ghi vết."""

    def __init__(
        self, max_steps: int, time_limit_s: float, sample_every: int, tracer: Tracer | None
    ) -> None:
        self.max_steps = max_steps
        self.deadline = perf_counter() + time_limit_s
        self.sample_every = sample_every
        self.tracer = tracer
        self.started = perf_counter()
        self.history: list[tuple[int, int]] = []
        self.steps = 0
        self.restarts = 0

    def out_of_budget(self) -> bool:
        if self.steps >= self.max_steps:
            return True
        return self.steps % 256 == 0 and perf_counter() > self.deadline

    def sample(self, cost: int) -> None:
        if self.steps % self.sample_every == 0:
            self.history.append((self.steps, cost))

    def emit(self, event: TraceEvent) -> None:
        if self.tracer is not None:
            self.tracer.emit(event)

    def result(self, values: list[int], cost: int) -> LocalSearchResult:
        status: LocalStatus = "solved" if cost == 0 else "not_found"
        if not self.history or self.history[-1][0] != self.steps:
            self.history.append((self.steps, cost))
        if self.tracer is not None:
            self.tracer.finish({"type": "end", "status": status})
        return LocalSearchResult(
            status=status,
            grid=tuple(values),
            steps=self.steps,
            restarts=self.restarts,
            final_cost=cost,
            time_ms=(perf_counter() - self.started) * 1000,
            cost_history=tuple(self.history),
            events=self.tracer.events if self.tracer is not None else None,
            trace_truncated=self.tracer.truncated if self.tracer is not None else False,
        )


def min_conflicts_solve(
    puzzle: Grid,
    representation: Representation = "box",
    *,
    max_steps: int = 100_000,
    restart_after: int = 2_000,
    seed: int | None = None,
    time_limit_s: float = 60.0,
    sample_every: int = 50,
    trace: bool = False,
    max_events: int = 50_000,
) -> LocalSearchResult:
    """Min-Conflicts: chọn ngẫu nhiên một ô đang vi phạm ràng buộc, rồi cho nó giá
    trị (hoặc với biểu diễn "box", đổi chỗ với ô cùng khối) làm h nhỏ nhất. Giữ nguyên hiện
    trạng cũng là một lựa chọn, hòa thì chọn ngẫu nhiên. Sau `restart_after` bước không cải thiện
    được h tốt nhất thì khởi động lại từ trạng thái ngẫu nhiên, vì leo đồi dễ kẹt ở cực trị địa
    phương.
    """
    rng = random.Random(seed)
    run = _Run(max_steps, time_limit_s, sample_every, Tracer(max_events) if trace else None)
    state: _CellState | _BoxState = (
        _CellState(puzzle, rng) if representation == "cell" else _BoxState(puzzle, rng)
    )
    state.randomize()
    run.emit({"type": "init", "values": list(state.values), "cost": state.cost})
    best, since_best = state.cost, 0
    while state.cost > 0 and not run.out_of_budget():
        run.steps += 1
        cell = rng.choice(state.conflicted())
        if isinstance(state, _CellState):
            _min_conflicts_cell_step(state, cell, rng, run)
        else:
            _min_conflicts_box_step(state, cell, rng, run)
        run.sample(state.cost)
        if state.cost < best:
            best, since_best = state.cost, 0
        else:
            since_best += 1
        if since_best >= restart_after and state.cost > 0:
            state.randomize()
            run.restarts += 1
            best, since_best = state.cost, 0
            run.emit({"type": "restart", "values": list(state.values), "cost": state.cost})
    return run.result(state.values, state.cost)


def _min_conflicts_cell_step(state: _CellState, cell: int, rng: random.Random, run: _Run) -> None:
    scores = {value: state.count_with(cell, value) for value in range(1, 10)}
    lowest = min(scores.values())
    value = rng.choice([v for v, score in scores.items() if score == lowest])
    if value != state.values[cell]:
        state.set_value(cell, value)
        run.emit({"type": "set", "cell": cell, "value": value, "cost": state.cost})


def _min_conflicts_box_step(state: _BoxState, cell: int, rng: random.Random, run: _Run) -> None:
    options: list[tuple[int, int | None]] = [(0, None)]
    options.extend(
        (state.swap_delta(cell, other), other)
        for other in state.free_by_box[BOX_OF[cell]]
        if other != cell
    )
    lowest = min(delta for delta, _ in options)
    partner = rng.choice([other for delta, other in options if delta == lowest])
    if partner is not None:
        state.swap(cell, partner)
        run.emit({"type": "swap", "a": cell, "b": partner, "cost": state.cost})


def simulated_annealing_solve(
    puzzle: Grid,
    *,
    max_steps: int = 200_000,
    alpha: float = 0.99,
    chain_length: int | None = None,
    frozen_temperature: float = 0.05,
    stuck_chains: int = 20,
    seed: int | None = None,
    time_limit_s: float = 60.0,
    sample_every: int = 50,
    trace: bool = False,
    max_events: int = 50_000,
) -> LocalSearchResult:
    """Simulated Annealing trên biểu diễn "box".

    Mỗi bước thử đổi chỗ ngẫu nhiên hai ô trong một khối. Bước làm h giảm hoặc giữ nguyên luôn
    được nhận; bước làm h tăng một lượng delta được nhận với xác suất exp(-delta / T). Nhiệt độ
    ban đầu T0 là độ lệch chuẩn của h trên các trạng thái lân cận ngẫu nhiên (Lewis 2007); sau
    mỗi chuỗi `chain_length` bước (mặc định bằng số ô trống) thì T nhân với `alpha`.

    Khi T đã xuống dưới `frozen_temperature` (lúc này bước xấu gần như không bao giờ được nhận,
    thuật toán chỉ còn là leo đồi) mà `stuck_chains` chuỗi liền không cải thiện được h tốt nhất,
    thì nâng T trở lại T0 (reheat) để thoát cực trị địa phương. Chỉ nâng nhiệt sau khi đã nguội
    hẳn, vì nâng sớm thì T không bao giờ đủ thấp để hội tụ.
    """
    rng = random.Random(seed)
    run = _Run(max_steps, time_limit_s, sample_every, Tracer(max_events) if trace else None)
    state = _BoxState(puzzle, rng)
    state.randomize()
    run.emit({"type": "init", "values": list(state.values), "cost": state.cost})
    if not state.swappable_boxes:
        return run.result(state.values, state.cost)
    chain = chain_length or max(len(state.free), 1)
    t0 = _initial_temperature(state)
    temperature = t0
    best, since_best = state.cost, 0
    while state.cost > 0 and not run.out_of_budget():
        run.steps += 1
        a, b = state.random_swap()
        delta = state.swap_delta(a, b)
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            state.swap(a, b)
            run.emit(
                {"type": "swap", "a": a, "b": b, "cost": state.cost, "temperature": temperature}
            )
        run.sample(state.cost)
        if state.cost < best:
            best, since_best = state.cost, 0
        else:
            since_best += 1
        if run.steps % chain != 0:
            continue
        temperature *= alpha
        if temperature < frozen_temperature and since_best >= stuck_chains * chain:
            temperature = t0
            since_best = 0
            run.restarts += 1
            run.emit({"type": "reheat", "temperature": temperature, "cost": state.cost})
    return run.result(state.values, state.cost)


def _initial_temperature(state: _BoxState, samples: int = 200) -> float:
    """Độ lệch chuẩn của h trên `samples` trạng thái lân cận ngẫu nhiên của trạng thái đầu."""
    costs = [state.cost + state.swap_delta(*state.random_swap()) for _ in range(samples)]
    spread = statistics.pstdev(costs)
    return spread if spread > 0 else 1.0
