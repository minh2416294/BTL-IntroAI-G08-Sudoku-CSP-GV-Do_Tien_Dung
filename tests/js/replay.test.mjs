import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ALL_CANDIDATES,
  PEERS,
  buildReplay,
  conflictingCells,
  describeEvent,
  hasCandidate,
  parsePuzzle,
} from "../../app/static/replay.js";

const EMPTY = Array(81).fill(0);

function backtrackingEvents() {
  return [
    { type: "prune", cell: 1, value: 5, by: "fc" },
    { type: "assign", cell: 0, value: 3, depth: 1 },
    { type: "prune", cell: 2, value: 3, by: "fc" },
    { type: "prune", cell: 9, value: 3, by: "fc" },
    { type: "unassign", cell: 0, value: 3 },
    { type: "end", status: "unsolvable" },
  ];
}

test("every cell has 20 peers", () => {
  assert.deepEqual(new Set(PEERS.map((p) => p.length)), new Set([20]));
});

test("unassign restores exactly the candidates pruned after its assignment", () => {
  const replay = buildReplay(EMPTY, backtrackingEvents());
  const end = replay.seek(replay.length);
  assert.equal(end.values[0], 0);
  assert.ok(hasCandidate(end.candidates[2], 3));
  assert.ok(hasCandidate(end.candidates[9], 3));
  assert.ok(!hasCandidate(end.candidates[1], 5), "initial propagation is never undone");
});

test("seeking back to the middle reproduces the forward state", () => {
  const replay = buildReplay(EMPTY, backtrackingEvents());
  replay.seek(replay.length);
  const middle = replay.seek(4);
  assert.equal(middle.values[0], 3);
  assert.ok(!hasCandidate(middle.candidates[2], 3));
  assert.ok(!hasCandidate(middle.candidates[9], 3));
});

test("seeking to zero restores the initial state", () => {
  const replay = buildReplay(EMPTY, backtrackingEvents());
  replay.seek(replay.length);
  const start = replay.seek(0);
  assert.deepEqual(start.values, EMPTY);
  assert.deepEqual(start.candidates, Array(81).fill(ALL_CANDIDATES));
});

test("counters follow the event index", () => {
  const replay = buildReplay(EMPTY, backtrackingEvents());
  assert.deepEqual(
    [replay.statsAt(0).nodes, replay.statsAt(4).prunes, replay.statsAt(5).backtracks],
    [0, 3, 1],
  );
});

test("swap exchanges two values and is reversible", () => {
  const values = Array.from({ length: 81 }, (_, i) => (i % 9) + 1);
  const events = [
    { type: "init", values, cost: 10 },
    { type: "swap", a: 0, b: 1, cost: 8, temperature: 1.5 },
  ];
  const replay = buildReplay(EMPTY, events);
  const swapped = replay.seek(2);
  assert.deepEqual([swapped.values[0], swapped.values[1]], [2, 1]);
  assert.deepEqual([replay.statsAt(2).cost, replay.statsAt(2).temperature], [8, 1.5]);
  const before = replay.seek(1);
  assert.deepEqual([before.values[0], before.values[1]], [1, 2]);
});

test("conflicting cells are the ones sharing a value with a peer", () => {
  const values = EMPTY.slice();
  values[0] = 4;
  values[8] = 4;
  values[40] = 4;
  assert.deepEqual([...conflictingCells(values)].sort((a, b) => a - b), [0, 8]);
});

test("messages cite the lecture slides", () => {
  assert.equal(
    describeEvent({ type: "prune", cell: 10, value: 7, by: "ac3" }),
    "AC-3 (L6 tr.39): xóa 7 khỏi miền ô (2,2)",
  );
  assert.equal(
    describeEvent({ type: "backjump", cell: 0, conflict: [3, 80] }),
    "CBJ (L6 tr.22): nhảy qua ô (1,1), tập xung đột {(1,4), (9,9)}",
  );
});

test("parsePuzzle reads dots and rejects wrong length", () => {
  assert.equal(parsePuzzle(`5${".".repeat(80)}`)[0], 5);
  assert.throws(() => parsePuzzle("123"));
});
