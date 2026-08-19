# REAP context pack for a new Linux session

Read this after `AGENTS.md` and `reap/CODEX_BRIEFING.md`. It is a compact map, not
a replacement for either source.

## The project in plain language

This paper asks whether a reasoning model looks worse because it truly gives worse
answers, or because a token limit cuts it off before it can state an answer. REAP
will vary native reasoning effort and output allowance, record why a response ended,
and separate *no final answer appeared* from *a completed answer was wrong*.

The observational work is free, exploratory evidence from public archives. It is
not confirmatory data and must never be pooled with the later intervention. The
confirmatory experiment has made **zero** paid calls.

## Hard safety boundaries

- Do not edit `PREREGISTRATION*.md`, `confirmatory_artifacts/**`, a file headed
  `FROZEN`, or the statistics in `observational/pipeline.py`.
- Never make a provider, smoke, or confirmatory call. A script must default to a
  non-live path; secrets belong only in environment variables.
- Every future request needs explicit `max_tokens`, explicit effort where supported,
  termination metadata, token usage, and a receipt/ledger trail.
- An answer exists only with an explicit `Final answer:` terminator. Termination is
  recorded beside grading, never used to invent an answer.
- Keep exploratory, synthetic, smoke, and confirmatory estimates visibly separate.

## Where work stands

- Phases 0–2 are merged. The decision-independent Phase-3 safeguards were
  independently approved at `01aeb98`, but the scientific design is still not
  frozen. The current order is resolve benchmark/model/statistical choices,
  preregistration freeze, runner/executable budget gates, human smoke, then
  confirmatory collection.
- Tinker SDK 0.25.0 can resubmit. That violates the one-submission rule, so live
  Tinker smoke is blocked rather than merely delayed.
- The public observational finding is strong but qualified: 427 rows appeared at a
  cap; public MathArena cap detection is inferred, while the HELM Gemini route has
  a published length label. Read `observational/RESULTS.md` for denominators and
  caveats rather than repeating a headline from memory.
- The current benchmark audit covers HMMT 2025/2026 through MathArena and GPQA
  through HELM. It pins 20 source files and materializes 4,248 sanitized
  benchmark-model-question cells. Read
  `reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md`.
- HMMT-2026 item 25 has a real text-version mismatch affecting 106 attempts from
  28 models. Qwen3.5-4B is missing 11 HMMT-2026 cells. These are explicit analysis
  decisions, not rows to smooth over.
- HELM evaluates a deliberate 446-question GPQA test split from 448 source rows.
  Only Gemini has complete termination labels (42 length, 404 stop), and its token
  field is all zero. HELM token fields are not a comparable cross-provider unit.

## The research question agreed after the meeting

> On the same benchmark questions and across native reasoning-effort settings, at
> accuracy levels both models actually attain, how many comparably measured output
> tokens does each use, and when the output allowance is raised, how do scored
> accuracy and unanswered length stops change?

Simple version: when two reasoning models answer the same questions, how much output
does each use at accuracy levels both can actually reach, and what changes when they
get more room to finish?

## First commands

```sh
git status --short
python3 scripts/verify_linux_handoff.py
uv sync --python 3.12.8 --extra observational
./scripts/verify_offline.sh
```

Then report: branch/commit, dirty state, handoff verification result, offline-suite
result, what is confirmed, and what remains an assumption. Do not modify a frozen
artifact or infer an unrecorded provider fact.

## High-value starting documents

1. `reap/CODEX_BRIEFING.md` — official reading order and gates.
2. `reap/18_POST_MEETING_BENCHMARK_AUDIT_2026-08-18.md` — meeting result.
3. `reap/20_BENCHMARK_COMPARISON_2026-08-18.md` — why candidate archives differ.
4. `reap/21_MODEL_PAIR_ELIGIBILITY_2026-08-18.md` — when comparisons are allowed.
5. `reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md` — what the pinned
   public files can and cannot answer at the question level.
6. `reap/next_chapter/index.html` — self-contained plain-language report of this
   chapter; its build receipt states the limits of browser verification.
7. `reap/02_BUDGET_AND_COSTS.md` and `reap/08_HYPERPARAMETER_DECISIONS.md` — no
   unbounded model work or assumed provider behavior.

`reap/linux_handoff/REPO_CONTEXT.xml` collects the main tracked documents, source,
tests, and recent commit history for fast search in a new agent session. It excludes
raw archives, restricted GPQA content, the 4,248-row derived table, generated HTML,
and secrets. It is supporting context, not a substitute for exact files or tests.

## What “done” looks like for a code task

Use a `codex/` branch, preserve unrelated work, add a focused failing test when
practical, make the smallest change, run focused plus relevant broader checks,
checkpoint-commit only owned files, and state what was verified versus assumed. A
dashboard/report can describe state; it never authorizes a paid call.
