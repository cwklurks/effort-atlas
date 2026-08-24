# Reusable prompt: sort repository files safely (effort-atlas)

Archived agent prompt. First executed 2026-08-23 via `scripts/finish_and_push.sh`.
Reuse this with any agent (Claude, Codex) when the repo root gets cluttered again.

---

You are organizing the file layout of the research repository `effort-atlas`
(project "Thinking Cut Short" / REAP). Your job is to sort loose files into a
clean structure WITHOUT changing any scientific content or breaking provenance.

## Hard invariants — violating any of these is failure

1. NEVER move, rename, edit, or delete: `PREREGISTRATION.md`,
   `PREREGISTRATION_AMENDMENT_*.md`, `confirmatory_artifacts/`,
   `observational/pipeline.py`, or anything the repo marks frozen or protected.
2. NEVER move evidence-chain files referenced by name from the frozen
   preregistration: `RESEARCH_LOG.md`, `TRUNCATION_STUDY.md`, `CAP_SEMANTICS.md`.
   They stay at repo root.
3. NEVER edit file contents while sorting, with one exception: updating a
   relative link in a NON-frozen file so it points at a file you moved. List
   every such edit in your report.
4. NEVER delete anything. Sorting is `mv`/`git mv` only.
5. NEVER commit restricted content: `capabilities/restricted_local/` (GPQA
   plaintext) must stay gitignored wherever it ends up.
6. Root keeps its working identity: `README.md`, `LICENSE`, `CITATION.cff`,
   `AGENTS.md`, `TASK.md`, `METHODS_BRIEF.md`, `CONFIRMATORY_PREFLIGHT.md`,
   `config*.yaml`, `pyproject.toml`, `requirements.txt`, `uv.lock`,
   `.python-version` do not move.
7. Do not touch `src/`, `tests/`, `scripts/`, `reap/`, `observational/`,
   `capabilities/`, `pilot/`, or cache/results directories — they are already
   organized and code references their paths.

## Procedure

1. `git status --short` first. Classify every loose root file as tracked
   (needs `git mv`) or untracked (plain `mv`). Never guess — check.
2. Before moving anything, grep the repo (excluding `.git`, `.venv`, `site/`,
   `review-*/`) for references to each filename you intend to move. A reference
   from a frozen file means the file does not move. A reference from a
   non-frozen file means you update that link (invariant 3).
3. Sort into `docs/` by purpose, not by file type alone:
   - `docs/meetings/` — meeting prep, call runbooks/cribs, decision logs,
     anything named for Chirag or a call
   - `docs/paper/` — outlines, draft reviews, submission-facing prose
   - `docs/outreach/` — outreach packets and research
   - `docs/visuals/` — standalone HTML explainers, tldraw, figures not owned
     by `observational/`
4. Keep or update `docs/README.md` as the index: one line per file, what it is,
   old path. A reader must be able to find anything that used to be at root.
5. Commit the sort as its own commit ("chore: organize ...") separate from any
   content work, so the diff is pure renames/adds and trivially reviewable.
6. Report: every move (old → new), every link edit, everything you deliberately
   did NOT move and why, and the output of `git status --short` afterward.

## The test that you did it right

`git log --stat -1` on the sort commit shows only renames, `docs/` additions,
and the listed link fixes; `python3 capabilities/validate.py` and the offline
test suite still pass; and nothing under invariants 1–2 has a changed path.
