# Inkling length pilot — preflight document

**Date:** 2026-08-28 · **Status:** DRAFT — awaiting the two HUMAN-REQUIRED readings in §4
and Chirag's written approval (gate 2). **This document authorizes nothing.**
`pilot.enabled` stays `false`; live execution is human-initiated only (AGENTS.md
safeguard 2). Compiled from `reap/23_POST_MEETING_REVIEW_2026-08-23.md` §6–7,
`reap/26_PILOT_HARNESS_2026-08-26.md`, and `config_pilot_inkling.yaml`.

Note: `config_pilot_inkling.yaml` refers to this document as
`reap/25_INKLING_PILOT_PREFLIGHT.md`; numbers 25–26 were taken by later docs, so it
lives here as 27. Update that comment line when this file is accepted.

---

## 1. Purpose and estimand

Exploratory length pilot on one model (Inkling), labeled exploratory everywhere and
never pooled with confirmatory estimates. Question: the distribution of response
lengths at a deliberately high output allowance (32,000 tokens), and the post-hoc
truncation rate P(length ≥ c) per dataset for c ∈ {4,096, 8,000, 14,096, 16,000,
20,000} — exactly identified for c ≤ 32,000. Correctness is ignored on this pass;
strict-terminator presence is still recorded per response (costs nothing, no fallback
extraction ever). 32k-capped rows are kept, labeled `finish_reason="length"`, and
counted — never imputed or dropped. Medians reported only if below 32k; no means if
any row is censored.

## 2. Protocol (frozen for this pilot once approved)

- One pinned route, one explicit effort level (`medium`; a second level is decision 4),
  `max_tokens=32000` explicit on every request, sampling pinned.
- **One attempt per item, zero retries, fallbacks disabled, fresh cache identity**
  (`max_retries: 0` in config).
- Append-only hash-chained attempt ledger; requested cap, finish reason, token usage,
  latency, provider metadata, and receipt info recorded at collection time.
- Items: 200 per dataset × 5 datasets (mmlu_pro, gpqa_main, ifeval, wildbench_v2,
  omni_math) = 1,000 requests, `pilot-wrapper-v1`, wrapper/request seed 20260830.
- Responses land gitignored in `results_pilot/inkling_together/`; no prompt or
  response text in the ledger or any committed artifact; GPQA text only from
  `capabilities/restricted_local/`.

## 3. Route (Chirag decision 1)

**Proposed: OpenRouter → Together.** Already cap-semantics-audited in July
(CAP_SEMANTICS, `config_cap_inkling.yaml` pattern): `only: [together]`,
`allow_fallbacks: false`, `require_parameters: true`, `max_retries: 0`. Pool is
< $100, which the worst case exceeds — hence the staged, ceiling-gated run in §4.

**Tinker: blocked, not waived.** Pinned SDK 0.25.0 is proven to resubmit after the
429 sentinel, violating the one-submission rule (safeguard 8). The Tinker changelog
for SDK 0.21.0 claims sampling requests keep a stable request ID across retries and
are idempotent on the backend — **UNVERIFIED vendor claim, no billing evidence.**
What would settle it: one human-run ~1k-token sampling request with the receipt
showing exactly one billed sample, ideally under a forced retry. Also confirm the
0.25.0 pin against PyPI — the changelog's newest listed entry was 0.24.1
(2026-08-06) at last check. Open facts if Tinker is ever used: prefill billing on
sampling, exact `stop_reason` vocabulary, whether the 32k cap is
reasoning-inclusive on that route, per-response billing join.

Question to Chirag as posed in reap/23 §7: Tinker credits ($5,000 pool,
$4.68/M sample tokens) with a one-submission proof first or a human-in-the-loop
submission process — or OpenRouter/Together now with the staged budget below.

## 4. Budget and cost model

Dry-run table (config prices — **July figures, re-pin below before approval**;
$1.00/M in, $4.05/M out; expected 900 input tokens and ~5,000 output tokens per
item at `medium`):

| Dataset | Items | Expected $ | Worst case $ |
|---|---:|---:|---:|
| mmlu_pro | 200 | 4.09 | 25.96 |
| gpqa_main | 200 | 4.10 | 25.97 |
| ifeval | 200 | 4.06 | 25.93 |
| wildbench_v2 | 200 | 4.47 | 26.34 |
| omni_math | 200 | 4.08 | 25.95 |
| **Total** | 1,000 | **20.80** | **130.15** |

Enforcement (implemented and tested offline, see gate 5): before every call, the
runner checks ledgered spend + the worst case of that call against both the
per-dataset ceiling (**$30.00**) and the total ceiling; it halts the stage the
moment a ceiling would be crossed. Circuit breaker: 5 consecutive errors. A
receipt-vs-prediction mismatch > 20% is an automatic stop
(`receipt_mismatch_stop_fraction: 0.20`). The run is staged per dataset: run one
dataset, reconcile receipts against predicted spend, then proceed.

