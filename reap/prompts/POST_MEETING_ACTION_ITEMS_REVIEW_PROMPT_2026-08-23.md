# Post-meeting action-items review prompt

You are an independent senior reviewer helping plan the next stage of an ML-evaluation research project called **effort-atlas / REAP**, for a paper provisionally titled *Thinking Cut Short*. Read the full context below before recommending anything. Your job is to determine what Connor should do next after his latest meeting with Chirag, correct any misunderstandings in the meeting notes, and turn the assigned work into a small number of verifiable deliverables.

Do not merely agree with the action list. Separate verified facts from meeting interpretations, identify contradictions, and explain corrections in plain language. Prefer original benchmark sources, pinned revisions, source code, and raw provider metadata over summaries produced by Codex or another model. If you can browse, use primary sources. If you cannot verify a claim, label it **UNVERIFIED** and say exactly what evidence would settle it. Do not recommend a paid model call until every stated safety gate is satisfied.

## People, collaboration, and goal

Connor Klann is a high-school student and the first author. Chirag Nagpal is the statistical supervisor and senior coauthor. Chirag's survival-analysis work is the paper's statistical base; Connor owns the benchmark audit, controlled experiments, data pipeline, and empirical sections. Connor's parents have Chirag's contact information. They tentatively agreed to weekly 30-minute Sunday meetings. Connor still needs to create the Slack workspace and should contact his teacher only after his class assignment is known.

The scientific problem is that benchmark APIs impose output-token limits. A reasoning model can reach the limit before writing its final answer. The benchmark then marks the response wrong. Higher reasoning effort often produces longer responses, so it may hit the limit more often. This can make “thinking harder” appear to reduce accuracy even if the model did not become less capable.

The current simple research question is:

> When two models reach similar accuracy on the same questions, how many comparably measured output tokens does each need, and how does accounting for responses cut off by an output limit change that comparison?

The broader controlled design varies both native reasoning effort and output allowance. The key within-model question is whether raising the allowance reduces unanswered length stops and changes the apparent effort-versus-accuracy relationship. Chirag's censoring analysis concerns response lengths: when a response is stopped at allowance C, its uncensored natural length is only known to exceed C. It does not impute the missing answer. Correctness rescue requires new independent runs with more room.

## Funding and non-negotiable safeguards

The project has three separate funding pools: $5,000 in Tinker research credits, about $200 in OpenAI credit supplied by Chirag, and less than $100 for OpenRouter. These pools are platform-specific and must not be mixed in accounting.

No REAP confirmatory call has been made. The following rules remain binding:

1. Do not edit frozen preregistration files or frozen confirmatory artifacts.
2. Do not make paid research, smoke, or provider-probe calls as part of this review.
3. Set `max_tokens` explicitly on every ordinary request and set reasoning effort explicitly where supported.
4. Record requested allowance, termination reason, token usage, latency, provider metadata, and receipt information at collection time.
5. Do not use fallback answer extraction. An answer counts only when the configured explicit `Final answer: <answer>` terminator is present.
6. Keep exploratory, smoke, synthetic, and confirmatory data separate.
7. Pin source revisions and providers, disable provider fallbacks, use zero retries on billed generation calls, and preserve every attempt.
8. A known Tinker SDK version could resubmit a billed request. No paid Tinker work should begin until one-submission behavior is demonstrated or a safe route is approved.

Grader v2 and a pre-data analysis implementation have been written and reviewed on branches, but the accepted integrated baseline, frozen REAP preregistration, final runner, and executable budget gates are not all complete. Do not treat the existence of code on a branch as permission to collect data.

## Earlier evidence and work completed

The project began with a pipeline failure: a Tinker route silently used a 4,096-token default after the intended parameter was ignored. Seventy-eight archived responses ended at 4,096 without an explicit final answer, but an old grader's fallback scavenged stray numbers and reported no parse failures. This produced a false effort-decline result and motivated the strict grader and collection safeguards.

