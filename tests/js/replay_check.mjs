// Phát lại một vết do solver Python sinh ra và in trạng thái cuối, để test Python đối chiếu.
//     node tests/js/replay_check.mjs <file.json>
// File JSON có dạng {"puzzle": "<81 ký tự>", "events": [...]}.
import { readFileSync } from "node:fs";

import { buildReplay, parsePuzzle } from "../../app/static/replay.js";

const { puzzle, events } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const replay = buildReplay(parsePuzzle(puzzle), events);
const end = replay.seek(replay.length);
const middle = { values: [], candidates: [] };
replay.seek(Math.floor(replay.length / 2));
middle.values = replay.state.values.slice();
replay.seek(replay.length);
const again = replay.state.values.slice();
process.stdout.write(
  JSON.stringify({ values: end.values, candidates: end.candidates, middle, again }),
);
