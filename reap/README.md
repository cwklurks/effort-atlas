# REAP — Replicated Effort–Allowance Program

**Program of:** effort-atlas (github.com/cwklurks/effort-atlas) · **Paper:** *Thinking Cut Short* (Klann & Nagpal)
**Status:** Design/integration phase. No confirmatory calls under this program have been made. Funded 2026-08.
**Supersedes:** the Phase I confirmatory protocol (PREREGISTRATION.md, 2026-07-22) — Phase I remains the frozen record of the pre-funding design; REAP will be preregistered separately before its first confirmatory call.

## The question

When higher native reasoning effort lowers benchmark accuracy, how much of the decline is completed responses giving worse answers, and how much is longer responses hitting the output allowance before an answer exists? REAP measures this with replication (n ≥ 8–20 per cell), effort × allowance dose-response grids, and a direct validation of the censoring framework: length distributions observed at large allowances must predict truncation rates measured at small ones.

## What changed since Phase I

- **Funding:** $5,000 Tinker Research Grant (Thinking Machines credits) + ~$200 OpenAI (C. Nagpal) + <$100 personal (OpenRouter). Three platform-scoped pools; see `02_BUDGET_AND_COSTS.md`.
- **Replication:** the one-generation-per-cell limitation is retired.
- **Scope:** multiple models, graded effort sweeps, cap grids, additional datasets (`04_DATASET_CANDIDATES.md`).
- **Positioning:** closest prior work identified 2026-08 (Coupling Tax, arXiv:2605.07686) — see `05_RELATED_WORK_ALERT.md`. KM-on-censored-CoT is no longer claimable as novel; the effort axis, replication, and cap-invariance validation are.

## Governance (carried from Phase I, non-negotiable)

1. No confirmatory paid call before the REAP preregistration is committed (`06_PREREG_V2_SKELETON.md` → frozen document + hashes).
2. `max_tokens` explicitly set on every call, on every platform. (Tinker's SDK default is `None` with an undocumented server default — the Phase I bug's mechanism. The OpenAI-compat route also silently defaults effort to 0.9.)
3. Termination logged at collection time: Tinker `stop_reason`, OpenAI `incomplete_details.reason`, OpenRouter `finish_reason` + generation receipts. Truncation is unrecoverable from text after the fact.
4. Grading: termination is never a grade. `finish_reason="length"` + no extractable answer = token-starved/no-answer row. Answer extraction requires an explicit `Final answer:` terminator; no last-number fallbacks.
5. Per-pool spending ceilings with cumulative usage checks and kill thresholds; exploratory work labeled exploratory everywhere.

## Documents

| File | Contents |
|---|---|
| `01_EXPERIMENT_OUTLINE_v2.md` | The design: panels, arms, estimands — for Chirag's review |
| `02_BUDGET_AND_COSTS.md` | Pools, verified prices, cost model, allocation, reserves |
| `03_WORKPLAN.md` | Concrete next steps, owners, weeks |
| `04_DATASET_CANDIDATES.md` | Ranked dataset slate with evidence and grader risks |
| `05_RELATED_WORK_ALERT.md` | Coupling Tax finding and repositioning (read first) |
| `06_PREREG_V2_SKELETON.md` | Superseding preregistration, to be completed and frozen |
| `10_PHASE_GATE_PLAN_2026-08-08.md` | Current serial gates, development-model routing, and completion criteria |
| `11_PHASE3_DECISION_PACKET_2026-08-08.md` | Independently reviewed advisory D01-D15 decision packet |
| `12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md` | Non-frozen current positions, all alternatives, model/dataset research, and open questions; authorizes no call |
| [`status/index.html`](status/index.html) | Generated phase dashboard, safety counters, branch ownership, and verification ledger |

## Phase dashboard

The status dashboard is a generated, self-contained HTML file. Update
`status/phase_status.json`, run `python scripts/render_phase_status.py`, and commit
both the source data and rendered `status/index.html` at every phase checkpoint.
The canonical offline suite fails when the rendered page is stale. The dashboard
reports project state; it never authorizes a paid or confirmatory call.