An exploratory AIME pilot later used a 20,000-token allowance. Medium effort scored 25/30 with four wall hits; maximum effort scored 21/30 with nine wall hits. All 13 wall-hit responses lacked answers. One separate exploratory rescue finished correctly at 38,603 tokens. These results are exploratory and must not be pooled with future confirmatory estimates.

A zero-cost observational study examined public MathArena and HELM archives. MathArena included HMMT 2025, HMMT 2026, AIME 2026, and BRUMO 2025, totaling 123 competition-math questions. The archives provide per-question source-native grades and reported output-token counts, but they do not provide requested caps or finish reasons. Their “at cap” classifications are therefore inferred from token-count clustering rather than directly observed.

The historical `observational/RESULTS.md` says 16 of 17 selected MathArena model-dataset groups had zero accuracy at the inferred cap. A later recomputation used 15 of 17, with Phi-4-reasoning-plus at 2.6% and s1.1-32B at 11.1%. This disagreement is unresolved. Do not repeat either denominator as final until the exact input revisions, group inclusion rule, and pipeline output are reconciled.

An exact-source audit produced a **derived** file called `observational/benchmark_question_capabilities.jsonl`. It contains sanitized question-by-model metadata. It is not an original HELM file. This distinction caused confusion during the meeting and must stay explicit.

## What the original HELM files actually establish

The reviewed HELM Capabilities v1.15 GPQA run uses two original public files per model:

- `scenario_state.json`: request settings, model identifier, requested `max_tokens`, and completion finish reason.
- `display_predictions.json`: `instance_id`, HELM's source-native correctness statistic, and provider-dependent token statistics.

GPQA has 448 source rows. HELM assigns two fixed rows to its training split and evaluates the other 446. Gemini 3 Pro Preview, Claude Haiku 4.5, and GPT-5.1 have the same 446 evaluated IDs. The original Claude and GPT archive files do exist; they were not absent. Their finish-reason fields are blank, which is different from proving that no response hit its limit.

For Gemini 3 Pro Preview, every request records `max_tokens=14096`. The original `scenario_state.json` contains 42 `finish_reason="length"` rows and 404 `finish_reason="stop"` rows. HELM's source-native grade marks all 42 length-stopped rows wrong. In the companion `display_predictions.json`, Gemini's `num_output_tokens` value is zero for all rows and is unusable. Claude's and GPT's archived token values follow visibly different accounting systems, so the three providers cannot be placed on one honest token-efficiency axis.

For example, joining the two original files on `instance_id="id119"` gives:

- `scenario_state.json`: model `google/gemini-3-pro-preview`, requested allowance 14,096, `prompt_truncated=false`, and `finish_reason="length"`.
- `display_predictions.json`: `chain_of_thought_correctness=0.0` and unusable `num_output_tokens=0.0`.

The field `prompt_truncated` is not an error. It indicates whether HELM truncated the **input prompt** before sending it. Response-limit termination is recorded separately by `finish_reason="length"`. GPQA question text, choices, gold answers, and archived model responses appear as encrypted placeholders in the public HELM outputs because the content is restricted. The readable response prefix is therefore not available from the public archive, and no continuation beyond the cap ever existed.

The safe conclusion is: in this pinned HELM run, 42 Gemini responses were explicitly labeled length-stopped and all were scored wrong. This does not prove that extra room would have made any particular response correct. Also clarify the wording “only one confirmed case”: there is one reviewed **archive/model run with usable termination labels**, containing 42 length-stopped responses, not one individual length-stop event.

“Censoring” and “token exhaustion” are not competing explanations. A `length` stop is the operational event. For length analysis, that same observation is right-censored because its natural completion length is unknown beyond the allowance.

## Meeting transcript supplied by Connor, included verbatim

Treat the following as the primary record of what happened in the meeting and what Connor understood Chirag to have assigned. Direct quotations are evidence of what was said; technical interpretations in the record still require verification against original sources.

### Action Items — Full Detail with Context

