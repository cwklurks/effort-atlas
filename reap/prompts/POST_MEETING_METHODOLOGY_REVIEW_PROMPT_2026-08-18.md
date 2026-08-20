You are an independent scientific-methodology reviewer. Review the research
question and proposed experiment below. This is a pre-data design review: do not
invent results, do not assume censored answers would have been correct, and do not
recommend making any provider calls. Focus on statistical identifiability,
question-level comparison, censoring, and clear language.

PROJECT MOTIVATION

Reasoning-model benchmarks impose output-token limits. Longer reasoning responses
can hit those limits before producing a final answer and are then scored wrong.
Higher reasoning effort often creates longer responses, so a low token limit can
make greater effort or a longer-reasoning model look less accurate.

MEETING NOTES TO REPRESENT FAITHFULLY

- Compare Model A and Model B on the same benchmark questions.
- Determine, for each question, whether each model was correct and how many output
  tokens it used.
- Determine whether a wrong response exhausted the output limit when the source
  records that fact.
- The focus is not simply which model is more accurate. It is which model is more
  token-efficient at a common performance level.
- Proposed plot: x-axis performance; y-axis token efficiency; show a
  censoring-adjusted and non-adjusted comparison.
- Ask whether we can state how many tokens Model A needs to reach the performance
  of Model B, or vice versa.

CANDIDATE RESEARCH QUESTIONS

Q1, plain language:
"Which reasoning model uses fewer output tokens to reach the same accuracy on the
same questions, after accounting for responses cut off by benchmark token limits?"

Q2, more literal to the proposed curves:
"Across the same benchmark questions, what accuracy-token tradeoff does each
reasoning model achieve, and how does that comparison change after accounting for
responses censored by output-token limits?"

AVAILABLE OBSERVATIONAL DATA

1. MathArena public output datasets:
   - HMMT February 2025: 30 questions.
   - HMMT February 2026: 33 questions.
   - AIME 2026: 30 questions.
   - BRUMO 2025: 30 questions.
   - Per response: problem_idx, exact messages, model/config, attempt index, full
     response, input/output token counts, gold/parsed answer, correct boolean.
   - No provider finish reason or requested output cap. Apparent cap collisions are
     inferred from repeated round-number maxima and near-maximum token clustering.

2. Stanford HELM Capabilities v1.15 GPQA chain-of-thought runs:
   - 446 evaluated rows per archived model run; GPQA has 448 source instances.
   - Archived models: Gemini 3 Pro, Claude Haiku 4.5, GPT-5.1.
   - Per instance: request/configuration, response, correctness, requested max
     tokens, and some output-token information.
   - Gemini has explicit finish reasons: 42/446 are finish_reason="length" and all
     42 scored wrong. The archived Claude and OpenAI finish-reason fields are empty.
   - The current displayed token fields are not comparable across these three
     providers: Gemini's summary output counts are zero, Claude's are hundreds, and
     GPT's are single digits, apparently reflecting different visible/hidden
     reasoning accounting.

Important distinction: a response that was length-stopped and scored wrong is not
automatically a response that would have become correct with more room. Termination
is observed; the counterfactual answer is not. MathArena's cap status is inferred,
not observed.

PROPOSED QUESTION-LEVEL DATA UNIT

Each response row would contain:
benchmark_id, question_id, prompt_hash, model_id, model_config, attempt_id,
correct, output_tokens, requested_output_cap, finish_reason, cap_status
(observed/inferred/unknown), and answer_present.

For models with multiple attempts per question, compute each question's accuracy
as correct attempts / valid attempts and then weight questions equally. A paired
question table would compare Model A and Model B on shared question IDs.

PROPOSED CONTROLLED EXPERIMENT

- Use the same frozen questions and prompt template within a panel.
- Vary model, native reasoning-effort level, and explicit output-token cap.
- Generate replicated independent attempts for every question x effort x cap cell.
- Record termination, token usage, answer presence, grade, model/provider/config,
  and every failed attempt at collection time.
- No fallback answer extraction; a final answer requires an explicit terminator.
- Analyze models/panels separately rather than pooling unlike tokenizers/providers.
- Estimate accuracy and length-stop rates at each effort/cap.
- Use larger-cap runs to observe performance with more room; use a censoring method
  to estimate completion-length distributions, not to fabricate missing answers.
- Proposed graph: x = question-weighted accuracy; y = mean billed output tokens per
  question; each point = model x effort x cap. At a common target accuracy p,
  compare T_A(p)-T_B(p) and T_A(p)/T_B(p), if the curves identify those quantities.
- Show an unadjusted view and a censoring-aware view, but the exact definition of
  the censoring-aware performance-efficiency curve is not yet settled.

REVIEW TASK

Return a concise but rigorous review with these exact sections:

1. VERDICT: Is Q1 or Q2 faithful to the meeting, or should both be replaced?
2. RECOMMENDED ONE-SENTENCE QUESTION.
3. WHAT IS IDENTIFIABLE FROM THE FOUND DATA: separate MathArena, HELM Gemini, and
   HELM Claude/GPT.
4. WHAT REQUIRES THE CONTROLLED EXPERIMENT.
5. PRIMARY ESTIMANDS: give no more than three, with plain definitions and formulas
   only where helpful.
6. GRAPH SPECIFICATION: define both axes, the unit of weighting, what “adjusted”
   can honestly mean, and when T_m(p) is estimable.
7. EXPERIMENT CHANGES: list only changes needed to make the design answer the
   meeting question. Flag cross-tokenizer/provider token-comparability problems.
8. QUESTIONS FOR CHIRAG: no more than five genuine supervisor decisions.
9. RED FLAGS: identify any claim in the proposal that would be misleading or
   statistically unsupported.

Do not praise the proposal generically. Challenge it. When evidence is insufficient,
say exactly what cannot be concluded and what additional design element would make
it answerable.
