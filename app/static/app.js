import {
  STATUS_TEXT,
  buildReplay,
  cellName,
  conflictingCells,
  describeEvent,
  hasCandidate,
  parsePuzzle,
} from "./replay.js";

const $ = (id) => document.getElementById(id);

const LOG_LINES = 12;
const ALGORITHMS = [
  ["backtracking", "Quay lui (L6 tr.15-39)"],
  ["min_conflicts", "Min-Conflicts (L6 tr.41)"],
  ["simulated_annealing", "Simulated Annealing (L4 tr.37-39)"],
];
const INFERENCES = [
  ["none", "Không (quay lui thuần)"],
  ["fc", "Forward Checking"],
  ["ac3", "AC-3 (MAC)"],
];
const VAR_ORDERS = [
  ["static", "Thứ tự cố định"],
  ["mrv", "MRV + Degree"],
];
const VALUE_ORDERS = [
  ["static", "Tăng dần"],
  ["lcv", "LCV"],
];
const BACKJUMPS = [
  ["chronological", "Quay lui thường"],
  ["cbj", "CBJ"],
];
const REPRESENTATIONS = [
  ["box", "Hoán vị trong khối"],
  ["cell", "Từng ô 1..9"],
];

// ---------------------------------------------------------------- bảng nhập đề

const inputCells = [];

function borderClasses(cell, base) {
  const classes = [base];
  if (cell % 9 === 2 || cell % 9 === 5) classes.push("border-right");
  const row = Math.floor(cell / 9);
  if (row === 2 || row === 5) classes.push("border-bottom");
  return classes.join(" ");
}

function buildInputGrid() {
  const grid = $("input-grid");
  for (let cell = 0; cell < 81; cell += 1) {
    const input = document.createElement("input");
    input.className = borderClasses(cell, "input-cell");
    input.inputMode = "numeric";
    input.maxLength = 1;
    input.setAttribute("aria-label", `Ô ${cellName(cell)}`);
    input.addEventListener("input", () => {
      input.value = input.value.replace(/[^1-9]/g, "").slice(-1);
      clearInputMarks();
    });
    input.addEventListener("keydown", (event) => moveFocus(event, cell));
    grid.append(input);
    inputCells.push(input);
  }
}

function moveFocus(event, cell) {
  const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -9, ArrowDown: 9 }[event.key];
  if (delta === undefined) return;
  const target = cell + delta;
  if (target < 0 || target >= 81) return;
  event.preventDefault();
  inputCells[target].focus();
}

function readPuzzle() {
  return inputCells.map((input) => input.value || ".").join("");
}

function writePuzzle(text) {
  parsePuzzle(text).forEach((value, cell) => {
    inputCells[cell].value = value ? String(value) : "";
  });
  clearInputMarks();
}

function clearInputMarks() {
  for (const input of inputCells) input.classList.remove("conflict");
}

function setStatus(id, text, isError = false) {
  const element = $(id);
  element.textContent = text;
  element.classList.toggle("error", isError);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join("; ")
      : data.detail;
    throw new Error(detail ?? `Lỗi ${response.status}`);
  }
  return data;
}

async function loadSamples() {
  const select = $("sample-select");
  const response = await fetch("/api/samples");
  const samples = await response.json();
  for (const sample of samples) {
    const option = document.createElement("option");
    option.value = sample.puzzle;
    option.textContent = sample.name;
    select.append(option);
  }
  select.addEventListener("change", () => {
    writePuzzle(select.value);
    setStatus("puzzle-status", "");
  });
  if (samples.length) writePuzzle(samples[0].puzzle);
}

async function generatePuzzle() {
  const clues = Number($("clue-input").value);
  setStatus("puzzle-status", "Đang sinh đề...");
  try {
    const data = await postJson("/api/generate", { clues });
    writePuzzle(data.puzzle);
    setStatus(
      "puzzle-status",
      `Đã sinh đề ${data.clues} ô cho sẵn (seed ${data.seed}), có đúng một lời giải.`,
    );
  } catch (error) {
    setStatus("puzzle-status", error.message, true);
  }
}