#### 1. Rebuild the dataset pipeline from original sources

**What happened that triggered this:**
- Your mentor repeatedly asked "where is this coming from?" and you couldn't cleanly trace your data. Your `benchmark_question_capabilities.jsonl` turned out to be pulled from **your own repo/branch** — a file Codex had synthesized from the official benchmark, not the raw source.
- The two underlying Helm files (`scenario_state.json` and `display_predictions.json`) had problems:
  - **Output tokens showed 0 everywhere** in the right-hand file — clearly wrong, since token counts should vary per prompt
  - **Text responses said "encrypted text" everywhere**, making it impossible to inspect actual generations
  - A field said **"prompt truncated"** when it should have been about response truncation — you flagged this yourself as weird ("it shouldn't say that") and never resolved it
  - Files existed for Gemini, but the equivalent JSONLs for the other models were missing/unfound
- The Helm data traces to Stanford's **CRFM Helm Public** repo, but you never confirmed the exact generating repo or the paper/blog passage documenting the token-exhaustion error — when asked to show "the row exactly in the paper," you couldn't find it.

**The exact task:**
- For **MMLU Pro (~12,000), GPQA, IFEval, WildBench, OmniMath** — start with MMLU Pro, then descending order by prompt count
- Pull the **complete original prompt set** for each (mentor was explicit: "get ALL the prompts," not just 200 — the 200 is only what you *run*)
- One JSONL per dataset, one row per prompt, exact prompt text "to the last T"
- **Ground truth answers must be paired with each prompt** (e.g., the correct choice in a 4-option MCQ). The why, which you paraphrased back: accuracy can only be estimated relative to output length if you know the right answer
- **Every file gets its source URL documented** at the point where you store it
- Codex is allowed as a helper, but you must independently verify where files originate — "you should know exactly what the model's trying to do, where it's getting its stuff from"

#### 2. Google Doc as single workspace

- Mentor explicitly said: "don't use Codex for everything... just open a new Google Doc"
- Contents required:
  - Screenshot of the benchmark list page (the one showing the 5 datasets and their sizes)
  - The link to that website
  - Source links for every dataset as you collect them
- Intent: **one doc that has everything**, replacing the scattered Codex chats, JSONs, and screenshots that made this meeting hard

#### 3. The Inkling experiment — full design

**Setup:**
- Model: **Inkling** (chosen because you have credits there; any accessible model works)
- Prompts: **first 200 per dataset × 5 datasets = ~1,000 total** (200 is arbitrary, purely to protect your credits)
- **Max output token cap: 32,000** — deliberately high so nothing gets truncated by the cap itself

**Analysis:**
- **Ignore correctness on this first pass** — "let's not even bother whether it gets the answer right or not"
- Measure the **distribution of response lengths**
- Then run **post-hoc simulated truncation**: "if the maximum token cap was 16,000, all these responses would have been truncated" — this estimates truncation rates at realistic caps without new API spend

**Why this matters (the research question):**
- GPQA/Helm caps outputs at **14,096 tokens**. Existing published benchmarks show "output limit reached" flags (up to 42 instances for Gemini 3 Pro Preview in Helm/GPQA), but **only one confirmed token-exhaustion case exists** across everything you found
- The unresolved question your experiment answers: are those cutoffs **censoring** or genuine token exhaustion? You confirmed you believe models *will* exceed 14,000 tokens on these benchmarks
- This gives a **scientifically defensible baseline** before the paper makes any claims

#### 4. Communication & logistics

- **Slack updates:** ongoing progress reports; ping mentor when files are ready — "whenever you have this, let me know and we can take it from there"
- **Teacher email:** blocked until you know your teacher assignment (~1.5 weeks out). Once the class list is confirmed, share your mentor's email with your teacher
- **Parents:** ✓ done — they have the mentor's email if they need to make contact
- **Recurring check-in:** weekly 30 minutes, **Sundays** agreed (mentor offered a weekday if you prefer — your call), goal is "constant momentum"

