# Adversarial review — PR #1 (codex/ecosystem-audit @ 5c31b53)

**Reviewer:** Claude (Opus red-team, per playbook Prompt 4) · **Date:** 2026-08-07
**Verdict:** MERGE-AFTER-FIXES. No fabrication found — all 67 static receipts verified byte-exact at pinned commits; both headline pipelines re-executed against fresh upstream source with 0 mismatches; timeline blobs verified; 27 tests pass; verifier passes on a clean clone. The defects are in metric framing, applicability rules, and two entry-point choices. All fixable without recollecting data.

## Critical findings

**F-1. The "Inspect Evals AIME 37.4%" headline is 93% synthetic.** Real truncated generations: **0/7** answers returned (5 of the 7 applicable real rows have empty text). All 40 "answers" and all 20 "accidental corrects" come from Codex-authored synthetic strings that literally print the gold answer. Controls = 6 replicates of ONE problem. Must not be cited.

**F-2. The "LiveBench 91.2%" headline runs a scorer LiveBench never dispatches for this data.** `proof_rearrangement_process_results` is dispatched only for imo/usamo step-ordering golds; Codex fed it integer competition answers. The scorer actually in path for AIME-shaped data — `aime_process_results`, gold-in-last-50-characters, *more* dangerous — was statically audited (F031) but never executed.

**F-3. Six of seven "control_disqualified" verdicts are artifacts, not harness failures.** Nearly all control failures trace to three symbolic golds Codex's applicability rule wrongly admitted, plus an adapter bug (lighteval gold marshaling — its own math_verify adapter handles the same case correctly). On a uniform integer-gold control set (n=28): helm 28/28, lighteval 28/28, math-verify 28/28, matharena 28/28 — **five more pipelines become headline-eligible under a consistent rule.** Classification: codex-fault 3 (incl. OpenCompass env), fixture-fault 3, mixed 2, outright harness-fault 0.

**F-4. GAPS.md claims lm-eval has no AIME task — false at the pinned commit, contradicted by the PR's own timeline (T002).** The omission deletes the paper's best single finding: `lm_eval/tasks/aime/utils.py` swallows the mid-box AssertionError and falls back to a $-span — exactly the pathology the paper documents, in AIME's own scoring path.

**F-5. "OpenCompass import_failed" = missing `rouge-score` in Codex's own requirements file.** An environment bug presented as a study status.

## The corrected real-data story (stronger than the broken headline)

Real truncated generations (n=131), per pipeline: last-number-style extractors (lm-eval, lighteval, math-verify, matharena — **identical fixture sets, one measurement not four**) return an "answer" on **111/131 = 84.7%**; inspect_ai 77.1%; **HELM only 17.6%** — because HELM's extractor requires a complete `\boxed{}`, making it near truncation-safe. **Accidental-correct on real data is 0–2.3% across all pipelines** — the scary "scored correct" rates in the draft table are synthetic artifacts. Stratification Codex skipped (computed in review): 26/131 truncated texts contain a complete box before the cut; for the other 105, any returned answer is necessarily fallback-scraped.

The defensible ecosystem claim: *most shipped extractors manufacture an answer from ~85% of truncated reasoning traces (harmless-looking but it silently converts "didn't finish" into "wrong," and occasionally into "right"); requiring a completed answer marker, as HELM does, drops that to ~18%.* That's a better result than the inflated one — and it's real.

## Blocking fixes (feed to Codex as round 2)

1. Rebuild the headline table real-only, explicit n, inspect_evals marked insufficient_power (n=7, 5 empty, controls n_eff=1). Synthetic results reported separately as constructed probes, never blended.
2. Add `livebench/aime_last50` pipeline (`aime_process_results`); demote olympiad_expression (wrong dispatch for this data).
3. Fix lighteval adapter gold marshaling to match math_verify's; freeze ONE gold schema across all pipelines; re-run the control gate; publish corrected eligibility.
4. Retract the lm-eval-AIME "not found" claim; add aime.yaml (32768) and utils.py (AssertionError swallow → $-span) findings; add an lm-eval AIME executable pipeline.
5. Add `rouge-score` to the OpenCompass lock (or use the _locked_namespace bypass); re-run.
6. Delete `fabrication_pct` rows from pipeline_metrics.csv; add `answer_is_numeric` column (6 of 111 lm-eval "answers" contain no digit — `$$`, `$,`, `$.`).
7. Add task-path call-graph receipts (registration/dispatch site) for every executed pipeline; re-check eligibility.
8. Add `pre_truncation_answer_present` stratification to real rows (26 vs 105).
Non-blocking: pin a livebench env; stop injecting output_tokens=4096 into synthetic rows undisclosed; split timeline "remediation" into cap_raised/cap_removed/cap_lowered; load gsm8k constants from the task YAML instead of transcribing; reword "2,950 rows verified" (2,655 executed, 295 import_failed placeholders); add a limitations block above the results table.

## Citable today

All 67 Phase-1 static findings (verified); Phase-3 timeline dates/settings (relabel "remediation" first); trunccheck as an artifact; the corrected real-only rates above. **Not citable:** 37.4%, 91.2%, 18.7% accidental-correct, any fabrication_pct value, "7 of 10 failed controls."
