# Inkling baseline pause and continuation — 2026-09-10

Connor wants to start the agreed 1,000-question medium experiment, rather than
prepare a separate four-request diagnostic. The runner now accepts
`--live --max-new-requests 5` to pause after at most five new requests from that
same approved plan. The five observations remain part of the baseline.

## Behavior

The full stage reservation remains held. Previously completed rows are
authenticated and skipped on continuation. A pause cannot finish or reconcile
the stage, bypass launch evidence, or recover an uncertain attempt. Continuing
without the flag sends only the remaining questions; repeating the flag permits
at most five further new requests. Invalid limits refuse before collection.

The update changes the execution hash. It does not change the 1,000 questions,
prompts, gold mappings, effort, 32,768-token cap, input-count request hashes or
approved $250 medium / $250 conditional-max ceilings. Launch evidence created
before this update needs a freshly reviewed execution hash at a new file path.
Detailed first-launch and continuation commands are in
`reap/inkling_baseline/RUNBOOK.md`.

## Verification and launch state

The new pause/resume regressions failed before implementation. Mac and box offline
verification now passes 252 canonical tests (251 passed, one optional source
rebuild skipped), 14 supplemental upstream/SDK tests, and both 1,000-item synthetic
rehearsals. Independent Sol XHigh review is clean; the reviewer reran all four
SDK collection tests and nine stage-boundary tests with Python networking denied.

The preparation hash remains
`345e5727528d8af0ea208e2a0b266d33093f241fdf2744423e444bc49abc6320`.
SSH to the box initially timed out on September 10, then reconnected after Connor
reported it online. The nine-file update is installed and the complete offline
suite passed there with the same preparation hash. The expected medium input-count
file is absent; a filename search of the results directory found only the old
launch template. Connor reports that his key is set in his own box shell.
A fresh blank `results_pilot/inkling-stage-evidence/launch-medium-20260910.json`
was prepared offline without overwriting the original. Account evidence and input
counts still need completion. No generation or other provider call was made by Codex.

A Tinker reply is not itself an approval gate. Required account/route evidence
must still support the launch record. Derek's August 26 reply, supplied by Connor
in the task, confirms reasoning-inclusive caps and aggregate billing for the
native sampling route; details for the compatible route and account deduction
remain unresolved. Five normal completions cannot establish cap-collision
behavior. Separate reasoning-token counts remain optional, and no scientific
or accounting requirement is silently relaxed by this operational pause.