#### Loose threads worth closing proactively

These weren't formally assigned but came up unresolved:
- The **ID 119** case you were tracing (truncated response + censoring signal) — you never located the correlating file with model names
- Whether OmniMath's models/censoring examples actually differ — you'd claimed fewer models and no censoring, but hadn't built a prompt/response table for it
- The exact **Helm blog post or paper citation** for the 4/4 token-limit error — needed for the paper's claims

## Corrections and cautions to apply when interpreting the transcript

1. `benchmark_question_capabilities.jsonl` is a Codex-produced sanitized derivative. The original HELM evidence comes from `scenario_state.json` and `display_predictions.json`, joined by `instance_id`.
2. `prompt_truncated` correctly refers to truncation of the input prompt. Response-limit termination appears separately as `finish_reason="length"`.
3. The original HELM Claude and GPT companion archives exist. Their finish labels are blank, so their termination status is unknown.
4. The 14,096 value is a requested maximum, not a verified Gemini output-token count. Gemini's archived token count is zero and unusable.
5. The safe “one confirmed case” interpretation is one reviewed archive/model run with usable labels, containing 42 length stops. It is not one individual response.
6. Token exhaustion is the observed stopping event; censoring describes the missing natural length after that stop. They are not alternatives.
7. A 32,000-token Inkling allowance is not guaranteed to be uncensored. Rows that hit it remain censored. Post-hoc 16,000-token estimates are cleanest among responses known to complete below 32,000.
8. “Exact prompt” must distinguish the source benchmark item from the later model-facing wrapper. GPQA access conditions forbid publishing its raw content in the repository or an unrestricted shared document.
9. The proposed Inkling length study is an exploratory pilot unless Chirag and Connor explicitly integrate it into a new preregistration. It does not silently replace the fuller effort-by-allowance design.
10. The 15-of-17 versus 16-of-17 observational result remains unresolved and needs an input-and-inclusion-rule reconciliation.

## What I want you to produce

Return the following, in this order:

1. **Fact audit:** a table classifying each major meeting statement as verified, corrected, ambiguous, or unsafe. Cite the evidence given above and primary sources you verify. Include the HELM two-file distinction, `prompt_truncated` semantics, the 42-versus-one wording, and the 15/16 discrepancy.
2. **Recommended scientific framing:** one precise technical problem statement and one plain-language version. Explain what the first Inkling experiment can and cannot establish.
3. **Prioritized execution plan:** a dependency-ordered plan for the next seven days. For each step give the deliverable, owner, estimated effort, prerequisite, completion check, and whether Chirag must approve it.
4. **Dataset provenance plan:** one row for each of MMLU-Pro, GPQA, IFEval, WildBench, and OmniMath with the official source, pinned revision strategy, license/access risk, expected count, prompt field, gold/grading field, and validation tests. Mark anything not verified.
5. **Normalized JSONL contract:** propose the smallest schema that preserves source identity, exact source prompt, choices where applicable, gold/grading target, dataset split, license policy, source URL and revision, source-row hash, and later provider-specific wrapper separately. Include handling for restricted text without leaking it.
6. **Inkling pilot preflight:** specify a safe exploratory protocol, cost-bound method, treatment of 32,000-capped responses, post-hoc truncation estimates, reproducible 200-item selection, and stop/go gates. State every fact that still requires Tinker documentation or a human-run smoke test.
7. **Questions for Chirag:** only the decisions Connor cannot safely make alone. Keep this list short and explain why each decision matters.
8. **Communication drafts:** a brief Slack progress update for Chirag and a one-paragraph description of what belongs in the Google Doc.
9. **Immediate next action:** end with the single task Connor should start first, the exact artifact it should produce, and the test that proves it is complete.

Use direct, simple technical language. Avoid generic encouragement, filler, and inflated claims. Do not treat meeting notes as a preregistration. Do not recommend collecting data merely because credits exist. The final plan should let Connor explain where every row came from and what every field means without needing an AI system open during the next meeting.