async function analyzePuzzle() {
  clearInputMarks();
  setStatus("puzzle-status", "Đang kiểm tra...");
  try {
    const data = await postJson("/api/analyze", { puzzle: readPuzzle() });
    if (data.conflicts.length) {
      for (const [a, b] of data.conflicts) {
        inputCells[a].classList.add("conflict");
        inputCells[b].classList.add("conflict");
      }
      const pairs = data.conflicts.map(([a, b]) => `${cellName(a)}-${cellName(b)}`).join(", ");
      setStatus("puzzle-status", `Đề sai: các ô cho sẵn trùng số ${pairs}.`, true);
      return;
    }
    const verdict = {
      0: "Đề vô nghiệm (không vi phạm trực tiếp nhưng không có lời giải nào).",
      1: "Đề hợp lệ: có đúng một lời giải.",
      2: "Đề có từ hai lời giải trở lên.",
    }[data.solution_count];
    setStatus(
      "puzzle-status",
      `${data.clues} ô cho sẵn. ${verdict ?? "Chưa kết luận được trong giới hạn thời gian."}`,
      data.solution_count === 0,
    );
  } catch (error) {
    setStatus("puzzle-status", error.message, true);
  }
}

// ---------------------------------------------------------------- cấu hình

function selectHtml(name, choices, selected) {
  const options = choices
    .map(([value, text]) => `<option value="${value}"${value === selected ? " selected" : ""}>${text}</option>`)
    .join("");
  return `<select name="${name}">${options}</select>`;
}

function buildConfig(fieldset, defaults) {
  fieldset.insertAdjacentHTML(
    "beforeend",
    `<label>Thuật toán ${selectHtml("algorithm", ALGORITHMS, defaults.algorithm)}</label>
     <div class="option-group bt-options">
       <label>Suy diễn ${selectHtml("inference", INFERENCES, defaults.inference)}</label>
       <label>Chọn biến ${selectHtml("var_order", VAR_ORDERS, defaults.var_order)}</label>
       <label>Chọn giá trị ${selectHtml("value_order", VALUE_ORDERS, defaults.value_order)}</label>
       <label>Khi thất bại ${selectHtml("backjump", BACKJUMPS, defaults.backjump)}</label>
     </div>
     <div class="option-group ls-options">
       <label class="mc-only">Biểu diễn ${selectHtml("representation", REPRESENTATIONS, "box")}</label>
       <label>Số bước tối đa <input name="max_steps" type="number" min="1" max="200000" value="20000" /></label>
       <label>Seed <input name="seed" type="number" min="0" placeholder="ngẫu nhiên" /></label>
     </div>`,
  );
  const field = (name) => fieldset.querySelector(`[name="${name}"]`);
  const sync = () => {
    const algorithm = field("algorithm").value;
    fieldset.querySelector(".bt-options").hidden = algorithm !== "backtracking";
    fieldset.querySelector(".ls-options").hidden = algorithm === "backtracking";
    fieldset.querySelector(".mc-only").hidden = algorithm !== "min_conflicts";
  };
  field("algorithm").addEventListener("change", sync);
  sync();
  return () => ({
    algorithm: field("algorithm").value,
    backtracking: {
      inference: field("inference").value,
      var_order: field("var_order").value,
      value_order: field("value_order").value,
      backjump: field("backjump").value,
    },
    local: {
      representation: field("representation").value,
      max_steps: Number(field("max_steps").value) || 20000,
      seed: field("seed").value === "" ? null : Number(field("seed").value),
    },
  });
}

// ---------------------------------------------------------------- bảng phát lại

