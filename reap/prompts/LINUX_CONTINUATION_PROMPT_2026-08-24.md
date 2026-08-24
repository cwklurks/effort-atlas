# Linux continuation prompt — archived verbatim 2026-08-24

Archived per the prompt's own task 5. The text below is the exact prompt this
session was launched with.

---

You are continuing work on the research repo `effort-atlas` (project "Thinking Cut
Short" / REAP): benchmark output-token limits can cut off reasoning models before
their final answer, making higher reasoning effort look like lower accuracy.
Connor Klann is first author; Chirag Nagpal is the statistical supervisor.

SETUP
1. git clone https://github.com/cwklurks/effort-atlas.git && cd effort-atlas
2. git checkout codex/reap-governance   # everything lives on this branch, not main
3. Read, before doing anything else: AGENTS.md, reap/23_POST_MEETING_REVIEW_2026-08-23.md,
   capabilities/README.md, reap/20_BENCHMARK_COMPARISON_2026-08-18.md. Treat these as
   the project's current state of truth.

HARD RULES — violating any of these is failure
- Make NO paid, smoke, or provider API calls of any kind. The Inkling pilot is
  explicitly BLOCKED pending two decisions from Chirag (route: Tinker vs OpenRouter;
  selection: first-200 vs seeded stratified 200). Do not run it, prepare-and-fire it,
  or "test" any endpoint.
- Never edit frozen or protected files: PREREGISTRATION*.md, confirmatory_artifacts/,
  observational/pipeline.py, observational/RESULTS.md (corrections are separate
  additive files, never edits).
- GPQA question text must never be committed, printed to logs, pasted into docs, or
  uploaded anywhere. capabilities/restricted_local/ stays gitignored. Work with IDs,
  counts, and hashes only.
- Every factual claim in anything you write must cite a file path, pinned URL, or
  hash that Connor can check himself. If you cannot verify something, label it
  UNVERIFIED. Do not invent numbers.

TASKS, in order
1. Reproduce the dataset pipeline on this machine:
     pip install huggingface_hub pandas pyarrow
     python3 capabilities/acquire.py
     python3 capabilities/validate.py
   validate.py must print PASS with counts 12,102 / 448 / 541 / 1,024 / 4,428.
   Confirm the emitted JSONLs' SHA-256 values match capabilities/sources_manifest.json
   (that proves byte-identical cross-machine reproduction — report the comparison).
2. Merge the observational headline correction: merge branch
   codex/observational-headline-correction (commit 6b2e69d, adds
   observational/CORRECTION_2026-08-13.md; touches nothing frozen). Then fix the one
   stale reference in reap/20_BENCHMARK_COMPARISON_2026-08-18.md that cites the
   correction as commit "7204667" — the real commit is 6b2e69d. After this, the only
   safe headline is 15 of 17 groups with zero at-cap accuracy; never write 16/17.
3. Close the last open loose thread from the 2026-08-23 meeting: audit the HELM
   Capabilities v1.15.0 omni_math runs the same way reap/22 audited GPQA. Download the
   run archives from the public GCS bucket (pattern in
   observational/benchmark_sources_manifest.json — replace the gpqa run key with the
   omni_math run keys from runs_to_run_suites.json). Record for each archived model:
   requested max_tokens, count of finish_reason values ("length"/"stop"/blank), and
   whether token fields are usable. Write the result as
   reap/24_OMNI_MATH_HELM_AUDIT_<date>.md following reap/22's format: pinned URLs,
   generations, SHA-256 for every file, no plaintext restricted content, and an
   explicit "no provider calls were made" line. This tests Connor's meeting claim that
   omni_math has "fewer models and no censoring" — report what the files actually say.
4. Commit each task separately with clear messages; push codex/reap-governance.
5. Archive this prompt verbatim as reap/prompts/LINUX_CONTINUATION_PROMPT_<date>.md
   in the same push.

REPORT back: PASS/FAIL of the reproduction with the hash comparison, the merged
correction commit id, the omni_math audit's headline numbers with their evidence
locations, and anything that surprised you — flagged, not smoothed over.
