# Architecture constraints

Canonical architecture record: `docs/KIEN_TRUC.md` (Vietnamese). Read it before proposing structure.
Any diff that breaks one of these invariants updates `docs/KIEN_TRUC.md` in the same diff, or says in
one line why it does not apply.

## Never do

- Import `fastapi`, `pandas`, `matplotlib`, or anything from `app/` or `experiments/` inside `sudoku_csp/`.
- Measure time while a tracer is recording. Benchmarks run with tracing off.
- `deepcopy` domains or the board inside the search loop. Undo goes through the trail.
- Report `limit` (budget hit) or `not_found` (local search gave up) as `unsolvable`.
- Commit lecture PDFs, extracted lecture text, or tool logs.

## Always do

- Cite the lecture slide (for example "L6 tr.39") in the docstring of each algorithm function.
- Write user-facing text (README, docs, report, commit messages, PR bodies) in Vietnamese.
- Pin expected test values from theory or hand calculation, never from the code's own output.
