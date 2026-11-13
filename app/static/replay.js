// Engine phát lại thuần (không đụng DOM), test bằng `node --test tests/js`.
//
// Server gửi chuỗi sự kiện của thuật toán. Engine chạy thử một lượt từ đầu tới cuối, và với mỗi
// sự kiện ghi lại các thao tác nguyên tố kèm giá trị trước/sau. Nhờ vậy có thể tua tới hoặc lùi
// tới bất kỳ bước nào một cách chính xác mà server không phải gửi ảnh chụp bàn cờ ở từng bước.
//
// Miền giá trị của mỗi ô được biểu diễn bằng bitmask: bit v bật nghĩa là v còn trong miền.
// Quay lui dùng cùng cơ chế trail như solver Python: mỗi phép gán ghi một mốc, khi bỏ gán thì
// khôi phục mọi giá trị đã bị FC/AC-3 xóa sau mốc đó.

export const ALL_CANDIDATES = 0b1111111110;

export const PEERS = Array.from({ length: 81 }, (_, cell) => {
  const row = Math.floor(cell / 9);
  const col = cell % 9;
  const peers = [];
  for (let other = 0; other < 81; other += 1) {
    if (other === cell) continue;
    const r = Math.floor(other / 9);
    const c = other % 9;
    const sameBox = Math.floor(r / 3) === Math.floor(row / 3) && Math.floor(c / 3) === Math.floor(col / 3);
    if (r === row || c === col || sameBox) peers.push(other);
  }
  return peers;
});

export const STATUS_TEXT = {
  solved: "Đã tìm thấy lời giải",
  unsolvable: "Đã duyệt hết không gian tìm kiếm: đề vô nghiệm",
  limit: "Hết ngân sách trước khi kết luận (không có nghĩa là vô nghiệm)",
  not_found: "Hết số bước, chưa tìm thấy lời giải (tìm kiếm cục bộ không chứng minh được vô nghiệm)",
};

export function parsePuzzle(text) {
  const chars = [...text].filter((ch) => !/\s/.test(ch));
  if (chars.length !== 81) throw new Error(`Đề phải có đúng 81 ô, nhận được ${chars.length}.`);
  return chars.map((ch) => (ch === "." || ch === "0" ? 0 : Number(ch)));
}

export function cellName(cell) {
  return `(${Math.floor(cell / 9) + 1},${(cell % 9) + 1})`;
}

export function hasCandidate(mask, value) {
  return (mask & (1 << value)) !== 0;
}

export function conflictingCells(values) {
  const result = new Set();
  for (let cell = 0; cell < 81; cell += 1) {
    const value = values[cell];
    if (value && PEERS[cell].some((peer) => values[peer] === value)) result.add(cell);
  }
  return result;
}

export function describeEvent(event) {
  switch (event.type) {
    case "assign":
      return `Gán ô ${cellName(event.cell)} = ${event.value} (độ sâu ${event.depth})`;
    case "prune":
      return event.by === "fc"
        ? `FC (L6 tr.29): xóa ${event.value} khỏi miền ô ${cellName(event.cell)}`
        : `AC-3 (L6 tr.39): xóa ${event.value} khỏi miền ô ${cellName(event.cell)}`;
    case "wipeout":
      return `Miền ô ${cellName(event.cell)} rỗng: nhánh này thất bại`;
    case "unassign":
      return `Quay lui: bỏ gán ô ${cellName(event.cell)} = ${event.value}`;
    case "backjump":
      return `CBJ (L6 tr.22): nhảy qua ô ${cellName(event.cell)}, tập xung đột {${event.conflict
        .map(cellName)
        .join(", ")}}`;
    case "init":
      return `Khởi tạo phép gán đầy đủ ngẫu nhiên, h = ${event.cost}`;
    case "restart":
      return `Kẹt quá lâu: khởi động lại ngẫu nhiên, h = ${event.cost}`;
    case "set":
      return `Min-Conflicts (L6 tr.41): đổi ô ${cellName(event.cell)} thành ${event.value}, h = ${event.cost}`;
    case "swap":
      if (event.temperature === undefined) {
        return `Min-Conflicts: đổi chỗ ${cellName(event.a)} và ${cellName(event.b)}, h = ${event.cost}`;
      }
      return `SA (L4 tr.38): đổi chỗ ${cellName(event.a)} và ${cellName(event.b)}, h = ${event.cost}, T = ${event.temperature.toFixed(3)}`;
    case "reheat":
      return `SA: kẹt khi đã nguội, nâng nhiệt độ lại T = ${event.temperature.toFixed(3)}`;
    case "end":
      return STATUS_TEXT[event.status] ?? event.status;
    default:
      return event.type;
  }
}