**HUMAN-REQUIRED before approval (config `budget:` block):**

| Field | Value | Source |
|---|---|---|
| `balance_verified_usd` | ____ | OpenRouter account page, read directly |
| `balance_verified_on` | ____ (ISO date) | same reading |
| Re-pinned prices, with date | in $____/M · out $____/M | provider pricing page on that date |
| `total_ceiling_usd` | ____ | rule: balance − $10.00 reserve, and ≥ staged need |
| Config mock dry-run by a human | done / not done | gate 3 requirement |

## 5. Selection rule (Chirag decision 2)

Both candidate rules are committed, deterministic, and content-free:

- `capabilities/selections/selection_first200_v1.json` — literal first 200 rows per
  dataset by `source_row_index` (the meeting's literal instruction).
- `capabilities/selections/selection_stratified200_seed20260830_v1.json` — seeded,
  proportional across a per-dataset stratum, largest-remainder rounding, exactly 200.

Evidence that literal first-200 is category-skewed on three of five datasets:

| Dataset | First-200 rule | Proportional rule |
|---|---|---|
| MMLU-Pro | 200 of 200 rows are `business` (14 categories exist) | proportional across categories |
| WildBench v2 | 0 Coding & Debugging, 0 Creative Writing | 33 and 28 respectively |
| Omni-MATH | Applied Mathematics 4, Number Theory 47 | 33 and 27 |
| GPQA, IFEval | effectively unordered — both rules similar | — |

**Proposed: the stratified rule.** A first-200 run measures one discipline's length
distribution on MMLU-Pro, not the benchmark's. This deviates from the literal
"first 200" instruction, so it requires Chirag's sign-off either way. Whichever rule
is chosen is frozen in §8 and the selection file named in the config.

## 6. Remaining decisions (Chirag; from reap/23 §7)

3. **WildBench scope:** multi-turn, no gold answer. Include with the recorded
   conversation-serialization rule (wrapper sends turns as chat messages), or drop
   to 4 datasets? Changes the ~1,000-request count and the claim surface.
4. **Effort level(s):** one (`medium`, pure length baseline) or two (e.g. medium +
   max at 100 items each — same budget, adds the effort–length signal).
5. **Written amendment/appendix** noting the pilot as a preregistered-exploratory
   addition, or keep it informal.

## 7. Stop/go gates — status as of 2026-08-28

| # | Gate (reap/23 §6) | Status | Evidence |
|---|---|---|---|
| 1 | Normalized JSONLs pass validation | **CLOSED** | `capabilities/validate.py` PASS (0 hash failures, 5/5 datasets), re-run 2026-08-25; wired into `verify_offline.sh` in commit `3aae500` |
| 2 | Preflight doc + cost model approved by Chirag in writing | OPEN | this document |
| 3 | Route gates: balance read, prices re-pinned, human mock dry-run of config (OpenRouter) · one-submission proof or explicit waiver (Tinker) | OPEN | §4 blanks; Tinker §3 |
| 4 | Selection rule decided and frozen | OPEN | §5, decision 2 |
| 5 | Ledger + ceiling enforcement tested offline (simulated overrun actually halts) | **CLOSED** | `tests/test_pilot.py::CeilingTests::test_run_halts_on_simulated_overrun_and_ledger_verifies` (halts before the 4th call, exit 3, ledger verifies); 1,000-item mock run 2026-08-26: 1,000 ledger events, `ledger_verified: true`, fabricated $20.59 vs $20.80 expectation |

The `--live` path refuses to run and enumerates the open gates (exit 2) until all
five are closed.

## 8. Approval record (fill on approval; nothing runs before this is complete)

```
Approved by:            ____________________  (in writing; link or quote)
Date:                   ____________________
Route:                  openrouter_together / tinker (circle one)
Selection rule frozen:  first200_v1 / stratified200_seed20260830_v1
WildBench:              included / dropped
Effort level(s):        medium / medium+max@100
Amendment/appendix:     yes / no
```

After approval, a human fills the config `budget:` fields, sets
`preflight_approved_by`, and flips `pilot.enabled` — agents never do.

## 9. Provenance

- Protocol, cost bound, gates, decisions: `reap/23_POST_MEETING_REVIEW_2026-08-23.md` §6–7.
- Harness, offline gate-5 evidence, dry-run table, skew evidence:
  `reap/26_PILOT_HARNESS_2026-08-26.md`; `tests/test_pilot.py` (18 offline tests).
- Config facts: `config_pilot_inkling.yaml` (uncommitted as of this writing).
- Gate-1 evidence: `reap/25_STATUS_REVIEW_2026-08-25.md` §2 item 1; commit `3aae500`.
- Drafted 2026-08-28 by Claude at Connor's direction; every number above traces to
  one of the files listed here. Nothing in this document was newly measured, and no
  provider call of any kind was made in preparing it.
