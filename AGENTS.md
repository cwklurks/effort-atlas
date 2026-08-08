# Codex instructions for effort-atlas / REAP

These instructions apply to the entire repository.

## Mandatory startup

Before taking a task, read `reap/CODEX_BRIEFING.md` and follow its ordered reading
list. Report your understanding of the project state, the task's success criteria,
and any material assumptions before editing or running task code. If the briefing
conflicts with a frozen artifact, stop and surface the conflict rather than silently
choosing one.

REAP is in the design and implementation phase. No confirmatory calls have been
made. Nothing confirmatory may run until grader v2, the analysis layer, executable
budget gates, and the REAP preregistration are complete and frozen.

## Non-negotiable research safeguards

1. Never edit frozen artifacts: `PREREGISTRATION*.md`,
   `confirmatory_artifacts/**`, any document headed `FROZEN`, or the statistical
   logic in `observational/pipeline.py`. Propose changes in a new dated file.
2. Never make paid study-generation, smoke, or provider-probe calls. Scripts must
   default to `--dry-run`; live execution is human-initiated. Read secrets only
   from environment variables and fail loudly when a required variable is unset.
   The only development-tool exception is an explicitly user-authorized OpenCode
   Go call used for repository analysis or implementation. It must not generate
   research data, receive secrets, use `--auto`, or serve as final scientific or
   financial verification.
3. Set `max_tokens` explicitly on every ordinary request template. Also set effort
   explicitly wherever the platform supports it. The only allowed omission is the
   controlled default-cap diagnostic specified in Task C; keep it isolated, label
   it exploratory, and do not execute it as Codex.
4. Record termination reason and token usage at collection time on every response
   row. Keep termination separate from extraction and grading.
5. Extract an answer only from the configured explicit `Final answer: <answer>`
   terminator. Never add last-number, dollar-span, partial-box, or similar fallback
   extraction.
6. Import upstream harness logic. Never reimplement upstream behavior as a fallback.
   If an import fails, repair or pin the environment when in scope; otherwise report
   `import_failed`.
7. Keep exploratory, smoke, synthetic, and confirmatory data visibly separate.
   Never blend their estimates or denominators.
8. Treat provider and accounting metadata as part of the result: pin providers,
   disable fallbacks, require supported parameters, reconcile receipts, and preserve
   every attempt in the append-only ledger.

## Change workflow

- Work on the task's named `codex/` branch. Task A stays on
  `codex/ecosystem-audit`; Tasks B-E use the branches named in the briefing.
- Inspect `git status` before editing. Preserve all unrelated tracked and untracked
  work. Make surgical changes only in the task's stated scope.
- Add or identify failing tests before behavior changes when practical. Run focused
  tests, then the relevant broader suite. Never claim verification that was not run.
- Make a checkpoint commit for each coherent unit. Open or update a PR; never merge.
- In every PR description, distinguish what changed, what was verified, and what was
  assumed. Expect an adversarial review that recomputes headline numbers from raw
  data and mutation-tests the tests.

## Supported local verification

- Use Python 3.12 or another interpreter satisfying `pyproject.toml`; do not use the
  repository's legacy Python 3.9 virtual environment as evidence of correctness.
- The canonical offline suite is `./scripts/verify_offline.sh` after
  `uv sync --python 3.12.8`.
- No verification command may make a model-provider call. A branch-specific suite
  may extend the canonical command but may not replace it silently.

## Development-agent routing

- Keep one Sol integration owner for each phase. Use Terra for fast, read-only
  repository exploration and Sol XHigh for independent high-consequence review.
- OpenCode Go with `opencode-go/deepseek-v4-flash` may handle bounded mechanical
  work after the exception above is in force. Give it explicit file ownership and
  measurable checks; Codex reviews every diff and reruns every claimed test.
- Builders do not approve their own work. Paid experiment execution and
  preregistration freeze remain human decisions.

## Current priority and ownership boundaries

The current critical path is Phase 0 governance, Task B acceptance, B/D integration,
REAP preregistration freeze, and Task E's runner/budget gates. Task A and the
dry-run-only Task C repair may proceed independently where ownership is isolated.
Do not begin E until the grader-v2 interfaces it depends on are accepted; do not
run any smoke or confirmatory call until the later human gate opens.

The canonical project/task state lives in `reap/CODEX_BRIEFING.md`; update that file
when the state materially changes, without rewriting frozen historical records.
