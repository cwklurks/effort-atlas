# PROJECT_BRIEF — canonical state of REAP / Thinking Cut Short

**Last updated: 2026-08-10. Update this file whenever project state changes; it is the single source of truth for Claude Project chats.**

## People and roles

- **Connor Klann** — high school student (entering grade 11), independent researcher, **first author**. Owns: harness, audits, runs, empirical sections, datasets/hyperparameters. ~8–12 h/wk while school is out.
- **Chirag Nagpal** — statistician (survival analysis), CMU PhD, industry researcher. **Supervisor / senior author.** Owns: censoring framework (his monograph is the paper's base), Helpfulness semi-synthetic experiment, statistical review, the "scope of the formalism" boundary subsection. High availability for ~1 month (new job after). Weekly 30-min calls; Slack channel for async; contributed ~$200 OpenAI credits.

## The paper in one paragraph

Benchmarks impose output-token walls. Walls delete final answers mid-reasoning; graders score deletions as wrong; higher native effort writes longer and hits walls more — so a wall can masquerade as "thinking more makes models worse." The paper (a) treats truncated lengths as right-censored and analyzes them honestly (Chirag's half — corrected KM estimator, restricted means, semi-synthetic validation on the Helpfulness corpus), and (b) tests declines interventionally by raising the wall and watching the effort gap (Connor's half — replicated effort × allowance factorials). The seam: a cut response has a hidden true length but no hidden answer, so lengths get repaired by counting and correctness only by rerunning. Recommendation to the field: report your effective wall, finish reasons, and answer-presence before calling any decline "overthinking."

## History (compressed)

- Origin bug: Connor sent max_completion_tokens on a Tinker route; endpoint silently ignored it, applied a 4,096 default; **78 responses cut at exactly 4,096**, zero parse errors (grader fallback fabricated extractions), producing a fake "declines with effort" curve. Invalidated, not repaired.
- Pilot (30 AIME-25, Inkling via OpenRouter→Together, 20k cap): medium **25/30 (4 wall-hits)** vs max **21/30 (9 wall-hits)**; all 13 wall-hits unanswered, scored wrong. One exploratory rescue finished correct at 38,603 tokens.
- Cap-semantics audit (4 routes, 2k probes, receipts): 3 cap-inclusive/honest; **Grok/xAI billed 54,969 tokens on a 20,000 request (2.75×)** with no length flag; Inkling's behavior documented nowhere.
- Phase I preregistration committed 2026-07-22 (commit bc941bf) + one dated scoring amendment; $0 confirmatory spend ever made under it.
- Collaboration: Chirag reached out to merge after Connor's cold email; Option A accepted (Connor first author). First working call 2026-08-03: monograph = base, Connor's experiments = dedicated section; weekly calls; venues ACL/NAACL/EMNLP; AI tools accepted for checking/analysis with prose typed by humans.
- **Funding 2026-08-04: $5,000 Tinker Research Grant** (Thinking Machines — the same platform as the origin bug). Total pools: $5k Tinker / ~$200 OpenAI / <$100 OpenRouter. Platform-scoped.

## REAP (Phase II) design summary

The reviewed proposal remains advisory and human-pending; D01-D15 are in
`../11_PHASE3_DECISION_PACKET_2026-08-08.md`, and Connor's current choices,
alternatives, and open questions are recorded in the non-frozen
`../12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md`. Connor supports separate
A/B/C samples with `arm_key`, standard 32K GPT-OSS-120B, a planned shared 30-of-33
HMMT-2026 subset, Terra in principle, and descriptive/bootstrapped primary
statistics. He accepts standard Inkling's recommended effort/cap direction but has
reopened its 30-versus-60 scope and allocation along with the broader Tinker
portfolio, H6 rule, exact prompt, batching, final model roster, and DeepSeek gate.
Arm C remains a panel-specific large-cap reference in the detailed design options.
The original planning maxima ($1,492.1761 P1, $187.0258 P2, $125.8291 P3) remain
auditable alternatives, not approved schedules. Preregistration v2 must freeze
before any confirmatory call.

## Positioning (updated 2026-08)

**Closest prior work: "The Coupling Tax" (arXiv:2605.07686)** — already applies KM to right-censored CoT lengths with budget sweeps and CDF-based accuracy prediction. KM-on-CoT is therefore NOT novel. Surviving contributions: (1) native effort axis (they are binary think/no-think), (2) replication/variance decomposition (they are greedy single-sample), (3) cap-invariance validation (they assume, never test), (4) API reasoning models + route/receipt verification. Supporting anchors: 2506.09250 (Illusion-of-Thinking rebuttal — famous decline was a token-limit artifact), 2506.04210 (Mirage — live overthinking claim not controlling truncation; a target), 2605.16938 (effort = ceiling), 2602.09805 (Kaiser), 2607.21433 (Oladri: AIME 6.6% non-converged vs 90.3%), 2604.21083 (GateScope). Ecosystem evidence: lm-eval DEFAULT_MAX_GEN_TOKS=256 + last-number `group_select: -1` extraction; Tinker's own cookbook sets max_tokens as a function of effort on an AIME prompt; inspect_ai #3582 (truncation invisible in logs).

## Current implementation status and next gates

- The $0 MathArena/HELM observational study is complete and verified; it remains
  exploratory and separate from all future confirmatory estimates.
- Grader v2, Tinker probe tooling, the ecosystem audit, and governance are merged
  to main. The pre-data analysis branch now integrates accepted grader v2, uses
  item-level transition mass rather than replicate-index pairing, and passes the
  mandatory ordinary plus exact-lock Tinker offline suites. Initial review blockers
  in calibration reference accounting and rescue validation were remediated, and
  the final independent re-review passed and PR #3 is merged.
- A direct Fireworks ZDR DeepSeek V4 Flash lane is proposed for bounded mechanical
  development only. It remains disabled and not authorized until the exact
  `store=False`/Chat Completions configuration, served-route checks, separate
  ledger, and $10 cumulative ceiling are approved and committed.
- The advisory Phase-3 decision packet passed independent technical review at
  `2b9b161`, including exact arm/cost recomputation and 19/19 killed contract
  mutations. Connor's 2026-08-10 non-frozen worksheet records his current positions
  and every researched alternative; it authorizes no call.
- The packet corrects two unsafe planning assumptions: standard Tinker GPT-OSS-120B
  is a 32K-context route, and standard Inkling's 64K context cannot hold a literal
  64K output plus a nonempty prompt. Earlier expected-cost sketches are not hard
  budget gates. The proposed exact pre-smoke maxima are $1,492.1761 for P1,
  $187.0258 for P2, and $125.8291 for P3, pending human approval and frozen route
  and price evidence.
- The runner and executable budget gates do not exist yet.
- No paid REAP smoke or confirmatory call has run. Tinker cap semantics, omitted-cap
  cost bounds, sample independence, and OpenAI usage accounting remain unresolved.

Next gates: resolve D03/D04/D06/D09/D11/D12/D13/D15 and obtain Chirag's scientific
signoff on D03-D10; record the final human choices; freeze the scientific design and
fail-closed activation-or-omission rules; implement and red-team the runner; then
allow human-initiated smoke. Connor proposes at most $2 for the Tinker reliability
smoke, but the current SDK still blocks it. Smoke may activate an unchanged frozen
panel or omit it, never silently redesign the study. See
`../10_PHASE_GATE_PLAN_2026-08-08.md`.

## Vocabulary

Censored = cut before its event; the length is a floor. Risk set = still-visible responses at a checkpoint. KM = multiply survival fractions at finish-lengths; 0.453 toy. Restricted mean = area under survival curve to a horizon. Effort slope = D_c = A(high,c) − A(low,c), matching the frozen Phase-I definition; the exploratory pilot's low-cap slope was −13.3 percentage points. Interaction I = D_large − D_small. Token-starved/no-answer = length termination ∧ no extractable answer. Completed negative scaling = decline that survives with room to finish. Cap-inclusive/exclusive = whether billed generation respects the requested cap. Semi-synthetic = real corpus, imposed fake wall, kept answer key.