function createPanel(article) {
  article.innerHTML = `<h3 class="panel-title">Chưa chạy</h3>
    <p class="panel-result"></p>
    <div class="board"></div>
    <table class="stats"><tbody></tbody></table>
    <canvas class="cost-chart" width="440" height="120" hidden></canvas>
    <ol class="log"></ol>
    <p class="notice" hidden></p>`;
  const board = article.querySelector(".board");
  const cells = [];
  for (let cell = 0; cell < 81; cell += 1) {
    const div = document.createElement("div");
    const value = document.createElement("span");
    value.className = "value";
    const candidates = document.createElement("div");
    candidates.className = "cands";
    const candidateSpans = [];
    for (let digit = 1; digit <= 9; digit += 1) {
      const span = document.createElement("span");
      span.textContent = String(digit);
      candidates.append(span);
      candidateSpans.push(span);
    }
    div.append(value, candidates);
    board.append(div);
    cells.push({ div, value, candidateSpans });
  }
  return {
    article,
    cells,
    title: article.querySelector(".panel-title"),
    result: article.querySelector(".panel-result"),
    stats: article.querySelector(".stats tbody"),
    chart: article.querySelector(".cost-chart"),
    log: article.querySelector(".log"),
    notice: article.querySelector(".notice"),
    replay: null,
    response: null,
    puzzle: null,
  };
}

function loadPanel(panel, response) {
  panel.response = response;
  panel.puzzle = parsePuzzle(response.puzzle);
  panel.replay = buildReplay(panel.puzzle, response.events);
  panel.title.textContent = response.label;
  panel.result.textContent = resultText(response);
  panel.chart.hidden = response.algorithm === "backtracking";
  panel.notice.hidden = !response.trace_truncated;
  panel.notice.textContent = response.trace_truncated
    ? `Vết chỉ ghi ${response.events.length - 1} sự kiện đầu; phần thống kê bên trên là kết quả đầy đủ.`
    : "";
}

function resultText(response) {
  const { stats } = response;
  const status = STATUS_TEXT[response.status] ?? response.status;
  const time = `${stats.time_ms.toFixed(1)} ms (đo khi có ghi vết, không dùng để so hiệu năng)`;
  if (response.algorithm === "backtracking") {
    return `${status}. ${stats.nodes} nút, ${stats.backtracks} lần quay lui, ${stats.prunes} giá trị bị cắt, ${time}.`;
  }
  return `${status}. ${stats.steps} bước, ${stats.restarts} lần khởi động lại/nâng nhiệt, h cuối = ${stats.final_cost}, ${time}.`;
}

function eventHighlights(event) {
  const map = new Map();
  if (!event) return map;
  switch (event.type) {
    case "assign":
    case "set":
      map.set(event.cell, "ev-assign");
      break;
    case "prune":
      map.set(event.cell, "ev-prune");
      break;
    case "wipeout":
      map.set(event.cell, "ev-wipeout");
      break;
    case "unassign":
      map.set(event.cell, "ev-backtrack");
      break;
    case "backjump":
      for (const cell of event.conflict) map.set(cell, "ev-conflict-set");
      map.set(event.cell, "ev-backjump");
      break;
    case "swap":
      map.set(event.a, "ev-assign");
      map.set(event.b, "ev-assign");
      break;
    default:
      break;
  }
  return map;
}

function renderPanel(panel, index) {
  if (!panel.replay) return;
  const state = panel.replay.seek(index);
  const event = state.index > 0 ? panel.replay.events[state.index - 1] : null;
  const isLocal = panel.response.algorithm !== "backtracking";
  const conflicts = isLocal ? conflictingCells(state.values) : new Set();
  const highlights = eventHighlights(event);
  panel.cells.forEach((view, cell) => {
    const value = state.values[cell];
    const classes = [borderClasses(cell, "cell")];
    if (panel.puzzle[cell]) classes.push("given");
    else if (value) classes.push("filled");
    if (conflicts.has(cell)) classes.push("conflict");
    if (highlights.has(cell)) classes.push(highlights.get(cell));
    const showCandidates = !value && !isLocal;
    if (showCandidates) classes.push("show-cands");
    view.div.className = classes.join(" ");
    view.value.textContent = value ? String(value) : "";
    if (!showCandidates) return;
    view.candidateSpans.forEach((span, k) => {
      const digit = k + 1;
      span.classList.toggle("on", hasCandidate(state.candidates[cell], digit));
      const justPruned = event?.type === "prune" && event.cell === cell && event.value === digit;
      span.classList.toggle("just-pruned", justPruned);
    });
  });
  renderStats(panel, state.index);
  renderLog(panel, state.index);
  if (isLocal) renderChart(panel, state.index);
}

