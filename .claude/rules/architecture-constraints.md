# Architecture constraints

Canonical architecture record: `tai-lieu-nhom/KIEN_TRUC.md` (Vietnamese, local only: the group keeps
its study notes out of the submitted repo, so the folder is gitignored). Read it before proposing
structure. Any change that breaks one of these invariants updates that file in the same session, or says
in one line why it does not apply.

## Never do

- Import `fastapi`, `pandas`, `matplotlib`, or anything from `app/` or `experiments/` inside `sudoku_csp/`.
- Measure time while a tracer is recording. Benchmarks run with tracing off.
- `deepcopy` domains or the board inside the search loop. Undo goes through the trail.
- Report `limit` (budget hit) or `not_found` (local search gave up) as `unsolvable`.
- Commit lecture PDFs, extracted lecture text, or tool logs.
- Cite lecture slides ("L6 tr.39") in README or the report. Use the lecture's knowledge without naming
  where it sits in the slides.
- Commit anything under `tai-lieu-nhom/` or link to it from README or the report.

## Always do

- Cite the lecture slide (for example "L6 tr.39") in the docstring of each algorithm function.
- Write user-facing text (README, docs, report, commit messages, PR bodies) in Vietnamese.
- Pin expected test values from theory or hand calculation, never from the code's own output.
