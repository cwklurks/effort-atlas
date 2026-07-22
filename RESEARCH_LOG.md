# Research log — effort-atlas

## Hypothesis

Inkling's thinking-effort dial buys accuracy at very different exchange rates per
task type. Specifically: reasoning-heavy tasks (competition math) improve
monotonically with effort, while retrieval/extraction tasks plateau at low effort —
meaning a fixed high-effort default wastes most of its tokens on most real queries.

## Hard invariants

- Token counts are provider-reported, never estimated, in any published figure
- Every published accuracy has n and a 95% Wilson interval
- Fixed question sets, fixed seed, full request config stored per row
- Prior art cited; claim is "first public per-domain effort curves for Inkling",
  not "invented adaptive test-time compute"

## Prior art (cite these, don't compete with them)

- s1: Simple test-time scaling / budget forcing — https://arxiv.org/abs/2501.19393
- L1: length-controlled reasoning via RL — https://arxiv.org/abs/2503.04697
- RouteLLM (routing between models; we route one model's native dial) —
  https://arxiv.org/abs/2406.18665
- TML's own effort/performance curves (Terminal Bench 2.1, HLE, IFBench only) —
  https://thinkingmachines.ai/news/introducing-inkling/

## Plan

- **Phase 1 (this week):** text-domain effort curves — math, knowledge, extraction.
  ~50 items × 3 domains × 5 effort levels ≈ 750 calls.
- **Phase 2:** audio (MMAU-style) + charts (CharXiv-style) — does effort help
  perception, or only inference-over-perception?
- **Phase 3:** effort autopilot — small classifier trained on Phase 1/2 rows
  predicts minimum sufficient effort per prompt. Target claim: iso-accuracy with
  the max-effort setting at a fraction of the tokens.

## Status

- 2026-07-15: Repo scaffolded. Pipeline verified end-to-end in mock mode.
- 2026-07-15: Confirmed against Tinker docs — OpenAI-compatible endpoint (beta),
  `reasoning_effort` accepts raw floats in [0,1] via extra_body, and
  `separate_reasoning` isolates CoT into `reasoning_content` (bonus: we can study
  CoT length/style vs effort directly). Harness updated.
  Remaining blockers: Inkling sampler checkpoint path + confirmed pricing.
  Deadline pressure: Tinker sample prices rise ~50% July 17 → sweep by July 16.
- 2026-07-15: Completed the 45-run free Playground pilot with exact efforts
  0.2/0.6/0.99, isolated chats, and web search disabled. Accuracy was 45/45 at
  every setting: easy math and extraction were saturated at effort 0.2, while
  rough UI latency increased at 0.99. This is a ceiling-effect result, not proof
  that effort is generally useless. The Playground raw view exposes no token
  usage, and its image/audio input controls are currently disabled (“coming
  soon”), so publishable token curves and multimodal tests still require API
  access.
- 2026-07-16: API smoke-test setup verified the plain
  `thinkingmachines/Inkling` 64K model ID and current console pricing in
  `config.yaml`, but Tinker's authenticated API rejected the request with HTTP
  402 because the account has no active billing balance. No completion was
  generated, so no model-ID, token-usage, or reasoning-content finding is
  claimed.
- 2026-07-17: The funded real sweep stopped during Phase 1 after the first
  uncached math request in the resume attempt failed on five consecutive
  connection attempts. The harness ended with `RuntimeError: Request failed
  after retries: Connection error.` This was a connection-level failure, not an
  HTTP model, billing, or `reasoning_effort` response. No API work continued
  after the failure.

  The retained partial data has eight unique paid rows. Extraction at effort
  0.6 was correct on 2/2 items (100.0%, n=2) with 23 mean completion tokens.
  Math at effort 0.2 was correct on 4/6 items (66.7%, n=6) with 1,776.3 mean
  completion tokens. A knee cannot be estimated for either domain because each
  domain has observations at only one effort level. In particular, these data
  cannot answer whether AIME accuracy dropped at low effort or where the AIME
  knee lies; they show only 4/6 correct at effort 0.2 with no comparison group.

  Provider-reported usage totaled 10,704 completion tokens and 944 prompt
  tokens. At $4.68 per million completion tokens and $1.87 per million prompt
  tokens, actual spend was $0.051860 against the $8.50 ceiling.

  There were zero refusals, zero empty responses, and zero parse failures
  (`extracted == ""`) in the eight retained rows. One math row had empty
  `reasoning_text` but a non-empty response and valid extracted answer. The
  longest completed latency was 59.83 seconds; the math mean was 31.23 seconds
  and the extraction mean was 1.25 seconds. The failed resume printed retry 1
  through retry 5 and produced no new row.

  The Phase 1 dry-run estimate was $5.07 for 150 math calls. No estimator values
  were hand-adjusted: the extraction smoke averaged 23 tokens at effort 0.6,
  but applying that domain's short-output ratio to the math-oriented estimator
  would not be a valid calibration. The failure left 144/150 planned math rows
  missing. Phase 2 knowledge was not started, so all 150 planned rows are
  missing. Phase 3 extraction was not started, so all 125 planned rows are
  missing apart from the two Phase 0 smoke observations. Phase 4 analysis was
  not run because the sweep had stopped and the partial data cannot support
  effort curves or knees. Failed resume files containing duplicate cached rows
  were preserved under `results/interrupted/` and excluded from spend and
  accuracy calculations.

- 2026-07-19: The funded real sweep completed with 424 unique successful
  domain-item-effort observations. This includes 149 math observations, 150
  knowledge observations, and 125 extraction observations. The only missing
  planned observation is `math_0005` at effort 0.99. It remained missing after
  the one permitted cleanup pass because the API returned a connection error.

  Extraction was correct on 25/25 items at effort 0.2 (100.0%, n=25; 95%
  Wilson CI 86.7%-100.0%) with 24.8 mean completion tokens; 25/25 at effort
  0.4 (100.0%, n=25; 95% CI 86.7%-100.0%) with 26.9 mean tokens; 25/25 at
  effort 0.6 (100.0%, n=25; 95% CI 86.7%-100.0%) with 45.4 mean tokens; 25/25
  at effort 0.8 (100.0%, n=25; 95% CI 86.7%-100.0%) with 77.9 mean tokens;
  and 25/25 at effort 0.99 (100.0%, n=25; 95% CI 86.7%-100.0%) with 92.8 mean
  tokens. The configured knee rule selected effort 0.2.

  Knowledge was correct on 22/30 items at effort 0.2 (73.3%, n=30; 95% Wilson
  CI 55.6%-85.8%) with 102.9 mean completion tokens; 24/30 at effort 0.4
  (80.0%, n=30; 95% CI 62.7%-90.5%) with 141.3 mean tokens; 23/30 at effort
  0.6 (76.7%, n=30; 95% CI 59.1%-88.2%) with 358.4 mean tokens; 23/30 at
  effort 0.8 (76.7%, n=30; 95% CI 59.1%-88.2%) with 1,077.1 mean tokens; and
  20/30 at effort 0.99 (66.7%, n=30; 95% CI 48.8%-80.8%) with 1,811.9 mean
  tokens. The configured knee rule selected effort 0.4.

  Math was correct on 17/30 items at effort 0.2 (56.7%, n=30; 95% Wilson CI
  39.2%-72.6%) with 2,184.5 mean completion tokens; 16/30 at effort 0.4
  (53.3%, n=30; 95% CI 36.1%-69.8%) with 2,499.4 mean tokens; 15/30 at effort
  0.6 (50.0%, n=30; 95% CI 33.2%-66.8%) with 2,777.3 mean tokens; 14/30 at
  effort 0.8 (46.7%, n=30; 95% CI 30.2%-63.9%) with 3,204.1 mean tokens; and
  10/29 at effort 0.99 (34.5%, n=29; 95% CI 19.9%-52.7%) with 3,616.0 mean
  tokens. The configured knee rule selected effort 0.2.

  The plain answer for AIME is that accuracy did not drop at effort 0.2 in
  this sample. The observed result at effort 0.2 was 17/30 correct (56.7%,
  n=30; 95% CI 39.2%-72.6%), the highest of the five observed math rates.
  Accuracy decreased as requested effort increased, ending at 10/29 correct
  at effort 0.99 (34.5%, n=29; 95% CI 19.9%-52.7%). The knee is therefore
  0.2 under the project's rule. The confidence intervals overlap, and the
  provider-side output cap described below is a material confound, so this
  result should not be read as proof that more reasoning hurts AIME accuracy.

  Provider-reported usage across deduplicated successful observations totaled
  536,265 completion tokens and 79,476 prompt tokens. At $4.68 per million
  completion tokens and $1.87 per million prompt tokens, actual spend was
  $2.658340 against the $8.50 ceiling, leaving $5.841660 of ceiling margin.

  The retained real-result files contain 27 terminal error rows, all with
  `Connection error`. They represent 22 unique failed item-effort keys; 21
  were later recovered from a successful call. The unresolved key is
  `math_0005` at effort 0.99. Each terminal error row was written after the
  client's initial attempt plus six retries, so these rows account for 189
  failed connection attempts. Additional transient retries on calls that
  eventually succeeded were not persisted, so their exact count cannot be
  reconstructed. The five-consecutive-failure circuit breaker did not trip.

  There were zero parse failures (`extracted == ""`), zero empty responses,
  and zero heuristic refusal matches among the 424 unique successful
  observations. Seventy-eight observations had empty `reasoning_text`.
  Exactly the same 78 observations reported exactly 4,096 completion tokens:
  10 knowledge observations and 68 math observations. This strongly suggests
  a provider-side 4,096-token truncation or reporting cap despite the
  configured maximum of 32,768 tokens. The results were retained as returned
  and were not repaired.

  Across all unique successful observations, latency min/median/max was
  0.47/5.01/60.20 seconds. Median latency by increasing effort
  (0.2/0.4/0.6/0.8/0.99) was 0.69/0.74/0.78/1.10/1.19 seconds for extraction,
  1.05/1.51/3.19/8.83/14.51 seconds for knowledge, and
  36.71/32.34/52.70/54.47/58.36 seconds for math.

  Nothing was cut for budget. Math used all five effort levels and all 30
  available items, subject only to the one unresolved API failure. Knowledge
  used 30 items at all five levels. Extraction used 25 items at all five
  levels. No values were hand-adjusted.

- 2026-07-20: The 2026-07-19 math and knowledge accuracy curves and knees are
  invalid. Seventy-eight successful-looking rows stopped at exactly 4,096
  completion tokens, had empty reasoning text, and often lost their final
  answers. Grading those incomplete responses as wrong created an artificial
  decline in accuracy as requested effort increased. Those rows remain in the
  historical result files, but they must not be used as final evidence.

  The cache invalidation tool found and deleted exactly 78 affected cache
  entries: 68 math entries and 10 knowledge entries. A first uncapped rerun
  using non-streaming responses repeatedly lost its connection at about 60
  seconds. It produced no new successful observations before being stopped.
  This timing motivated changing the client to stream response chunks while
  requesting usage in the final stream event.

  The streamed smoke test was configured for the first four math items at
  effort 0.2 so that `math_0003` was the only uncached request. Tinker rejected
  the request before generation with HTTP 402 and the message that API access
  was blocked due to billing status. Four identical attempts were observed
  before the run was stopped. The smoke result file contains only three cached
  replays and no new successful observation, so streaming beyond 60 seconds
  and streamed token accounting were not tested.

  No provider-reported token usage was added by either correction attempt.
  Result-backed spend therefore remains $2.658340. The corrected math and
  knowledge curves, their knees, and the direction of the math effort effect
  remain unknown. No further Tinker calls should be made unless billing access
  is restored.

- 2026-07-20: An isolated OpenRouter replication completed with 375 unique
  domain-item-effort observations. OpenRouter results and cache entries were
  written only to `results_openrouter/` and `.cache_openrouter/`; no Tinker
  rows or cache entries were mixed into this analysis. The model was
  `thinkingmachines/inkling`, and every row reported Together as the served
  provider. OpenRouter's endpoint metadata reported quantization as unknown.
  The model has published BF16 and NVFP4 checkpoints, so this run cannot
  establish which precision produced these results. The five OpenRouter effort
  values were categorical (`minimal`, `low`, `medium`, `high`, and `max`) and
  should not be treated as numerically equivalent to the Tinker float settings.

  Math was correct on 21/30 items at minimal effort (70.0%, n=30) with 5,829.8
  mean completion tokens; 22/30 at low effort (73.3%, n=30) with 4,754.0 mean
  tokens; 25/30 at medium effort (83.3%, n=30) with 6,692.9 mean tokens; 23/30
  at high effort (76.7%, n=30) with 9,785.8 mean tokens; and 21/30 at max
  effort (70.0%, n=30) with 12,512.1 mean tokens. Under the configured rule,
  the lowest effort within two percentage points of the best observed
  accuracy, the math knee was medium.

  Knowledge was correct on 16/20 items at minimal effort (80.0%, n=20) with
  74.6 mean completion tokens; 14/20 at low effort (70.0%, n=20) with 74.5
  mean tokens; 14/20 at medium effort (70.0%, n=20) with 664.4 mean tokens;
  17/20 at high effort (85.0%, n=20) with 3,685.7 mean tokens; and 14/20 at max
  effort (70.0%, n=20) with 6,255.8 mean tokens. The knowledge knee was high.

  Extraction was correct on 25/25 items at minimal effort (100.0%, n=25) with
  23.8 mean completion tokens; 25/25 at low effort (100.0%, n=25) with 24.1
  mean tokens; 25/25 at medium effort (100.0%, n=25) with 62.4 mean tokens;
  25/25 at high effort (100.0%, n=25) with 91.4 mean tokens; and 25/25 at max
  effort (100.0%, n=25) with 90.8 mean tokens. The extraction knee was
  minimal.

  The plain answer for AIME is that the observed curve was non-monotonic.
  Minimal effort scored 21/30 (70.0%, n=30), low scored 22/30 (73.3%, n=30),
  and accuracy peaked at medium with 25/30 (83.3%, n=30). It then fell to
  23/30 at high (76.7%, n=30) and 21/30 at max (70.0%, n=30). Thus low effort
  was lower than the medium-effort knee, but max effort did not outperform low
  effort. The remaining 20,000-token truncations increased with effort and
  materially confound the high and max points, so these observations do not
  establish that additional completed reasoning intrinsically hurts accuracy.

  Exactly 30 rows ended with `finish_reason == "length"` and all 30 were
  graded wrong. Math had 5/30 at minimal, 2/30 at low, 4/30 at medium, 6/30
  at high, and 9/30 at max. Knowledge had 0/20 at minimal, 0/20 at low, 0/20
  at medium, 0/20 at high, and 4/20 at max. Extraction had 0/25 at every
  effort. These rows were retained as returned and were not repaired.

  There were no terminal sweep error rows and the circuit breaker did not
  trip. Two otherwise recorded rows ended with `finish_reason == "error"`:
  `math_0005` at high effort and `knowledge_0010` at medium effort. Both had
  non-empty reasoning but no final response or extracted answer and were
  graded wrong. In total, 31/375 rows had `extracted == ""` and the same
  31/375 had empty final responses: 26 math rows and 5 knowledge rows.
  No row had empty reasoning text, and there were zero heuristic refusal
  matches. The console showed transient HTTP 429 and HTTP 503 responses that
  recovered through backoff. Retry counts were not persisted in result rows,
  so the exact number of transient retry attempts cannot be reconstructed
  honestly.

  Latency min/median/max across the 375 unique rows was
  0.42/9.03/572.77 seconds. Math was 3.48/70.68/572.77 seconds, knowledge was
  0.57/6.78/404.43 seconds, and extraction was 0.42/0.95/6.34 seconds. The
  longest completed row was a max-effort math response that reached the
  20,000-token limit.

  Runtime endpoint metadata listed $1.00 per million input tokens and $4.05
  per million output tokens. The unique rows contained 70,828 prompt tokens
  and 1,409,644 completion tokens. The list-price token formula gives
  $5.779886, while OpenRouter's per-generation reported costs sum to
  $5.732601. The account usage delta at the final balance check was $5.725974.
  The higher provider-reported row total, $5.732601, is used as the
  conservative actual spend against the $10.00 ceiling, leaving $4.267399.

  Math used all 30 available items and all five effort levels. Knowledge was
  reduced before the phase from 30 to 20 items, retaining all five effort
  levels, because the conservative pre-phase estimate did not satisfy the
  two-times remaining-budget gate. Extraction used all 25 planned items and
  all five effort levels. Two medium-effort extraction smoke observations
  replayed from the isolated cache for free. No values were hand-adjusted.

  The earlier Tinker math and knowledge curves remain invalid because the
  endpoint's silent 4,096-token cap removed final answers and fabricated an
  apparent decline with effort. This OpenRouter replication is the corrected,
  isolated result series, but its own 20,000-token length rows remain visible
  and explicitly limit interpretation.

## Next falsification test

Run genuinely difficult competition-math items through the API at multiple
effort values while collecting provider-reported token counts. The Playground
pilot established the easy-task ceiling; the next test must be hard enough for
accuracy to vary before an effort knee can be estimated.

- 2026-07-21: Cap-rescue work began in fresh Tinker and OpenRouter namespaces.
  Historical caches and result files were not changed. The harness gained
  explicit item selection, output-cap-aware cache keys, provider-route-aware
  cache keys, and a dry-run report that separates expected cost from maximum
  exposure.

  The isolated Tinker check requested `math_0003` at effort 0.99 with a
  49,152-token cap. Tinker returned HTTP 402 before generation. The new result
  file is empty, no usage was reported, and Tinker work was stopped.

  The OpenRouter fallback pinned `thinkingmachines/inkling` to Together with
  fallbacks disabled. Runtime endpoint metadata reported unknown quantization,
  a 524,288-token context limit, $1.00 per million input tokens, and $4.05 per
  million output tokens. Together did not advertise support for a fixed seed,
  so these observations are matched stochastic reruns rather than
  deterministic counterfactual pairs.

  The first fallback check reran `math_0003` at max effort with a 49,152-token
  cap. Its historical Together response ended with `finish_reason ==
  "length"` at 20,000 completion tokens, contained no final answer, and was
  wrong (0/1, 0%, n=1). The larger-cap response ended with `finish_reason ==
  "stop"` after 38,603 completion tokens, extracted `240` against gold `240`,
  and was correct (1/1, 100%, n=1). Latency was 447.27 seconds. OpenRouter
  reported $0.156443 for the row, and the authenticated account-usage delta
  matched that amount.

  A planned four-row expansion was stopped during its second request. The
  first row, `math_0008`, ended after 187.23 seconds without the required final
  streaming usage event or any finish reason. It has `completion_tokens ==
  -1`, `prompt_tokens == -1`, 40,481 recorded reasoning characters, no final
  response, and no extracted answer. This is an unaccounted stream, not an
  incorrect model answer. The generation audit endpoint returned HTTP 404 for
  its ID. The next request, `math_0009`, was interrupted shortly after it
  began and produced no result row. Account usage remained unchanged after
  both events, so no additional charge was observed.

  The current cap-rescue sampling frame contains nine historically capped
  max-effort math rows. One has a valid larger-cap rerun and was rescued (1/1,
  100%, n=1), one has an unaccounted stream, and seven are missing. This is a
  mechanism demonstration, not a population estimate. Conservative cumulative
  OpenRouter spend is $5.889044. Including the historical $2.658340 Tinker
  spend, combined study spend is $8.547384 against the latest $10.00 ceiling,
  leaving $1.452616. This combined-provider interpretation is used as the
  conservative budget gate. No further paid calls are running.

  The client now rejects streams missing usage or a finish reason, refuses to
  replay real cache entries with negative token counts, and retains the
  generation ID in the failure message. Both rescue configs are disabled by
  default. The focused test suite passes 12/12 tests. No prompts, graders, gold
  labels, or historical observations were edited.

  A separate disabled Grok 4.5 cap-control config was prepared but not run. It
  uses three AIME items, max effort, a fixed seed, and 20,000- versus
  49,152-token conditions. The six-call dry run estimates $0.84 and reports a
  $1.26 worst-case charge. Adding that maximum to current combined spend would
  total about $9.81, under the $10.00 ceiling. Request order still needs to be
  randomized before this can be treated as a controlled pilot.

- 2026-07-21: The first scheduled Grok 4.5 request was initially rejected
  before generation with HTTP 404 because the provider filter used the model
  author slug `x-ai` instead of OpenRouter's provider slug `xai`. The public
  providers endpoint confirmed the correct slug. Account usage did not change,
  no completion row was produced, and the request remains first in the locked
  experimental order.

- 2026-07-21: The corrected Grok 4.5 pilot was stopped after two completed
  requests because the provider's native billable token count was not bounded
  by the requested `max_tokens` value. This invalidates the intended 20,000-
  versus 49,152-token manipulation and the earlier $1.26 worst-case estimate.

  At the requested 20,000-token condition, `math_0009` ended normally after
  5,429 native completion tokens, including 4,727 native reasoning tokens. It
  extracted `62` against gold `62` and was correct (1/1, 100%, n=1). Latency
  was 64.72 seconds and reported cost was $0.032990.

  The next 20,000-token request, `math_0003`, also ended normally and extracted
  `240` against gold `240` (1/1, 100%, n=1), but xAI reported 54,969 native
  completion tokens, including 53,883 native reasoning tokens. OpenRouter's
  normalized completion field was 6,302 tokens. Latency was 895.40 seconds and
  reported cost was $0.330182. The authenticated account deltas matched both
  row costs.

  The remaining four preordered jobs were not run. No item received both cap
  conditions, so these two rows provide no estimate of a cap effect. xAI's
  documentation lists only low, medium, and high effort for Grok 4.5, not the
  requested `max`; the effective served effort is unknown. The rows are kept
  exactly as returned and are not relabeled.

  Conservative combined spend is now $8.910557: $2.658340 historical Tinker,
  $5.732601 original OpenRouter replication, $0.156443 Inkling rescue,
  $0.032990 first Grok row, and $0.330182 second Grok row. This leaves
  $1.089443 below the $10.00 ceiling. The Grok config is disabled and no paid
  request is running.

- 2026-07-21: The Cap Semantics Probe was preregistered in commit `ea022cd`
  before paid calls. The fixed protocol used streaming OpenRouter Chat
  Completions, one easy extraction item and hard AIME item `math_0003`, and a
  requested `max_tokens` value of 2,000. Routes, caches, and result directories
  were isolated by provider. The per-target ceiling was $0.40 and the existing
  all-provider project ceiling remained $10.00.

  OpenAI's [Responses API
  reference](https://developers.openai.com/api/reference/resources/responses/methods/create)
  describes `max_output_tokens` as: "An upper bound for the number of tokens
  that can be generated for a response, including visible output tokens and
  reasoning tokens." The [GPT-OSS model
  page](https://developers.openai.com/api/docs/models/gpt-oss-120b) documents
  low, medium, and high reasoning effort. Those statements describe OpenAI's
  API and model, not necessarily DeepInfra's OpenRouter Chat Completions
  implementation. The pinned DeepInfra BF16 route nevertheless behaved as
  cap-inclusive in native billing: the hard response stopped at exactly 2,000
  native completion tokens with `finish_reason == "length"`, no extracted
  answer, and 57.62-second latency. The receipt reported 2,066 reasoning
  tokens, larger than its 2,000 native completion total. That accounting
  inconsistency is retained and not corrected. The easy response was correct
  with 44 native completion tokens and 23 reasoning tokens, ending with
  `stop` after 2.32 seconds. The two receipts totaled $0.000357988.

  OpenRouter's [reasoning-token
  documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
  says: "Reasoning tokens are considered output tokens and charged
  accordingly." Its [API
  reference](https://openrouter.ai/docs/api_reference/overview) says completion
  usage and pricing use native token counts and identifies the generation
  endpoint as the historical cost receipt. No Inkling/Together-specific
  statement was found that says whether reasoning is inside `max_tokens`.
  Measurement filled that documentation gap for this route: the hard response
  stopped at 2,000 native completion tokens, including 1,999 reasoning tokens,
  with `length`, no extracted answer, and 70.44-second latency. The easy
  response was correct with 39 completion and 25 reasoning tokens, ending with
  `stop` after 2.06 seconds. The two receipts totaled $0.008463950. Together's
  endpoint metadata continued to report the served precision as unknown.

  Moonshot's [Kimi K2.6 thinking
  guide](https://platform.kimi.ai/docs/guide/use-kimi-k2-thinking-model) says:
  "the sum of tokens in reasoning_content and content must be less than or
  equal to max_tokens." It also says Kimi K2.6 thinking is enabled by default
  and does not support `reasoning_effort`. The probe therefore recorded the
  setting as provider-native `default`, not medium. The pinned Moonshot AI
  INT4 route agreed with the documentation. The hard response stopped at 2,000
  native completion tokens, including 1,999 reasoning tokens, with `length`,
  no extracted answer, and 52.56-second latency. The easy response was correct
  with 401 completion and 391 reasoning tokens, ending with `stop` after 11.69
  seconds. The two receipts totaled $0.009778800.

  xAI's [Chat-to-Responses parameter
  mapping](https://docs.x.ai/developers/model-capabilities/text/comparison)
  describes `max_tokens` / `max_output_tokens` as "Maximum tokens to
  generate." Its [usage and pricing
  documentation](https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing)
  says "Reasoning tokens Full completion token price." The [Grok 4.5 reasoning
  page](https://docs.x.ai/developers/model-capabilities/text/reasoning)
  documents only low, medium, and high effort, with high as the default. The
  two earlier OpenRouter/xAI rows requested `max`, so their effective effort
  remains unknown. They nonetheless demonstrate cap-exclusive billing on that
  route. At a requested 20,000 cap, `math_0003` used 54,969 native completion
  tokens, including 53,883 reasoning tokens, while OpenRouter's
  gateway-normalized completion count was 6,302. It returned the correct final
  answer with `stop` after 895.40 seconds and cost $0.330182400. The other row
  remained below the request at 5,429 native completion tokens, including
  4,727 reasoning tokens, and cost $0.032990400. These historical costs were
  already in the pre-probe total.

  The documented-versus-measured result is therefore three cap-inclusive
  routes in native billed accounting and one cap-exclusive route. Kimi agreed
  directly with its vendor documentation. GPT-OSS agreed with OpenAI's
  Responses-level description, although it was served by a third-party Chat
  endpoint. Inkling's measured inclusion rule was provider-specific and
  under-documented. Grok's OpenRouter/xAI native reasoning and billing exceeded
  the requested cap even though the visible/gateway-normalized response stayed
  below it. This is stated as an API-route difference, not as an allegation
  about vendor intent.

  Inkling and Kimi each had one HTTP 429 on the initial hard request. Neither
  failure had a generation ID or receipt. The harness did not retry
  automatically. One manually gated retry per provider was allowed by the
  preregistered no-billed-generation rule, and both completed. GPT-OSS required
  no retry. All three hard 2,000-token responses had no extracted answer and
  all three honestly reported `length`. All three easy responses were complete
  and correct.

  New Cap Semantics Probe spend was $0.018600738. Cumulative study spend is
  $8.929157688 against the $10.00 ceiling, leaving $1.070842312. No 2,000-token
  Grok call was made. With two existing observations, the conservative
  nearest-rank p95 reasoning count is 53,883; twice that is 107,766 tokens and
  about $0.65 at $6 per million before input, above the $0.40 target ceiling.
  GPT-5.6 and other closed-model probes remain pending a user-approved top-up.

  Future gates for the measured Grok/xAI route will treat `max_tokens` as no
  financial bound. They will assume at least 107,766 completion tokens per
  call until a larger sample supports a different p95, record a receipt for
  every call, and enforce a kill threshold. No prompt, grader, gold label,
  response, usage count, or receipt was hand-adjusted.