function renderStats(panel, index) {
  const s = panel.replay.statsAt(index);
  const isLocal = panel.response.algorithm !== "backtracking";
  const rows = isLocal
    ? [
        ["Sự kiện", `${index} / ${panel.replay.length}`],
        ["h (số vi phạm) hiện tại", s.cost ?? "-"],
        ["Nhiệt độ T", s.temperature === null ? "-" : s.temperature.toFixed(3)],
        ["Khởi động lại / nâng nhiệt", s.restarts],
      ]
    : [
        ["Sự kiện", `${index} / ${panel.replay.length}`],
        ["Số nút (phép gán)", s.nodes],
        ["Số lần quay lui", s.backtracks],
        ["Giá trị bị FC/AC-3 cắt", s.prunes],
        ["Số lần CBJ nhảy qua", s.backjumps],
      ];
  panel.stats.replaceChildren(
    ...rows.map(([label, value]) => {
      const tr = document.createElement("tr");
      const a = document.createElement("td");
      const b = document.createElement("td");
      a.textContent = label;
      b.textContent = String(value);
      tr.append(a, b);
      return tr;
    }),
  );
}

function renderLog(panel, index) {
  const start = Math.max(0, index - LOG_LINES);
  const items = [];
  for (let i = start; i < index; i += 1) {
    const li = document.createElement("li");
    li.textContent = `${i + 1}. ${describeEvent(panel.replay.events[i])}`;
    if (i === index - 1) li.className = "current";
    items.push(li);
  }
  panel.log.replaceChildren(...items);
}

function renderChart(panel, index) {
  const canvas = panel.chart;
  const ctx = canvas.getContext("2d");
  const costs = panel.replay.series.cost;
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);
  if (!costs.length) return;
  const maxCost = Math.max(1, ...costs.filter((c) => c !== null));
  const x = (i) => (i / Math.max(1, costs.length - 1)) * (width - 10) + 5;
  const y = (c) => height - 14 - (c / maxCost) * (height - 24);
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const stride = Math.max(1, Math.floor(costs.length / width));
  for (let i = 0; i < costs.length; i += stride) {
    if (costs[i] === null) continue;
    if (i === 0) ctx.moveTo(x(i), y(costs[i]));
    else ctx.lineTo(x(i), y(costs[i]));
  }
  ctx.stroke();
  ctx.strokeStyle = "#dc2626";
  ctx.beginPath();
  ctx.moveTo(x(Math.max(0, index - 1)), 0);
  ctx.lineTo(x(Math.max(0, index - 1)), height);
  ctx.stroke();
  ctx.fillStyle = "#616e7c";
  ctx.font = "11px sans-serif";
  ctx.fillText(`h theo từng sự kiện (max ${maxCost})`, 8, height - 2);
}

// ---------------------------------------------------------------- điều khiển phát lại

const panels = [];
const playback = { index: 0, playing: false, last: 0, carry: 0 };

function activePanels() {
  return panels.filter((panel) => panel.replay && !panel.article.hidden);
}

function maxLength() {
  return Math.max(0, ...activePanels().map((panel) => panel.replay.length));
}

function eventsPerSecond() {
  const slider = Number($("speed-input").value);
  return Math.max(1, Math.round(10 ** ((slider / 100) * 3.4)));
}

