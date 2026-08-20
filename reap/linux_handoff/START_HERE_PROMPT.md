# Copy-ready prompt for a new Linux Codex session

```text
You are working in the effort-atlas / REAP repository on Linux.

Before doing anything else, read AGENTS.md and then reap/CODEX_BRIEFING.md in its
specified order. Also read reap/linux_handoff/CONTEXT_PACK.md. Run:

  git status --short
  git log -1 --oneline
  python3 scripts/verify_linux_handoff.py

Report, in plain language, your understanding of: (1) the paper's question,
(2) what is exploratory versus confirmatory, (3) the gates that still block any
paid call, (4) the frozen/protected files, (5) the current branch and dirty state,
and (6) the exact task you propose to take. Do not edit or run any provider,
smoke, or confirmatory call until a human gives a bounded task after that report.

Then read reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md and inspect
observational/benchmark_question_capabilities_summary.json. Explain the item-25
text mismatch, the 11 explicit HMMT-2026 archive gaps, the deliberate HELM 446/448
split, and why the archived token fields cannot support one cross-provider
efficiency axis. Do not print or copy restricted GPQA content.

Non-negotiable rules: never edit PREREGISTRATION*.md,
confirmatory_artifacts/**, FROZEN artifacts, or observational/pipeline.py's
statistics; never use fallback answer extraction; every future request needs
explicit max_tokens and recorded termination + usage; preserve the separation of
exploratory, synthetic, smoke, and confirmatory work. Do not use secrets from files
or paste them into prompts. No paid/provider calls are authorized.

If a benchmark-provenance task is assigned, first use the committed acquisition
manifest and verifier. Do not replace revision-pinned public sources with ad-hoc
downloads, and do not transfer or print restricted GPQA question text.

reap/linux_handoff/REPO_CONTEXT.xml is an optional search bundle of tracked project
context. Use it to orient quickly, but resolve every important claim against the
canonical file and current Git commit.

For any implementation: work on a codex/ branch, state assumptions and success
criteria, add a focused test when practical, make a surgical change, run the focused
test and relevant offline suite, and distinguish verified facts from assumptions.
```
