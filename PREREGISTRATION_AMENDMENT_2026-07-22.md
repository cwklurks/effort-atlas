# Pre-data amendment: grading length-stopped responses

**Study:** *Thinking Cut Short: Separating Token Starvation from Genuine
Overthinking in Reasoning Models*

**Amendment date:** 2026-07-22

**Timing:** This amendment was made after an independent pre-publication code audit
and before any confirmatory API response or confirmatory outcome existed. The
original preregistration remains unchanged at commit
`bc941bf118516cddafc671fcb9acc4607fd7ea33`. This document supersedes only the
outcome-classification and simple-bound language identified below.

## Reason

The original protocol said that every valid `finish_reason="length"` response would
be retained as wrong. The pre-publication audit found that this conflicts with the
unchanged grader: a response can reach the requested cap after already emitting a
correct, extractable final answer. Forcing such a row to wrong could manufacture a
cap effect. No response data prompted this change.

## Amended scoring rule

- Conventional accuracy uses the unchanged grader's boolean result for every valid
  response, regardless of finish reason.
- `finish_reason="length"` is a termination property, not a grade.
- A **token-starved/no-answer row** requires both
  `finish_reason="length"` and `extracted_answer_present=false`.
- Length-stopped rows with an extractable answer retain their grader result and are
  reported separately.
- A row with `correct=true` and `extracted_answer_present=false` is internally
  inconsistent and is excluded with a machine-readable validation reason.

Every cell will therefore report at least four distinct quantities: conventional
accuracy, all length stops, unanswered length stops, and length stops that contain
an extractable answer. Empty extracted answers are also counted across all finish
reasons.

## Amended bound and rescue language

Let `n` be valid responses, `k` responses graded correct, and `u` unanswered length
stops. The deliberately narrow descriptive bound is
`[k/n, (k+u)/n]`. Its upper endpoint asks how high capped-endpoint accuracy could be
if every no-answer length stop were answerable correctly with adequate room. It is
not a bound on all possible counterfactual changes under a larger cap, because an
independent larger-cap generation can also change an already extractable answer.

A primary **answer rescue** is an item-effort pair whose smaller-cap response is an
unanswered length stop and whose larger-cap response ends normally and is correct.
A smaller-cap length stop with an extractable wrong answer followed by a correct
larger-cap response is reported as a separate grade transition, not as evidence that
the smaller-cap endpoint failed to produce an answer.

The original effort-by-allowance interaction, model panels, item set, prompts, gold
labels, grader, schedule order, budget, and stopping rules are unchanged. The
analysis will report both the original all-length-stop mechanism measure and the
narrower unanswered-length-stop measure.