function setIndex(index) {
  const total = maxLength();
  playback.index = Math.max(0, Math.min(total, index));
  $("progress-input").max = String(total);
  $("progress-input").value = String(playback.index);
  $("progress-label").textContent = `Sự kiện ${playback.index} / ${total}`;
  for (const panel of activePanels()) renderPanel(panel, playback.index);
}

function stop() {
  playback.playing = false;
  $("play-btn").textContent = "Phát";
}

function tick(now) {
  if (!playback.playing) return;
  playback.carry += ((now - playback.last) / 1000) * eventsPerSecond();
  playback.last = now;
  const step = Math.floor(playback.carry);
  if (step > 0) {
    playback.carry -= step;
    setIndex(playback.index + step);
  }
  if (playback.index >= maxLength()) {
    stop();
    return;
  }
  requestAnimationFrame(tick);
}

function togglePlay() {
  if (playback.playing) {
    stop();
    return;
  }
  if (!maxLength()) return;
  if (playback.index >= maxLength()) setIndex(0);
  playback.playing = true;
  playback.last = performance.now();
  playback.carry = 0;
  $("play-btn").textContent = "Dừng";
  requestAnimationFrame(tick);
}

async function runSolvers(getters) {
  stop();
  const compare = $("compare-toggle").checked;
  const puzzle = readPuzzle();
  const configs = compare ? getters : getters.slice(0, 1);
  $("run-btn").disabled = true;
  setStatus("run-status", "Đang chạy...");
  try {
    const responses = await Promise.all(
      configs.map((get) => postJson("/api/solve", { puzzle, ...get(), trace: true })),
    );
    responses.forEach((response, k) => loadPanel(panels[k], response));
    panels[1].article.hidden = !compare;
    setStatus("run-status", "Xong. Bấm Phát để xem từng bước, hoặc kéo thanh tiến độ.");
    setIndex(0);
  } catch (error) {
    setStatus("run-status", error.message, true);
  } finally {
    $("run-btn").disabled = false;
  }
}

function wireControls(getters) {
  $("generate-btn").addEventListener("click", generatePuzzle);
  $("analyze-btn").addEventListener("click", analyzePuzzle);
  $("clear-btn").addEventListener("click", () => {
    writePuzzle(".".repeat(81));
    setStatus("puzzle-status", "");
  });
  $("compare-toggle").addEventListener("change", (event) => {
    $("config-b").hidden = !event.target.checked;
  });
  $("run-btn").addEventListener("click", () => runSolvers(getters));
  $("play-btn").addEventListener("click", togglePlay);
  $("first-btn").addEventListener("click", () => setIndex(0));
  $("prev-btn").addEventListener("click", () => setIndex(playback.index - 1));
  $("next-btn").addEventListener("click", () => setIndex(playback.index + 1));
  $("last-btn").addEventListener("click", () => setIndex(maxLength()));
  $("progress-input").addEventListener("input", (event) => {
    stop();
    setIndex(Number(event.target.value));
  });
  const updateSpeed = () => {
    $("speed-label").textContent = `${eventsPerSecond()} sự kiện/giây`;
  };
  $("speed-input").addEventListener("input", updateSpeed);
  updateSpeed();
}

function main() {
  buildInputGrid();
  const getters = [
    buildConfig($("config-a"), {
      algorithm: "backtracking",
      inference: "ac3",
      var_order: "mrv",
      value_order: "static",
      backjump: "chronological",
    }),
    buildConfig($("config-b"), {
      algorithm: "backtracking",
      inference: "fc",
      var_order: "static",
      value_order: "static",
      backjump: "chronological",
    }),
  ];
  panels.push(createPanel($("panel-a")), createPanel($("panel-b")));
  wireControls(getters);
  loadSamples().catch((error) => setStatus("puzzle-status", error.message, true));
}

main();