export function buildReplay(puzzle, events) {
  const sim = { values: puzzle.slice(), candidates: puzzle.map((v) => (v ? 0 : ALL_CANDIDATES)) };
  const initial = { values: sim.values.slice(), candidates: sim.candidates.slice() };
  const ops = [];
  const series = {
    nodes: [],
    backtracks: [],
    prunes: [],
    backjumps: [],
    restarts: [],
    cost: [],
    temperature: [],
  };
  const totals = {
    nodes: 0,
    backtracks: 0,
    prunes: 0,
    backjumps: 0,
    restarts: 0,
    cost: null,
    temperature: null,
  };
  const markers = [];
  const pruneLog = [];

  for (const event of events) {
    const eventOps = [];
    const setValue = (cell, value) => {
      if (sim.values[cell] === value) return;
      eventOps.push(["v", cell, sim.values[cell], value]);
      sim.values[cell] = value;
    };
    const setCandidates = (cell, mask) => {
      if (sim.candidates[cell] === mask) return;
      eventOps.push(["c", cell, sim.candidates[cell], mask]);
      sim.candidates[cell] = mask;
    };
    applyEvent(event, { sim, setValue, setCandidates, markers, pruneLog, totals });
    ops.push(eventOps);
    for (const key of Object.keys(series)) series[key].push(totals[key]);
  }

  const state = { values: initial.values.slice(), candidates: initial.candidates.slice(), index: 0 };

  function apply(i) {
    for (const [kind, cell, , after] of ops[i]) {
      if (kind === "v") state.values[cell] = after;
      else state.candidates[cell] = after;
    }
  }

  function revert(i) {
    const list = ops[i];
    for (let k = list.length - 1; k >= 0; k -= 1) {
      const [kind, cell, before] = list[k];
      if (kind === "v") state.values[cell] = before;
      else state.candidates[cell] = before;
    }
  }

  function seek(target) {
    const goal = Math.max(0, Math.min(events.length, target));
    while (state.index < goal) {
      apply(state.index);
      state.index += 1;
    }
    while (state.index > goal) {
      state.index -= 1;
      revert(state.index);
    }
    return state;
  }

  function statsAt(index) {
    const at = Math.min(index, events.length) - 1;
    const pick = (key, fallback) => (at >= 0 ? series[key][at] : fallback);
    return {
      nodes: pick("nodes", 0),
      backtracks: pick("backtracks", 0),
      prunes: pick("prunes", 0),
      backjumps: pick("backjumps", 0),
      restarts: pick("restarts", 0),
      cost: pick("cost", null),
      temperature: pick("temperature", null),
    };
  }

  return { length: events.length, events, state, seek, statsAt, series, initial };
}

function applyEvent(event, ctx) {
  const { sim, setValue, setCandidates, markers, pruneLog, totals } = ctx;
  switch (event.type) {
    case "assign":
      markers.push(pruneLog.length);
      setValue(event.cell, event.value);
      totals.nodes += 1;
      break;
    case "prune":
      pruneLog.push([event.cell, event.value]);
      setCandidates(event.cell, sim.candidates[event.cell] & ~(1 << event.value));
      totals.prunes += 1;
      break;
    case "unassign": {
      const mark = markers.length ? markers.pop() : 0;
      while (pruneLog.length > mark) {
        const [cell, value] = pruneLog.pop();
        setCandidates(cell, sim.candidates[cell] | (1 << value));
      }
      setValue(event.cell, 0);
      totals.backtracks += 1;
      break;
    }
    case "backjump":
      totals.backjumps += 1;
      break;
    case "init":
    case "restart":
      event.values.forEach((value, cell) => setValue(cell, value));
      totals.cost = event.cost;
      if (event.type === "restart") totals.restarts += 1;
      break;
    case "set":
      setValue(event.cell, event.value);
      totals.cost = event.cost;
      break;
    case "swap": {
      const a = sim.values[event.a];
      const b = sim.values[event.b];
      setValue(event.a, b);
      setValue(event.b, a);
      totals.cost = event.cost;
      if (event.temperature !== undefined) totals.temperature = event.temperature;
      break;
    }
    case "reheat":
      totals.cost = event.cost;
      totals.temperature = event.temperature;
      totals.restarts += 1;
      break;
    default:
      break;
  }
}
