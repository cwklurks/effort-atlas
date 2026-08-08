# Ecosystem audit

## Scope and method

This is a source-code audit and an isolated post-generation diagnostic, not an end-to-end model evaluation. External repositories are frozen in `repos.lock.json`; code receipts are UTF-8 decoded without whitespace normalization and use 1-indexed inclusive line ranges. No model or paid API call is part of the workflow.

All code claims below resolve to the literal quote in the receipt ledger. Absence claims and exact searches are recorded in `GAPS.md`. Issue facts are kept separate from code claims.

## Output-token settings

| Target | Finding | Receipt |
|---|---|---|
| lm-evaluation-harness | Global generation default is 256 tokens and default_gen_kwargs propagates it. | [F001](#f001) |
| lm-evaluation-harness | Default generation kwargs place the cap in max_gen_toks. | [F002](#f002) |
| opencompass | LiteLLM adapter generation defaults max_out_len to 512. | [F006](#f006) |
| opencompass | LiteLLM adapter sends max_out_len as max_tokens. | [F007](#f007) |
| helm | Request schema defaults max_tokens to 100. | [F012](#f012) |
| inspect_ai | GenerateConfig leaves max_tokens unset and delegates the default to the model. | [F016](#f016) |
| simple-evals | ChatCompletionSampler defaults max_tokens to 1024. | [F022](#f022) |
| lighteval | Task generation_size defaults to None. | [F025](#f025) |
| lighteval | Transformers resolves max_new_tokens from model generation parameters or task generation_size. | [F026](#f026) |
| livebench | Generation CLI defaults the maximum new-token allowance to 4096. | [F030](#f030) |
| matharena | APIClient has no numeric max-token default. | [F041](#f041) |
| matharena | MathArena maps reasoning model token fields and injects a cap only when model configuration is non-null. | [F042](#f042) |
| simple-evals | Main runner overrides sampler caps to 2048 for GPT-4.1 configurations. | [F048](#f048) |
| helm | Bare AdapterSpec defaults max_tokens to 100. | [F054](#f054) |
| helm | Generic generation helper instead defaults max_tokens to 5, so default is construction-path specific. | [F055](#f055) |
| inspect_ai | Generation resolves an unset cap from the model API config then provider default. | [F062](#f062) |

## Reasoning-task settings and inheritance

| Target | Finding | Receipt |
|---|---|---|
| lm-evaluation-harness | GSM8K CoT omits max_gen_toks and therefore inherits the default through task resolution. | [F003](#f003) |
| inspect_evals | AIME 2026 task provides no GenerateConfig, so core model-specific cap resolution applies. | [F019](#f019) |
| inspect_evals | TAC explicitly raises the task cap to 16384 at medium reasoning effort. | [F021](#f021) |
| lighteval | AIME 24 explicitly leaves generation_size None. | [F027](#f027) |
| lighteval | GPQA multiple choice sets generation_size to one and a newline stop. | [F028](#f028) |
| matharena | DeepSeek R1 model config sets max_tokens to 32000. | [F037](#f037) |
| math-verify | Shipped MATH-Hard task sets generation_size to 1024 and uses the public parser-backed metric. | [F040](#f040) |
| matharena | AIME 2025 sets non-strict parsing but no competition-level generation cap. | [F043](#f043) |
| lighteval | GSM8K sets generation_size to 256. | [F044](#f044) |
| lighteval | Legacy MATH algebra sets generation_size to 2048. | [F045](#f045) |
| lighteval | MATH-500 sets generation_size to 32768. | [F046](#f046) |
| lighteval | Generative GPQA variants set generation_size to 32768 for reasoning models. | [F047](#f047) |
| helm | GSM8K sets 400; MATH sets 400 for CoT and 20 otherwise. | [F056](#f056) |

Not applicable means the repository is an extractor/scorer library rather than a generation harness. An unset value is not converted here into a guessed provider default. Adapter-specific defaults are scoped to the adapter named in the receipt.

## Extraction, normalization, and scoring

| Target | Finding | Receipt |
|---|---|---|
| lm-evaluation-harness | GSM8K flexible extraction selects the last regex match with group_select -1. | [F004](#f004) |
| lm-evaluation-harness | RegexFilter executes findall, indexed selection, tuple collapse, and fallback. | [F005](#f005) |
| opencompass | MATH postprocessor prefers boxed output then final-answer segments then the first period-delimited segment. | [F008](#f008) |
| opencompass | Boxed extraction returns None for an unmatched closing brace. | [F009](#f009) |
| helm | BasicGenerationMetric invokes reference metrics on generated request state. | [F015](#f015) |
| inspect_ai | Core match supports end-position numeric scoring after normalization. | [F018](#f018) |
| inspect_evals | AIME scorer takes the last nonempty line, removes boxed syntax, and invokes numeric match; empty output is incorrect. | [F020](#f020) |
| simple-evals | MATH extracts ANSWER_PATTERN group 1 or None and passes it to the equality checker. | [F023](#f023) |
| simple-evals | GPQA extracts one regex group or None and compares it to the shuffled correct letter. | [F024](#f024) |
| lighteval | Extractive match sorts matches rightmost-first and can append the first failed-parse string fallback. | [F029](#f029) |
| livebench | AIME scoring marks correct when gold occurs anywhere in the last 50 characters. | [F031](#f031) |
| livebench | Math contest scoring includes last-boxed, trailing-value, and last-line/parenthesis fallbacks. | [F032](#f032) |
| math-verify | Public parse defaults to LaTeX/expression extraction and first-match string fallback. | [F034](#f034) |
| math-verify | Public parse invokes the real regex/extraction pipeline under a timeout. | [F035](#f035) |
| math-verify | Public verify compares parsed gold and target with native mathematical strategies. | [F036](#f036) |
| matharena | Non-strict parser falls back to the last integer; strict parsing suppresses that fallback. | [F038](#f038) |
| matharena | Competition grader sends the last assistant message through the configured real parser. | [F039](#f039) |
| helm | GSM scorer extracts the final numeric regex match from both gold and prediction. | [F057](#f057) |
| helm | MATH get_answer selects the last complete box and native equivalence compares extracted answers. | [F058](#f058) |
| simple-evals | MGSM requires an answer prefix then returns the last numeric regex match. | [F059](#f059) |
| simple-evals | MGSM task calls the real parser then local scorer. | [F060](#f060) |
| inspect_ai | Numeric end matching scans whitespace tokens backward and takes the first parseable number. | [F063](#f063) |
| inspect_evals | GSM8K registers Inspect numeric match on generated output. | [F064](#f064) |
| opencompass | GSM8K postprocessor returns the last number or registered NULL sentinel and its evaluator scores numeric equality. | [F065](#f065) |
| opencompass | Canonical GSM8K dataset config wires gsm8k_postprocess to Gsm8kEvaluator. | [F066](#f066) |
| livebench | Olympiad scorer calls the real multi-stage extractor then native edit-distance or positional comparison. | [F067](#f067) |
| lm-evaluation-harness | The lm-eval AIME task initializes a dollar-span fallback before optional boxed extraction and returns exact-match scoring. | [F069](#f069) |

Extraction is reported separately from correctness. A returned nonempty value on a truncated fixture is the operational answer-returned event; it is not by itself evidence that answer text was newly invented. Native correctness is used only where the actual downstream path is runnable.

## Executable task-path dispatch receipts

| Target | Pipeline | Registered/dispatch path | Receipts | Headline eligible |
|---|---|---|---|---|
| lm-evaluation-harness | gsm8k_flexible_extract | lm_eval/tasks/gsm8k/gsm8k-cot.yaml flexible-extract | [F004](#f004), [F005](#f005) | yes |
| lm-evaluation-harness | aime_process_results | lm_eval/tasks/aime/aime.yaml | [F068](#f068), [F069](#f069) | yes |
| opencompass | gsm8k_last_number | configs/datasets/gsm8k/gsm8k_gen_1d7fe4.py | [F066](#f066) | yes |
| helm | math_chain_of_thought | src/helm/benchmark/run_specs/lite_run_specs.py MATH CoT | [F056](#f056), [F058](#f058) | yes |
| inspect_ai | gsm8k_numeric_match | inspect_evals/gsm8k | [F064](#f064) | yes |
| inspect_evals | aime_last_line_numeric | inspect_evals/aime2026 | [F019](#f019), [F020](#f020) | yes |
| simple-evals | mgsm_answer_prefix | mgsm_eval English Answer: prefix | [F060](#f060) | yes |
| lighteval | math_extractive_match | Metrics.expr_gold_metric extraction configuration | [F027](#f027), [F029](#f029) | yes |
| livebench | aime_last50 | gen_ground_truth_judgment.py AIME dispatch | [F031](#f031), [F070](#f070) | yes |
| livebench | olympiad_expression | LiveBench IMO/USAMO-only olympiad dispatch | [F067](#f067), [F070](#f070) | no |
| math-verify | default_parse_verify | public default Latex+Expr parser; generic isolated utility | [F040](#f040) | yes |
| matharena | competition_extract_and_grade | dataset-matched AIME/BRUMO/HMMT configs, strict_parsing=false | [F039](#f039), [F043](#f043) | yes |

Every executed pipeline is tied to a pinned task registration or dispatch receipt. The demoted LiveBench olympiad pipeline remains in this table as non-headline audit history; F070 proves that AIME-shaped data dispatches elsewhere.

## Truncation visibility

| Target | Captured | Persisted/logged | User-visible | Used to distinguish truncated from wrong | Evidence |
|---|---|---|---|---|---|
| lm-evaluation-harness | No | No | No | No | not found; see GAPS.md |
| opencompass | Yes in inspected streaming adapter | Yes, aggregate counts | Yes, as result counts | No evidence | F010-F011 |
| helm | Yes | Yes, finish metrics | Yes, as metrics | No; reported alongside scoring | F013-F014 |
| inspect_ai | Yes | Yes in ModelOutput/log | Yes | No in inspected match scorer | F017-F018 |
| inspect_evals | Via inspect_ai | Via inspect_ai | Via inspect_ai | No in AIME scorer | F019-F020 |
| simple-evals | No | No | No | No | not found; see GAPS.md |
| lighteval | No in inspected LiteLLM conversion | No | No | No | finish reason dropped; receipt ledger |
| livebench | Partial for empty token exhaustion | Coarse eval_status | Coarse status | Only coarse failure status, not nonempty truncation | receipt ledger |
| math-verify | Not applicable | Not applicable | Not applicable | No finish input | text-only library |
| matharena | Raw provider log may capture it | Raw log only; semantic result drops it | Heuristic warning only | Actual reason no; length heuristic after wrong score | receipt ledger |

## Issue receipts

These issue facts corroborate but do not replace code evidence. Retrieval metadata and hashes are in `issue_receipts.json`.

| Repository | Issue | Title | State | Created | Closed | Retrieved |
|---|---|---|---|---|---|---|
| EleutherAI/lm-evaluation-harness | [#3382](https://github.com/EleutherAI/lm-evaluation-harness/issues/3382) | [Bug] Truncation before think_end_token causes incomplete reasoning to be parsed as the final response | open | 2025-11-02T02:40:36Z |  | 2026-08-07 |
| EleutherAI/lm-evaluation-harness | [#3044](https://github.com/EleutherAI/lm-evaluation-harness/issues/3044) | Reasoning models and token limits | closed | 2025-06-06T15:34:56Z | 2025-07-10T22:06:57Z | 2026-08-07 |
| EleutherAI/lm-evaluation-harness | [#3391](https://github.com/EleutherAI/lm-evaluation-harness/issues/3391) | lm_eval harness with mmlu_pro and thinking models | open | 2025-11-09T17:39:19Z |  | 2026-08-07 |
| UKGovernmentBEIS/inspect_ai | [#3582](https://github.com/UKGovernmentBEIS/inspect_ai/issues/3582) | evaluations with max tokens set often result in truncated responses that are not easily visible to end users | closed | 2026-03-28T00:09:46Z | 2026-05-27T23:59:10Z | 2026-08-07 |

- `lm-evaluation-harness` #3382 directly describes incomplete reasoning being parsed as a final response after truncation.
- #3044 concerns reasoning models and token limits; #3391 concerns thinking-model MMLU-Pro behavior.
- `inspect_ai` #3582 concerns token-limited responses not being readily visible to end users.

## Finding inventory

| Target | Atomic code findings |
|---|---|
| helm | 9 |
| inspect_ai | 5 |
| inspect_evals | 4 |
| lighteval | 10 |
| livebench | 7 |
| lm-evaluation-harness | 7 |
| math-verify | 4 |
| matharena | 9 |
| opencompass | 8 |
| simple-evals | 7 |

## Receipt ledger

### F001

Global generation default is 256 tokens and default_gen_kwargs propagates it.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/defaults.py` lines 5-6
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/defaults.py#L5-L6
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"DEFAULT_MAX_LENGTH = 2048\nDEFAULT_MAX_GEN_TOKS = 256\n"
````

### F002

Default generation kwargs place the cap in max_gen_toks.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/defaults.py` lines 38-46
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/defaults.py#L38-L46
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def default_gen_kwargs(\n    until: str | list[str] | None, max_gen_toks: int = DEFAULT_MAX_GEN_TOKS\n) -> dict[str, Any]:\n    \"\"\"Returns default generation kwargs for LM evaluation.\"\"\"\n    _gen = {\n        \"temperature\": 0.0,\n        \"do_sample\": False,\n        \"max_gen_toks\": max_gen_toks,\n    }\n"
````

### F003

GSM8K CoT omits max_gen_toks and therefore inherits the default through task resolution.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/tasks/gsm8k/gsm8k-cot.yaml` lines 58-63
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/gsm8k/gsm8k-cot.yaml#L58-L63
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"generation_kwargs:\n  do_sample: false\n  until:\n  - 'Q:'\n  - </s>\n  - <|im_end|>\n"
````

### F004

GSM8K flexible extraction selects the last regex match with group_select -1.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/tasks/gsm8k/gsm8k-cot.yaml` lines 46-57
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/gsm8k/gsm8k-cot.yaml#L46-L57
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"filter_list:\n- filter:\n  - function: regex\n    regex_pattern: The answer is (\\-?[0-9\\.\\,]+).\n  - function: take_first\n  name: strict-match\n- filter:\n  - function: regex\n    group_select: -1\n    regex_pattern: (-?[$0-9.,]{2,})|(-?[0-9]+)\n  - function: take_first\n  name: flexible-extract\n"
````

### F005

RegexFilter executes findall, indexed selection, tuple collapse, and fallback.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/filters/extraction.py` lines 39-58
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/filters/extraction.py#L39-L58
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def apply(\n        self, resps: Iterable[Sequence[str]], docs: Sequence[dict[str, Any]]\n    ) -> Iterable[list[str]]:\n        def filter_set(inst: Sequence[str]) -> list[str]:\n            filtered = []\n            for resp in inst:\n                if not isinstance(resp, str):\n                    resp = \"\"\n                match = self.regex.findall(resp)\n                if match:\n                    match = match[self.group_select]\n                    if isinstance(match, tuple):\n                        match = [m for m in match if m]\n                        if match:\n                            match = match[0]\n                        else:\n                            match = self.fallback\n                    match = match.strip()\n                else:\n                    match = self.fallback\n"
````

### F006

LiteLLM adapter generation defaults max_out_len to 512.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/models/litellm_api.py` lines 106-118
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/litellm_api.py#L106-L118
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def generate(\n        self,\n        inputs: List[PromptType],\n        max_out_len: int = 512,\n        **gen_kwargs,\n    ) -> List[str]:\n        \"\"\"Generate responses for a batch of inputs.\n\n        Args:\n            inputs: list of strings or ``PromptList`` messages.\n            max_out_len: max output tokens per response. Defaults to 512.\n            **gen_kwargs: extra per-call generation kwargs forwarded to\n                LiteLLM, except core request fields managed by this wrapper.\n"
````

### F007

LiteLLM adapter sends max_out_len as max_tokens.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/models/litellm_api.py` lines 234-241
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/litellm_api.py#L234-L241
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"        call_kwargs: Dict = {\n            **safe_extra_body,\n            **safe_gen_kwargs,\n            'model': self.path,\n            'messages': messages,\n            'max_tokens': max_out_len,\n            'drop_params': True,\n        }\n"
````

### F008

MATH postprocessor prefers boxed output then final-answer segments then the first period-delimited segment.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/datasets/math.py` lines 190-201
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/datasets/math.py#L190-L201
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"@TEXT_POSTPROCESSORS.register_module('math_postprocess_v2')\ndef math_postprocess_v2(text: str) -> str:\n\n    cand_ans = extract_boxed_answer(text, strip_double_curly_brace=True)\n    if cand_ans:\n        return cand_ans\n\n    for maybe_ans in text.split('.'):\n        # if 'final answer' in maybe_ans.lower():\n        if re.search('final answer|answer is', maybe_ans.lower()):\n            return normalize_final_answer(maybe_ans)\n    return normalize_final_answer(text.split('.')[0])\n"
````

### F009

Boxed extraction returns None for an unmatched closing brace.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/datasets/math.py` lines 16-41
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/datasets/math.py#L16-L41
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def last_boxed_only_string(string):\n    idx = string.rfind('\\\\boxed')\n    if idx < 0:\n        idx = string.rfind('\\\\fbox')\n        if idx < 0:\n            return None\n\n    i = idx\n    right_brace_idx = None\n    num_left_braces_open = 0\n    while i < len(string):\n        if string[i] == '{':\n            num_left_braces_open += 1\n        if string[i] == '}':\n            num_left_braces_open -= 1\n            if num_left_braces_open == 0:\n                right_brace_idx = i\n                break\n        i += 1\n\n    if right_brace_idx is None:\n        retval = None\n    else:\n        retval = string[idx:right_brace_idx + 1]\n\n    return retval\n"
````

### F010

Streaming OpenAI adapter captures and logs finish_reason.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/models/openai_streaming.py` lines 257-267
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/openai_streaming.py#L257-L267
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"                # Check if streaming is finished\n                if chunk.choices[0].finish_reason is not None:\n                    finish_reason = chunk.choices[0].finish_reason\n                    if self.verbose:\n                        print()  # Add newline after streaming complete\n                        elapsed = current_time - start_time\n                        log_with_thread(\n                            f'Streaming finished with reason: '\n                            f'{chunk.choices[0].finish_reason}, '\n                            f'chunks: {chunk_count}, elapsed: {elapsed:.1f}s')\n                    break\n"
````

### F011

OpenICL evaluator aggregates finish reasons into results.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/tasks/openicl_eval.py` lines 384-400
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/tasks/openicl_eval.py#L384-L400
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            for pred_sample in replica_pred_strs:\n                replica_total_neg_logprob += pred_sample['rollout'][\n                    'sum_neg_logprob']\n                replica_total_tokens += pred_sample['rollout']['num_tokens']\n                replica_finish_counts[pred_sample['rollout']\n                                      ['finish_reason']] += 1\n                if pred_sample['rollout']['num_tokens'] > 0:\n                    replica_successful_samples += 1\n\n            replica_entropy_nats = replica_total_neg_logprob / replica_total_tokens\n            replica_avg_length = replica_total_tokens / replica_successful_samples if replica_successful_samples > 0 else 0.0\n\n            result[f'{i}_th rollout results'] = dict(\n                total_neg_logprob=replica_total_neg_logprob,\n                total_tokens=replica_total_tokens,\n                finish_reason=replica_finish_counts,\n                successful_samples=replica_successful_samples,\n"
````

### F012

Request schema defaults max_tokens to 100.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/common/request.py` lines 39-43
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/common/request.py#L39-L43
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    top_k_per_token: int = 1\n    \"\"\"Take this many highest probability candidates per token in the completion\"\"\"\n\n    max_tokens: int = 100\n    \"\"\"Maximum number of tokens to generate (per completion)\"\"\"\n"
````

### F013

Together client copies provider finish_reason into GeneratedOutput.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/clients/together_client.py` lines 307-315
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/clients/together_client.py#L307-L315
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            raw_finish_reason: Optional[str] = raw_completion.get(\"finish_reason\")\n            finish_reason: Optional[Dict] = {\"reason\": raw_finish_reason} if raw_finish_reason else None\n\n            completion = GeneratedOutput(\n                text=cleanup_str(raw_completion[\"text\"], \"together\"),\n                logprob=sequence_logprob,\n                tokens=tokens,\n                finish_reason=finish_reason,\n            )\n"
````

### F014

Basic metrics expose length, stop, endoftext, and unknown finish-reason counters.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/metrics/basic_metrics.py` lines 432-451
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/basic_metrics.py#L432-L451
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def _compute_finish_reason_metrics(\n    adapter_spec: AdapterSpec, request_state: RequestState, metric_service: MetricService\n) -> List[Stat]:\n    \"\"\"Record how often generation finished due to reaching token limit, stop token(s), or end of text\"\"\"\n    assert request_state.result is not None\n    sequence = request_state.result.completions[0]\n    valid_reasons = [\n        \"length\",\n        \"stop\",\n        \"endoftext\",\n        \"unknown\",\n    ]\n    if sequence.finish_reason is None or sequence.finish_reason[\"reason\"] not in valid_reasons:\n        reason = \"unknown\"\n    else:\n        reason = sequence.finish_reason[\"reason\"]\n    return [\n        Stat(MetricName(f\"finish_reason_{valid_reason}\")).add(int(reason == valid_reason))\n        for valid_reason in valid_reasons\n    ]\n"
````

### F015

BasicGenerationMetric invokes reference metrics on generated request state.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/metrics/basic_metrics.py` lines 199-215
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/basic_metrics.py#L199-L215
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def evaluate_generation(\n        self,\n        adapter_spec: AdapterSpec,\n        request_state: RequestState,\n        metric_service: MetricService,\n        eval_cache_path: str,\n    ) -> List[Stat]:\n        \"\"\"Compute all metrics.\"\"\"\n        stats: List[Stat] = []\n        stats.extend(compute_request_state_metrics(self.efficiency_metric, adapter_spec, request_state, metric_service))\n\n        if len(request_state.instance.references) > 0:\n            stats.extend(compute_reference_metrics(self.names, adapter_spec, request_state, metric_service))\n\n        stats.extend(compute_language_modeling_metrics(adapter_spec, request_state, metric_service))\n\n        return stats\n"
````

### F016

GenerateConfig leaves max_tokens unset and delegates the default to the model.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`
Path: `src/inspect_ai/model/_generate_config.py` lines 198-220
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_generate_config.py#L198-L220
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"class GenerateConfig(BaseModel):\n    \"\"\"Model generation options.\"\"\"\n\n    max_retries: int | None = Field(default=None)\n    \"\"\"Maximum number of times to retry request, so e.g. 1 allows two attempts total (defaults to unlimited).\"\"\"\n\n    timeout: int | None = Field(default=None)\n    \"\"\"Timeout (in seconds) for an entire request (including retries).\"\"\"\n\n    attempt_timeout: int | None = Field(default=None)\n    \"\"\"Timeout (in seconds) for any given attempt (if exceeded, will abandon attempt and retry according to max_retries).\"\"\"\n\n    max_connections: int | None = Field(default=None)\n    \"\"\"Maximum number of concurrent connections to Model API (default is model specific).\"\"\"\n\n    adaptive_connections: bool | int | AdaptiveConcurrency | None = Field(default=None)\n    \"\"\"Adaptive concurrency for model API connections. Defaults to enabled (`None` and `True` both resolve to `AdaptiveConcurrency()` defaults: min=10, start=20, max=100). Pass `False` to opt out (uses static concurrency). Pass an integer `N` as shorthand for `AdaptiveConcurrency(max=N)`. Pass an `AdaptiveConcurrency` to fully customize bounds and tuning (cooldown_seconds, decrease_factor, scale_up_percent). An explicit `max_connections` or `batch=True` takes precedence and uses static concurrency.\"\"\"\n\n    system_message: str | None = Field(default=None)\n    \"\"\"Override the default system message.\"\"\"\n\n    max_tokens: int | None = Field(default=None)\n    \"\"\"The maximum number of tokens that can be generated in the completion (default is model specific).\"\"\"\n"
````

### F017

Model output stores stop_reason and normalizes legacy length to max_tokens.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`
Path: `src/inspect_ai/model/_model_output.py` lines 224-256
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_model_output.py#L224-L256
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"class ChatCompletionChoice(BaseModel):\n    \"\"\"Choice generated for completion.\"\"\"\n\n    message: ChatMessageAssistant\n    \"\"\"Assistant message.\"\"\"\n\n    stop_reason: StopReason = Field(default=\"unknown\")\n    \"\"\"Reason that the model stopped generating.\"\"\"\n\n    stop_details: StopDetails | None = Field(default=None)\n    \"\"\"Additional detail about the stop reason (e.g. refusal category/explanation), when provided.\"\"\"\n\n    logprobs: Logprobs | None = Field(default=None)\n    \"\"\"Logprobs.\"\"\"\n\n    prompt_logprobs: Logprobs | None = Field(default=None)\n    \"\"\"Per-prompt-token log probabilities (vLLM only).\n\n    Placed on the choice (not ``ModelOutput``) so scorers access prompt\n    and output logprobs uniformly via ``choices[0]``.  Perplexity evals\n    use ``num_choices=1``, so there is no duplication in practice.\"\"\"\n\n    @model_validator(mode=\"before\")\n    @classmethod\n    def migrate_stop_reason(cls: Type[\"ChatCompletionChoice\"], values: Any) -> Any:\n        if not isinstance(values, dict):\n            return values\n        if \"stop_reason\" in values:\n            stop_reason = values[\"stop_reason\"]\n            if stop_reason == \"length\":\n                values[\"stop_reason\"] = \"max_tokens\"\n\n        return values\n"
````

### F018

Core match supports end-position numeric scoring after normalization.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`
Path: `src/inspect_ai/scorer/_match.py` lines 9-42
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/scorer/_match.py#L9-L42
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def match(\n    location: Literal[\"begin\", \"end\", \"any\", \"exact\"] = \"end\",\n    *,\n    ignore_case: bool = True,\n    numeric: bool = False,\n) -> Scorer:\n    \"\"\"Scorer which matches text or a number.\n\n    Args:\n       location: Location to match at. \"any\" matches anywhere in the\n          output; \"exact\" requires the output be exactly\n          equal to the target (module whitespace, etc.)\n       ignore_case: Do case insensitive comparison.\n       numeric: Is this a numeric match? When True, currency symbols\n          (`$`, `€`, `£`), thousands separators (`,`), and formatting\n          markers (`*`, `_`) are stripped before numbers are normalized\n          and compared. The percent sign is not stripped: `60%` is\n          ambiguous (it could mean `60` or `0.6`), so an answer of `60%`\n          will not match a numeric target of `60`. To accept a\n          percentage-formatted answer, pass both forms as targets, e.g.\n          `Target([\"60\", \"60%\"])`, where the non-numeric `\"60%\"` is\n          matched as a string.\n    \"\"\"\n\n    def check(value: str, target: str) -> tuple[str, bool]:\n        return match_str(\n            value=value,\n            target=target,\n            location=location,\n            ignore_case=ignore_case,\n            numeric=numeric,\n        )\n\n    return str_match_scorer(check)\n"
````

### F019

AIME 2026 task provides no GenerateConfig, so core model-specific cap resolution applies.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`
Path: `src/inspect_evals/aime2026/aime2026.py` lines 16-34
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/aime2026/aime2026.py#L16-L34
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"@task\ndef aime2026() -> Task:\n    \"\"\"Inspect Task implementation for the AIME 2026 benchmark.\"\"\"\n    dataset = hf_dataset(\n        path=DATASET_PATH,\n        split=\"test\",\n        sample_fields=record_to_sample,\n        revision=AIME2026_DATASET_REVISION,\n    )\n\n    return Task(\n        dataset=dataset,\n        solver=aime_solver(),\n        scorer=[\n            aime_scorer(),\n        ],\n        version=EVAL_VERSION.comparability_version,\n        metadata=EVAL_VERSION.to_metadata(),\n    )\n"
````

### F020

AIME scorer takes the last nonempty line, removes boxed syntax, and invokes numeric match; empty output is incorrect.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`
Path: `src/inspect_evals/utils/aime_common.py` lines 37-59
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/utils/aime_common.py#L37-L59
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"@scorer(metrics=[accuracy(), stderr()])\ndef aime_scorer() -> Scorer:\n    async def score(state: TaskState, target: Target) -> Score:\n        raw = state.output.completion\n        lines = raw.strip().splitlines()\n        if not lines:\n            return Score(\n                value=INCORRECT,\n                explanation=\"Model produced empty completion\",\n            )\n        last_line = lines[-1]\n        cleaned = remove_boxed_from_ans(last_line)\n        state.output.completion = cleaned\n\n        result = await match(numeric=True)(state, target)\n        if result is None:\n            raise ValueError(\"No result found\")\n\n        result.metadata = {\"unprocessed_answer\": raw, \"cleaned_answer\": cleaned}\n\n        return result\n\n    return score\n"
````

### F021

TAC explicitly raises the task cap to 16384 at medium reasoning effort.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`
Path: `src/inspect_evals/tac/tac.py` lines 48-58
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/tac/tac.py#L48-L58
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            confirm_to_complete(),\n        ],\n        scorer=tac_scorer(),\n        epochs=3,\n        max_messages=30,\n        version=EVAL_VERSION.comparability_version,\n        metadata=EVAL_VERSION.to_metadata(),\n        config=GenerateConfig(\n            max_tokens=16384,\n            reasoning_effort=\"medium\",\n        ),\n"
````

### F022

ChatCompletionSampler defaults max_tokens to 1024.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `sampler/chat_completion_sampler.py` lines 21-34
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/sampler/chat_completion_sampler.py#L21-L34
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def __init__(\n        self,\n        model: str = \"gpt-3.5-turbo\",\n        system_message: str | None = None,\n        temperature: float = 0.5,\n        max_tokens: int = 1024,\n    ):\n        self.api_key_name = \"OPENAI_API_KEY\"\n        self.client = OpenAI()\n        # using api_key=os.environ.get(\"OPENAI_API_KEY\")  # please set your API_KEY\n        self.model = model\n        self.system_message = system_message\n        self.temperature = temperature\n        self.max_tokens = max_tokens\n"
````

### F023

MATH extracts ANSWER_PATTERN group 1 or None and passes it to the equality checker.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `math_eval.py` lines 45-60
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/math_eval.py#L45-L60
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def __call__(self, sampler: SamplerBase) -> EvalResult:\n        def fn(row: dict):\n            prompt_messages = [\n                sampler._pack_message(content=QUERY_TEMPLATE.format(**row), role=\"user\")\n            ]\n            sampler_response = sampler(prompt_messages)\n            response_text = sampler_response.response_text\n            actual_queried_prompt_messages = sampler_response.actual_queried_message_list\n            match = re.search(ANSWER_PATTERN, response_text)\n            extracted_answer = match.group(1) if match else None\n            score = float(check_equality(self.equality_checker, row[\"Answer\"], extracted_answer))\n            html = common.jinja_env.from_string(HTML_JINJA).render(\n                prompt_messages=actual_queried_prompt_messages,\n                next_message=dict(content=response_text, role=\"assistant\"),\n                score=score,\n                correct_answer=row[\"Answer\"],\n"
````

### F024

GPQA extracts one regex group or None and compares it to the shuffled correct letter.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `gpqa_eval.py` lines 56-67
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/gpqa_eval.py#L56-L67
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            sampler_response = sampler(prompt_messages)\n            response_text = sampler_response.response_text\n            actual_queried_prompt_messages = sampler_response.actual_queried_message_list\n            match = re.search(ANSWER_PATTERN_MULTICHOICE, response_text)\n            extracted_answer = match.group(1) if match else None\n            score = 1.0 if extracted_answer == correct_answer else 0.0\n            html = common.jinja_env.from_string(HTML_JINJA).render(\n                prompt_messages=actual_queried_prompt_messages,\n                next_message=dict(content=response_text, role=\"assistant\"),\n                score=score,\n                correct_answer=correct_answer,\n                extracted_answer=extracted_answer,\n"
````

### F025

Task generation_size defaults to None.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/lighteval_task.py` lines 137-140
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/lighteval_task.py#L137-L140
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    # Generation args\n    generation_size: int | None = None\n    generation_grammar: TextGenerationInputGrammarType | None = None\n    stop_sequence: ListLike[str] | None = None\n"
````

### F026

Transformers resolves max_new_tokens from model generation parameters or task generation_size.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/models/transformers/transformers_model.py` lines 559-564
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/models/transformers/transformers_model.py#L559-L564
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"                # stop_tokens and max_tokens genrated) which is not necessarily\n                # the case! Because of that we only use batch size of 1\n                stop_tokens = split[0].stop_sequence\n\n            max_new_tokens = self.config.generation_parameters.max_new_tokens or split[0].generation_size\n            returns_logits = split[0].use_logits\n"
````

### F027

AIME 24 explicitly leaves generation_size None.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/aime.py` lines 64-78
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/aime.py#L64-L78
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"aime24 = LightevalTaskConfig(\n    name=\"aime24\",\n    prompt_function=aime_prompt,\n    sample_fields=record_to_sample,\n    solver=[prompt_template(MATH_PROMPT_TEMPLATE), generate(cache=True)],\n    scorer=math_scorer(),\n    hf_repo=\"HuggingFaceH4/aime_2024\",\n    hf_subset=\"default\",\n    hf_avail_splits=[\"train\"],\n    evaluation_splits=[\"train\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=None,\n    metrics=[Metrics.pass_at_k_math(sample_params={\"k\": 1}), Metrics.avg_at_n_math(sample_params={\"n\": 1})],\n    version=2,\n"
````

### F028

GPQA multiple choice sets generation_size to one and a newline stop.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/gpqa.py` lines 108-124
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gpqa.py#L108-L124
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"gpqa = LightevalTaskConfig(\n    name=\"gpqa:mc\",\n    prompt_function=gpqa_prompt,\n    sample_fields=record_to_sample,\n    sample_to_fewshot=sample_to_fewshot,\n    solver=[multiple_choice(cache=True)],\n    scorer=choice(),\n    hf_repo=\"Idavidrein/gpqa\",\n    hf_subset=\"gpqa_main\",\n    hf_avail_splits=[\"train\"],\n    evaluation_splits=[\"train\"],\n    few_shots_split=None,\n    few_shots_select=\"random_sampling\",\n    generation_size=1,\n    metrics=[Metrics.loglikelihood_acc],\n    stop_sequence=[\"\\n\"],\n    version=0,\n"
````

### F029

Extractive match sorts matches rightmost-first and can append the first failed-parse string fallback.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/metrics/utils/extractive_match_utils.py` lines 590-632
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/metrics/utils/extractive_match_utils.py#L590-L632
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    # Get all patterns and sort by priority\n    all_patterns = [\n        (pattern, target_type, priority)\n        for target_patterns, target_type in target_res\n        for pattern, priority in target_patterns\n    ]\n    match_found = False\n\n    # Group patterns by priority using itertools.groupby\n    for _, patterns_group in groupby(sorted(all_patterns, key=lambda x: x[2]), key=lambda x: x[2]):\n        # Find all matches for each pattern in this priority group\n        matches_with_pos = (\n            (match, match.start(), match.end(), target_type)\n            for pattern, target_type, _ in patterns_group\n            for match in pattern.finditer(pred)\n        )\n\n        # Sort matches by end position (rightmost first) and then by start position (leftmost first)\n        matches_with_pos = sorted(matches_with_pos, key=lambda x: (x[2], -x[1]), reverse=True)\n\n        # Try to extract from each match, starting from rightmost\n        for match, _, _, target_type in matches_with_pos:\n            extracted_match, str_fallback = extract_match(match, target_type, timeout_seconds)\n            match_found = True\n\n            if str_fallback:\n                fallbacks.append(str_fallback)\n\n            if extracted_match is not None:\n                extracted_predictions.append(extracted_match)\n                break\n\n            if extraction_mode == \"first_match\":\n                break\n\n        # If we found something and we're in first_match mode, stop processing other priorities\n        if extracted_predictions or (match_found and extraction_mode == \"first_match\"):\n            break\n\n    if fallback_mode == \"first_match\" and fallbacks:\n        extracted_predictions += [fallbacks[0]]\n\n    return extracted_predictions\n"
````

### F030

Generation CLI defaults the maximum new-token allowance to 4096.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/gen_api_answer.py` lines 380-388
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/gen_api_answer.py#L380-L388
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    parser.add_argument(\n        \"--force-temperature\", type=float, help=\"Forcibly set a sampling temperature.\"\n    )\n    parser.add_argument(\n        \"--max-tokens\",\n        type=int,\n        default=4096,\n        help=\"The maximum number of new generated tokens.\",\n    )\n"
````

### F031

AIME scoring marks correct when gold occurs anywhere in the last 50 characters.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/process_results/math/math_competitions/utils.py` lines 87-104
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/process_results/math/math_competitions/utils.py#L87-L104
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def aime_process_results(ground_truth: str, llm_answer: str, debug=False) -> int:\n    score = 0\n\n    # extract text from <solution></solution> tags\n    solution_matches = re.findall(r'<solution>(.*?)</solution>', llm_answer)\n    if len(solution_matches) > 0:\n        solution_match = solution_matches[-1]\n        if len(set(solution_match)) == 1 and next(iter(set(solution_match))).lower() == ground_truth.lower():\n            score = 1\n\n    if score == 0 and ground_truth in llm_answer[-50:]:\n        score = 1\n\n    if debug and score == 0:\n        print('INCORRECT')\n        print('GROUND TRUTH', ground_truth)\n        print('SOLUTION', llm_answer[-200:])\n    return score\n"
````

### F032

Math contest scoring includes last-boxed, trailing-value, and last-line/parenthesis fallbacks.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/process_results/math/math_competitions/utils.py` lines 22-50
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/process_results/math/math_competitions/utils.py#L22-L50
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    parsed_answer = None\n\n    allow_boxed = True\n    if score == 0 and allow_boxed:\n        llm_answer = llm_answer.replace(\"\\\\\\\\fbox{\", \"\\\\\\\\boxed{\")\n        last_boxed = last_boxed_only_string(llm_answer)\n        if last_boxed:\n            last_boxed_res = remove_boxed(last_boxed).replace('\\\\text{', '').replace('}', '').replace('\\\\', '').lower()\n            if last_boxed_res in {'a', 'b', 'c', 'd', 'e'}:\n                parsed_answer = last_boxed_res\n            if parsed_answer == ground_truth.lower():\n                score = 1\n\n    allow_answer_values = True\n    if score == 0 and allow_answer_values:\n        value = extract_answer(question_text, ground_truth)\n        length_to_check = 20 + len(value)\n        if value in llm_answer[-length_to_check:]:\n            score = 1\n\n    allow_last_line = True\n    if score == 0 and allow_last_line:\n        last_line = llm_answer.strip().split('\\n')[-1]\n        if last_line.strip().replace('*', '').lower() == ground_truth.lower():\n            score = 1\n        elif '(' in last_line and ')' in last_line:\n            val = last_line.split('(')[1].split(')')[0]\n            if val.lower() == ground_truth.lower():\n                score = 1\n"
````

### F033

Anthropic completion path records an empty answer with token_exhaustion instead of retrying when reasoning consumes the cap.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/model/completions.py` lines 578-587
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/model/completions.py#L578-L587
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    text_messages = [c for c in message if c['type'] == 'text' and c.get('text', '').strip()]\n    if len(text_messages) == 0:\n        block_types = [c['type'] for c in message]\n        if stop_reason == 'max_tokens':\n            # Token exhaustion: the entire max_tokens budget went to the thinking\n            # block, leaving no final answer. Match the litellm path -- record an\n            # empty answer + eval_status so it grades as a genuine 0 (a real model\n            # failure), not a hard infra $ERROR$. Do NOT retry-chase token limits.\n            _md: dict[str, Any] = {'eval_status': 'token_exhaustion'}\n            _out = -1\n"
````

### F034

Public parse defaults to LaTeX/expression extraction and first-match string fallback.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`
Path: `src/math_verify/parser.py` lines 649-682
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/parser.py#L649-L682
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def parse(\n    pred: str,\n    extraction_config: Sequence[ExtractionTarget] = [\n        LatexExtractionConfig(),\n        ExprExtractionConfig(),\n    ],\n    fallback_mode: Literal[\"no_fallback\", \"first_match\"] = \"first_match\",\n    extraction_mode: Literal[\"first_match\", \"any_match\"] = \"any_match\",\n    parsing_timeout: int = 5,\n    raise_on_error: bool = False,\n):\n    \"\"\"Extracts and parses mathematical expressions from a prediction string.\n\n    This function attempts to extract mathematical expressions from text using various strategies\n    (LaTeX, plain expressions, etc.) and converts them to SymPy objects.\n\n    Args:\n        pred (str): The prediction string to parse.\n        extraction_config (Sequence[ExtractionTarget], optional): Configuration for what types of expressions\n            to extract and how to extract them. Defaults to [LatexExtractionConfig(), ExprExtractionConfig()].\n        fallback_mode (Literal[\"no_fallback\", \"first_match\"], optional): How to handle extraction failures. Defaults to \"first_match\".\n            - \"no_fallback\": Return only successfully parsed expressions\n            - \"first_match\": Include the first string match even if parsing failed\n        extraction_mode (Literal[\"first_match\", \"any_match\"], optional): Strategy for extracting matches. Defaults to \"any_match\".\n            - \"first_match\": Stop after finding the first match\n            - \"any_match\": Try to extract all possible matches, stops after first sucesful parsing attempt\n        parsing_timeout (int, optional): Maximum time in seconds to spend parsing each expression. Defaults to 3. Any timeout seconds > 0 or not None will result in the function to raise a ValueError if it's called in a threaded environment.\n        raise_on_error (bool, optional): Whether to raise an exception if an error occurs during parsing or return an empty list. Defaults to False.\n\n    Returns:\n        list: List of extracted predictions. Each prediction can be:\n            - SymPy expression (for successfully parsed mathematical expressions)\n            - String (for fallback matches when fallback_mode=\"first_match\")\n            Empty list if no matches are found.\n"
````

### F035

Public parse invokes the real regex/extraction pipeline under a timeout.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`
Path: `src/math_verify/parser.py` lines 700-706
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/parser.py#L700-L706
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    try:\n        target_res = get_extraction_regexes(extraction_config)\n        return timeout(timeout_seconds=parsing_timeout)(extract_target_from_pred)(\n            pred,\n            target_res,\n            fallback_mode=fallback_mode,\n            extraction_mode=extraction_mode,\n"
````

### F036

Public verify compares parsed gold and target with native mathematical strategies.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`
Path: `src/math_verify/grader.py` lines 755-773
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/grader.py#L755-L773
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def verify(\n    gold: list[Basic | MatrixBase | str] | Basic | MatrixBase | str,\n    target: list[Basic | MatrixBase | str] | Basic | MatrixBase | str,\n    float_rounding: int = 6,\n    numeric_precision: int = 15,\n    strict: bool = True,\n    allow_set_relation_comp: bool = False,\n    timeout_seconds: int | None = 5,\n    raise_on_error: bool = False,\n) -> bool:\n    \"\"\"Verifies if the target expression matches the gold expression using multiple comparison strategies.\n\n    This function implements a comprehensive comparison system for mathematical expressions,\n    handling various types of mathematical objects (numbers, expressions, sets, matrices, etc.)\n    with multiple fallback strategies.\n\n    Note:\n        - It's expected that both gold and pred has been parsed with math_verify.parse function.\n        - Function is not symmetric, gold answer should be passed as gold and prediction as pred. The non-symmetric nature appears at assignment simplification and equation interval conversion.\n"
````

### F037

DeepSeek R1 model config sets max_tokens to 32000.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `configs/models/deepseek/deepseek_r1.yaml` lines 1-5
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/configs/models/deepseek/deepseek_r1.yaml#L1-L5
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"model: deepseek-ai/DeepSeek-R1\napi: together\nmax_tokens: 32000\ntemperature: 0.6\ntop_p: 0.95\n"
````

### F038

Non-strict parser falls back to the last integer; strict parsing suppresses that fallback.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/parser.py` lines 346-395
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/parser.py#L346-L395
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def extract_last_integer(text: str) -> Optional[int]:\n    \"\"\"Extracts the last integer from a string.\n\n    Args:\n        text (str): The string to search.\n\n    Returns:\n        tuple: A tuple containing the last integer and a warning level.\n    \"\"\"\n    pattern = r\"\\b\\d+\\b\"\n    matches = list(regex.finditer(pattern, text))\n    if not matches:\n        return None, WarningType.MAJOR\n    try:\n        return int(matches[-1].group()), WarningType.MAJOR\n    except Exception as e:\n        logger.warning(f\"Error extracting last integer: {e}\")\n        return None, WarningType.MAJOR\n\n\ndef extract_answer(\n    text: str, strict_parsing: bool = True, parse: bool = True, list_answer: bool = False, typed_delimiters: bool = True\n):\n    \"\"\"Extracts and parses the final answer from a string.\n\n    Args:\n        text (str): The string to search.\n        strict_parsing (bool, optional): Whether to use strict parsing. Defaults to True.\n        parse (bool, optional): Whether to parse the answer. Defaults to True.\n        list_answer (bool, optional): Whether to expect a list of answers. Defaults to False.\n\n    Returns:\n        tuple: A tuple containing the parsed answer and a warning level.\n    \"\"\"\n    if text is None or len(text) == 0:\n        return None, WarningType.MAJOR\n    warning_old = WarningType.NONE\n    if text in complete_mapper:\n        text = complete_mapper[text]\n        warning_old = WarningType.MAJOR\n    text, warning = replace_unicode(text)\n    warning = max(warning, warning_old)\n    answer, warning_new = extract_boxed_answer_parse(text, parse, list_answer, typed_delimiters=typed_delimiters)\n    if isinstance(answer, AnswerList) and len(answer.answers) == 1:\n        answer = answer.answers[0]\n    warning = max(warning, warning_new)\n    if answer is not None or strict_parsing:\n        return answer, warning\n\n    return extract_last_integer(text)\n"
````

### F039

Competition grader sends the last assistant message through the configured real parser.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/grader.py` lines 152-189
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/grader.py#L152-L189
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def extract_and_grade(messages, output_tokens, gold_answer, competition_config, problem=None, debug_info=\"\"):\n    \"\"\"\n    Grade the model's messages against the gold answer.\n\n    Args:\n        messages (list): The list of message dictionaries from the model (clean format).\n        gold_answer (str): The gold answer as string.\n\n    Returns:\n        tuple: (answer, is_correct, warning)\n    \"\"\"\n\n    is_final_answer = competition_config.get(\"final_answer\", True)\n    is_lean_comp = competition_config.get(\"lean\", False)\n    use_strict_parsing = competition_config.get(\"strict_parsing\", False)\n    use_exact_match = competition_config.get(\"exact_match_parsing\", False)\n    use_typed_delimiters = competition_config.get(\"typed_delimited_answers\", True)\n\n    is_broken, reason = is_conversation_broken(messages)\n    if is_broken:\n        raise ValueError(f\"Message list is broken: {reason}\")\n\n    if is_lean_comp:\n        return grade_lean_submission(messages, competition_config, problem, debug_info=debug_info)\n\n    gold_answer_is_list = is_final_answer and \",\" in gold_answer\n\n    last_message = messages[-1][\"content\"]\n    if use_exact_match:\n        model_answer, warning = extract_boxed_answer(last_message, list_answer=gold_answer_is_list)\n    else:\n        model_answer, warning = extract_answer(\n            last_message,\n            strict_parsing=use_strict_parsing,\n            parse=True,\n            list_answer=gold_answer_is_list,\n            typed_delimiters=use_typed_delimiters,\n        )\n"
````

### F040

Shipped MATH-Hard task sets generation_size to 1024 and uses the public parser-backed metric.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`
Path: `src/math_verify/tasks.py` lines 167-190
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/tasks.py#L167-L190
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"math_hard_lighteval = [\n    LightevalTaskConfig(\n        name=f\"math_hard:{subset}\",\n        suite=[\"lighteval\", \"math\"],\n        prompt_function=math_hard_prompt_function,\n        hf_repo=\"lighteval/MATH-Hard\",\n        hf_subset=subset,\n        evaluation_splits=[\"test\"],\n        few_shots_split=\"train\",\n        generation_size=1024,\n        metric=[\n            as_lighteval_metric(\n                math_metric(\n                    gold_extraction_target=(\n                        LatexExtractionConfig(boxed_match_priority=0),\n                    ),\n                    pred_extraction_target=(\n                        LatexExtractionConfig(),\n                        ExprExtractionConfig(),\n                    ),\n                )\n            ),\n        ],\n        stop_sequence=[\"\\nQuestion:\", \"\\nProblem:\", \"\\nquestion:\", \"\\nproblem:\"],\n"
````

### F041

APIClient has no numeric max-token default.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/api_client.py` lines 51-56
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L51-L56
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def __init__(\n        self,\n        model,\n        timeout=30000,\n        max_tokens=None,\n        api=\"openai\",\n"
````

### F042

MathArena maps reasoning model token fields and injects a cap only when model configuration is non-null.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/api_client.py` lines 125-150
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L125-L150
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"        # Adapt model name and other args to the model\n        if \"--\" in model:\n            model, reasoning_effort = model.split(\"--\")\n            logger.info(f\"Model: {model}, Reasoning effort: {reasoning_effort}\")\n        if (api not in [\"anthropic\", \"openai\"] or self.tool_calls_allowed) and batch_processing:\n            logger.warning(\"Batch processing is only supported for the Anthropic API and OpenAI API without tool calling.\")\n            batch_processing = False\n        if (\"o1\" in model or \"o3\" in model or \"o4\" in model or \"gpt-5\" in model) and api == \"openai\":\n            logger.info(\"Not using system messages for o1/o3/o4 model.\")\n            no_system_messages = True  # o1 model cannot handle system messages\n            if not use_openai_responses_api:\n                max_tokens_param = \"max_completion_tokens\"\n        if use_openai_responses_api and not batch_processing:\n            max_tokens_param = \"max_output_tokens\"\n        if self.tool_calls_allowed and not use_openai_responses_api and not api == \"anthropic\":\n            max_tokens_param = \"max_completion_tokens\"\n        self._kwarg_remover(api, model, kwargs)\n\n        self.model = model\n        self.kwargs = kwargs\n        self.max_tokens_param = max_tokens_param\n        self.context_limit = context_limit\n        self.max_tokens = max_tokens\n        if max_tokens is not None:\n            self.kwargs[max_tokens_param] = max_tokens\n        self.timeout = timeout\n"
````

### F043

AIME 2025 sets non-strict parsing but no competition-level generation cap.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `configs/competitions/aime/aime_2025.yaml` lines 1-5
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/configs/competitions/aime/aime_2025.yaml#L1-L5
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"instruction: \"Put your final answer within \\\\boxed{{}}.\\nThe answer is an integer between 0 and 999 inclusive.\"\nstrict_parsing: false\nn_problems: 30\ndate: \"2025-02-12\"\ndataset_path: MathArena/aime_2025\n"
````

### F044

GSM8K sets generation_size to 256.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/gsm8k.py` lines 67-85
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gsm8k.py#L67-L85
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"gsm8k = LightevalTaskConfig(\n    name=\"gsm8k\",\n    prompt_function=gsm8k_prompt,\n    sample_fields=record_to_sample,\n    sample_to_fewshot=sample_to_fewshot,\n    solver=[prompt_template(MATH_PROMPT_TEMPLATE), generate(cache=True)],\n    scorer=math_scorer(),\n    hf_repo=\"openai/gsm8k\",\n    hf_subset=\"main\",\n    hf_avail_splits=[\"train\", \"test\"],\n    evaluation_splits=[\"test\"],\n    few_shots_split=None,\n    few_shots_select=\"random_sampling_from_train\",\n    generation_size=256,\n    metrics=[\n        Metrics.expr_gold_metric,\n    ],\n    stop_sequence=[\"Question:\"],\n    version=0,\n"
````

### F045

Legacy MATH algebra sets generation_size to 2048.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/math.py` lines 35-56
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/math.py#L35-L56
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"math_algebra = LightevalTaskConfig(\n    name=\"math:algebra\",\n    prompt_function=math_prompt,\n    hf_repo=\"DigitalLearningGmbH/MATH-lighteval\",\n    hf_subset=\"algebra\",\n    hf_avail_splits=[\"train\", \"test\"],\n    evaluation_splits=[\"test\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=2048,\n    metrics=[\n        Metrics.maj_at_n(\n            sample_params={\n                \"n\": 4,\n                \"strip_strings\": True,\n                \"normalize_pred\": math_normalizer,\n                \"normalize_gold\": math_normalizer,\n            }\n        ),\n    ],\n    stop_sequence=[\"\\n\"],\n    version=1,\n"
````

### F046

MATH-500 sets generation_size to 32768.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/math_500.py` lines 58-75
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/math_500.py#L58-L75
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"math_500 = LightevalTaskConfig(\n    name=\"math_500\",\n    prompt_function=math_500_prompt,\n    hf_repo=\"HuggingFaceH4/MATH-500\",\n    hf_subset=\"default\",\n    hf_avail_splits=[\"test\"],\n    evaluation_splits=[\"test\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=32768,\n    metrics=[\n        Metrics.pass_at_k_math(sample_params={\"k\": 1, \"n\": 1}),\n    ],\n    version=2,\n    sample_fields=record_to_sample,\n    solver=[prompt_template(MATH_QUERY_TEMPLATE), generate(cache=True)],\n    scorer=model_graded_fact(),\n)\n"
````

### F047

Generative GPQA variants set generation_size to 32768 for reasoning models.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/tasks/tasks/gpqa.py` lines 127-180
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gpqa.py#L127-L180
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"gpqa_diamond_instruct = LightevalTaskConfig(\n    name=\"gpqa:diamond\",\n    prompt_function=gpqa_instruct_prompt,\n    sample_fields=record_to_sample,\n    sample_to_fewshot=sample_to_fewshot,\n    solver=[multiple_choice(cache=True)],\n    scorer=choice(),\n    hf_repo=\"Idavidrein/gpqa\",\n    hf_subset=\"gpqa_diamond\",\n    hf_avail_splits=[\"train\"],\n    evaluation_splits=[\"train\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=32768,  # needed for reasoning models like R1\n    metrics=[Metrics.gpqa_instruct_pass_at_k(sample_params={\"k\": 1})],\n    stop_sequence=[],  # no stop sequence, will use eos token\n    version=1,\n)\n\ngpqa_extended_instruct = LightevalTaskConfig(\n    name=\"gpqa:extended\",\n    prompt_function=gpqa_instruct_prompt,\n    sample_fields=record_to_sample,\n    sample_to_fewshot=sample_to_fewshot,\n    solver=[multiple_choice(cache=True)],\n    scorer=choice(),\n    hf_repo=\"Idavidrein/gpqa\",\n    hf_subset=\"gpqa_extended\",\n    hf_avail_splits=[\"train\"],\n    evaluation_splits=[\"train\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=32768,  # needed for reasoning models like R1\n    metrics=[Metrics.gpqa_instruct_metric],\n    stop_sequence=[],  # no stop sequence, will use eos token\n    version=0,\n)\n\ngpqa_main_instruct = LightevalTaskConfig(\n    name=\"gpqa:main\",\n    prompt_function=gpqa_instruct_prompt,\n    sample_fields=record_to_sample,\n    sample_to_fewshot=sample_to_fewshot,\n    solver=[multiple_choice(cache=True)],\n    scorer=choice(),\n    hf_repo=\"Idavidrein/gpqa\",\n    hf_subset=\"gpqa_main\",\n    hf_avail_splits=[\"train\"],\n    evaluation_splits=[\"train\"],\n    few_shots_split=None,\n    few_shots_select=None,\n    generation_size=32768,  # needed for reasoning models like R1\n    metrics=[Metrics.gpqa_instruct_metric],\n    stop_sequence=[],  # no stop sequence, will use eos token\n"
````

### F048

Main runner overrides sampler caps to 2048 for GPT-4.1 configurations.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `simple_evals.py` lines 213-223
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/simple_evals.py#L213-L223
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"        # GPT-4.1 models\n        \"gpt-4.1\": ChatCompletionSampler(\n            model=\"gpt-4.1-2025-04-14\",\n            system_message=OPENAI_SYSTEM_MESSAGE_API,\n            max_tokens=2048,\n        ),\n        \"gpt-4.1-temp-1\": ChatCompletionSampler(\n            model=\"gpt-4.1-2025-04-14\",\n            system_message=OPENAI_SYSTEM_MESSAGE_API,\n            max_tokens=2048,\n            temperature=1.0,\n"
````

### F049

RequestLogger can persist a redacted raw provider response.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/request_logger.py` lines 100-129
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/request_logger.py#L100-L129
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def log_response(self, ts, batch_idx, response=None, **info):\n        if not self.enabled:\n            return\n        try:\n            problem_idx, logfile = self._logfile(ts, batch_idx)\n            if not os.path.exists(logfile):\n                logger.warning(f\"Can't log response, log file does not exist: {logfile}\")\n                return\n\n            try:\n                with open(logfile, \"r\", encoding=\"utf-8\") as f:\n                    data = json.load(f, object_pairs_hook=OrderedDict)\n            except Exception as exc:\n                logger.warning(f\"Recovering response log after unreadable request log {logfile}: {exc}\")\n                data = OrderedDict(\n                    {\n                        \"comp_name\": self.comp_name,\n                        \"solver_name\": self.solver_name,\n                        \"timestamp\": ts,\n                        \"problem_idx\": problem_idx,\n                        \"batch_idx\": batch_idx,\n                        \"request_log_error\": str(exc),\n                    }\n                )\n\n            # Update the data with the response information\n            data[\"response_info\"] = info\n            if response is not None:\n                data[\"response\"] = self._redact_for_logging(response)\n            self._write_json(logfile, data)\n"
````

### F050

Semantic InternalRequestResult drops finish reason and retains only conversation, token counts, retries, and time.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/api_client.py` lines 332-342
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L332-L342
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    class InternalRequestResult:\n        \"\"\"A class to hold the result of a request internally (below run_queries).\"\"\"\n\n        def __init__(self, conversation, input_tokens, output_tokens, cached_input_tokens=0, cached_write_tokens=0, n_retries=0, time=0):\n            self.conversation = conversation\n            self.input_tokens = input_tokens\n            self.output_tokens = output_tokens\n            self.cached_input_tokens = cached_input_tokens\n            self.cached_write_tokens = cached_write_tokens\n            self.n_retries = n_retries\n            self.time = time\n"
````

### F051

Grader warns on suspicious power-of-two/ten output lengths only after an incorrect score.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`
Path: `src/matharena/grader.py` lines 215-224
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/grader.py#L215-L224
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"        typed_gold_answer, _ = parse_answer(\n            gold_answer, list_answer=gold_answer_is_list, typed_delimiters=use_typed_delimiters\n        )\n        is_correct = check_answers(model_answer, typed_gold_answer)\n\n    if not is_correct and check_output_length(output_tokens):\n        logger.warning(\n            f\"[{debug_info}] Model output length {output_tokens} is of the form 10**k * 2**n. This might indicate it hit the token limit.\"\n        )\n        warning = WarningType.MINOR  # model just didn't have time, any error could have been caused by this\n"
````

### F052

LiteLLM response conversion retains content and reasoning but drops choice finish reason.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`
Path: `src/lighteval/models/endpoints/litellm_model.py` lines 363-375
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/models/endpoints/litellm_model.py#L363-L375
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            for response, context in zip(responses, contexts):\n                result: list[str] = [choice.message.content for choice in response.choices]\n                reasonings: list[str | None] = [\n                    getattr(choice.message, \"reasoning_content\", None) for choice in response.choices\n                ]\n\n                cur_response = ModelResponse(\n                    # In empty responses, the model should return an empty string instead of None\n                    text=result if result[0] else [\"\"],\n                    reasonings=reasonings,\n                    input=context,\n                )\n                results.append(cur_response)\n"
````

### F053

Ground-truth judgment forces zero only for recognized coarse eval_status failures.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/gen_ground_truth_judgment.py` lines 108-116
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/gen_ground_truth_judgment.py#L108-L116
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    eval_status = answer.get(\"eval_status\")\n\n    splits = task_or_subtask.split('_')\n\n    eval_error = None\n    try:\n        if eval_status in FAILURE_EVAL_STATUSES:\n            score = 0\n            category = question.get(\"category\", task)\n"
````

### F054

Bare AdapterSpec defaults max_tokens to 100.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/adaptation/adapter_spec.py` lines 112-124
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/adaptation/adapter_spec.py#L112-L124
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    # Decoding parameters (inherited by `Request`)\n\n    model_deployment: str = \"\"\n    \"\"\"Name of the language model deployment (<host_organization>/<model name>) to send requests to.\"\"\"\n\n    model: str = \"\"\n    \"\"\"Name of the language model (<creator_organization>/<model name>) to send requests to.\"\"\"\n\n    temperature: float = 1\n    \"\"\"Temperature parameter used in generation.\"\"\"\n\n    max_tokens: int = 100\n    \"\"\"Maximum number of tokens to generate.\"\"\"\n"
````

### F055

Generic generation helper instead defaults max_tokens to 5, so default is construction-path specific.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/adaptation/common_adapter_specs.py` lines 276-289
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/adaptation/common_adapter_specs.py#L276-L289
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def get_generation_adapter_spec(\n    instructions: str = \"\",\n    input_noun: Optional[str] = None,\n    newline_after_input_noun: bool = False,\n    output_noun: Optional[str] = None,\n    newline_after_output_noun: bool = False,\n    max_train_instances: int = 5,\n    num_outputs: int = 1,\n    max_tokens: int = 5,\n    stop_sequences: Optional[List] = None,  # default value of `stop_sequences` is [\"\\n\"]\n    temperature: float = 0.0,\n    multi_label: bool = False,\n    sample_train: bool = True,\n) -> AdapterSpec:\n"
````

### F056

GSM8K sets 400; MATH sets 400 for CoT and 20 otherwise.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/run_specs/lite_run_specs.py` lines 137-224
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/run_specs/lite_run_specs.py#L137-L224
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"@run_spec_function(\"gsm\")\ndef get_gsm_spec() -> RunSpec:\n    scenario_spec = ScenarioSpec(class_name=\"helm.benchmark.scenarios.gsm_scenario.GSM8KScenario\", args={})\n\n    # Create AdapterSpec based on the GSM8K paper: https://arxiv.org/pdf/2110.14168.pdf\n    adapter_spec = get_generation_adapter_spec(\n        input_noun=\"Q\",\n        output_noun=\"A\",\n        max_train_instances=5,  # Due to limited context and long example length\n        max_tokens=400,  # The paper uses 400 tokens as the max sample length\n        stop_sequences=[\"\\n\\n\"],  # Since answer may contain newlines, we use two as SEP\n    )\n\n    return RunSpec(\n        name=\"gsm\",\n        scenario_spec=scenario_spec,\n        adapter_spec=adapter_spec,\n        metric_specs=get_basic_generation_metric_specs([\"exact_match_indicator\", \"final_number_exact_match\"])\n        + get_generic_metric_specs()\n        + get_generative_harms_metric_specs(),\n        groups=[\"gsm\"],\n    )\n\n\n@run_spec_function(\"math\")\ndef get_math_spec(\n    subject: str,\n    level: str,\n    use_official_examples: str = \"False\",\n    use_chain_of_thought: str = \"False\",\n) -> RunSpec:\n    # Convert to bools and remove the str versions\n    use_official_examples_bool: bool = use_official_examples.lower() == \"true\"\n    use_chain_of_thought_bool: bool = use_chain_of_thought.lower() == \"true\"\n    del use_official_examples\n    del use_chain_of_thought\n\n    if use_chain_of_thought_bool:\n        assert not use_official_examples_bool, \"Cannot use official examples when use_chain_of_thought is True.\"\n    scenario_spec = ScenarioSpec(\n        class_name=\"helm.benchmark.scenarios.math_scenario.MATHScenario\",\n        args={\n            \"subject\": subject,\n            \"level\": level,\n            \"use_official_examples\": use_official_examples_bool,\n            \"use_chain_of_thought\": use_chain_of_thought_bool,\n        },\n    )\n\n    if use_chain_of_thought_bool:  # Include the solution in the output as per https://arxiv.org/abs/2201.11903\n        output_prefix = \"Answer: \"  # Don't include LaTeX '$' delimiters\n        output_suffix = \"\\n\"\n        instance_prefix = \"###\\n\"  # Don't include LaTeX '$' delimiters\n        max_tokens = 400  # Increase the number of tokens to generate\n        stop_sequences = [\"###\"]  # Break at the next instance; extraneous output will be stripped out\n        groups = [\"math_chain_of_thought\"]\n    else:\n        output_prefix = \"Answer: $\"\n        output_suffix = \"$\\n\"\n        instance_prefix = \"###\\n\"\n        max_tokens = 20\n        stop_sequences = [\"$\"]  # Break at the nearest LaTeX closing delimiter\n        groups = [\"math_regular\"]\n\n    adapter_spec = AdapterSpec(\n        method=ADAPT_GENERATION,\n        instructions=\"Given a mathematics problem, determine the answer. Simplify your answer as much as possible.\\n\",\n        max_train_instances=8,\n        num_outputs=1,\n        temperature=0.0,\n        stop_sequences=stop_sequences,\n        max_tokens=max_tokens,\n        input_prefix=\"Problem: \",\n        input_suffix=\"\\n\",\n        output_prefix=output_prefix,\n        output_suffix=output_suffix,\n        instance_prefix=instance_prefix,\n    )\n\n    return RunSpec(\n        name=f\"math:subject={subject},level={level},\"\n        f\"use_official_examples={use_official_examples_bool},use_chain_of_thought={use_chain_of_thought_bool}\",\n        scenario_spec=scenario_spec,\n        adapter_spec=adapter_spec,\n        metric_specs=get_basic_metric_specs(\n            [\"math_equiv_chain_of_thought\" if use_chain_of_thought_bool else \"math_equiv\"]\n        )\n        + get_generative_harms_metric_specs(),\n"
````

### F057

GSM scorer extracts the final numeric regex match from both gold and prediction.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/metrics/evaluate_reference_metrics.py` lines 145-161
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/evaluate_reference_metrics.py#L145-L161
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def final_number_exact_match(gold: str, pred: str) -> float:\n    \"\"\"\n    Returns 1 iff the final number in gold and pred match.\n    Similar to exact_match_indicator.\n    Example:\n    - gold = \"The answer is 15.\"\n    - pred = \"The answer is 15 eggs.\"\n    - Returns 1\n    \"\"\"\n\n    def get_final_number(x: str) -> str:\n        matches = re.findall(r\"-?[\\d,]+(?:.\\d+)?\", x)\n        if not matches:\n            return \"\"\n        return matches[-1].replace(\",\", \"\")\n\n    return exact_match(get_final_number(gold), get_final_number(pred))\n"
````

### F058

MATH get_answer selects the last complete box and native equivalence compares extracted answers.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`
Path: `src/helm/benchmark/scenarios/math_scenario.py` lines 253-293
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/scenarios/math_scenario.py#L253-L293
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def get_answer(solution: Optional[str]) -> Optional[str]:\n    if solution is None:\n        return None\n    last_boxed = last_boxed_only_string(solution)\n    if last_boxed is None:\n        return None\n    answer = remove_boxed(last_boxed)\n    if answer is None:\n        return None\n    return answer\n\n\ndef is_equiv(str1: Optional[str], str2: Optional[str]) -> float:\n    \"\"\"Returns (as a float) whether two strings containing math are equivalent up to differences of formatting in\n    - units\n    - fractions\n    - square roots\n    - superfluous LaTeX.\n\n    Source: https://github.com/hendrycks/math\n    \"\"\"\n    if str1 is None and str2 is None:\n        print(\"WARNING: Both None\")\n        return 1.0\n    if str1 is None or str2 is None:\n        return 0.0\n\n    try:\n        ss1 = _strip_string(str1)\n        ss2 = _strip_string(str2)\n        return float(ss1 == ss2)\n    except Exception:\n        return float(str1 == str2)\n\n\ndef is_equiv_chain_of_thought(str1: str, str2: str) -> float:\n    \"\"\"Strips the solution first before calling `is_equiv`.\"\"\"\n    ans1 = get_answer(str1)\n    ans2 = get_answer(str2)\n\n    return is_equiv(ans1, ans2)\n"
````

### F059

MGSM requires an answer prefix then returns the last numeric regex match.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `mgsm_eval.py` lines 83-100
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/mgsm_eval.py#L83-L100
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def parse_answer(answer: str, answer_prefix: str) -> str:\n    if answer_prefix not in answer:\n        return \"\"\n\n    answer_text = answer.split(answer_prefix)[-1].strip()\n\n    # find all the numbers (including decimals) in the string\n    numbers = re.findall(r\"\\d+\\.?\\d*\", answer_text.replace(\",\", \"\"))\n\n    # return the first number (removing trailing decimal point if present),\n    # or an empty string if there were no numbers\n    return numbers[-1].rstrip(\".\") if numbers else \"\"\n\n\ndef score_mgsm(target: str, prediction: str) -> bool:\n    if \".\" in prediction:\n        prediction = prediction.rstrip(\"0\").rstrip(\".\")\n\n"
````

### F060

MGSM task calls the real parser then local scorer.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `mgsm_eval.py` lines 154-181
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/mgsm_eval.py#L154-L181
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def __call__(self, sampler: SamplerBase) -> EvalResult:\n        def fn(example: dict[str, str]):\n            language = example[\"lang\"]\n            latin_language = \"group_latin\" if language in LATIN_LANGUAGES else \"group_non_latin\"\n            correct_answer = example[\"targets\"]\n            instruction = LANG_TO_INSTRUCTIONS[language]\n            prompt_messages = [\n                sampler._pack_message(\n                    content=instruction.format(input=example[\"inputs\"]), role=\"user\"\n                )\n            ]\n            try:\n                sampler_response = sampler(prompt_messages)\n                response_text = sampler_response.response_text\n                actual_queried_prompt_messages = sampler_response.actual_queried_message_list\n            except Exception as e:\n                response_text = \"\"\n\n            answer_prefix = LANG_TO_ANSWER_PREFIX[language]\n            extracted_answer = parse_answer(response_text, answer_prefix)\n\n            score = score_mgsm(correct_answer, extracted_answer)\n            html = common.jinja_env.from_string(HTML_JINJA).render(\n                prompt_messages=actual_queried_prompt_messages,\n                next_message=dict(content=response_text, role=\"assistant\"),\n                score=score,\n                correct_answer=correct_answer,\n                extracted_answer=extracted_answer or None,\n"
````

### F061

Responses sampler retains output text and usage but not incomplete or finish metadata.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`
Path: `sampler/responses_sampler.py` lines 55-85
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/sampler/responses_sampler.py#L55-L85
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    def __call__(self, message_list: MessageList) -> SamplerResponse:\n        if self.system_message:\n            message_list = [\n                self._pack_message(\"developer\", self.system_message)\n            ] + message_list\n        trial = 0\n        while True:\n            try:\n                if self.reasoning_model:\n                    reasoning = (\n                        {\"effort\": self.reasoning_effort}\n                        if self.reasoning_effort\n                        else None\n                    )\n                    response = self.client.responses.create(\n                        model=self.model,\n                        input=message_list,\n                        reasoning=reasoning,\n                    )\n                else:\n                    response = self.client.responses.create(\n                        model=self.model,\n                        input=message_list,\n                        temperature=self.temperature,\n                        max_output_tokens=self.max_tokens,\n                    )\n                return SamplerResponse(\n                    response_text=response.output_text,\n                    response_metadata={\"usage\": response.usage},\n                    actual_queried_message_list=message_list,\n                )\n"
````

### F062

Generation resolves an unset cap from the model API config then provider default.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`
Path: `src/inspect_ai/model/_model.py` lines 813-817
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_model.py#L813-L817
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"        # provide max_tokens from the model api if required\n        if config.max_tokens is None:\n            config.max_tokens = self.api.max_tokens_for_config(config)\n            if config.max_tokens is None:\n                config.max_tokens = self.api.max_tokens()\n"
````

### F063

Numeric end matching scans whitespace tokens backward and takes the first parseable number.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`
Path: `src/inspect_ai/scorer/_common.py` lines 59-83
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/scorer/_common.py#L59-L83
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    if numeric:\n        t = strip_numeric_punctuation(t)\n    if numeric and _is_number(t):\n        # the target is a number: extract the relevant number(s) from the\n        # value, normalize both, and compare for numeric equality. we do\n        # NOT fall through to the text comparison below because e.g.\n        # \"25\".endswith(\"5\") is True but 25 != 5.\n        v = strip_numeric_punctuation(v)\n        t = normalize_number(t)\n        words = re.split(r\"\\s+\", v)\n        if location == \"begin\":\n            v = first_number_normalized(words)\n        elif location == \"end\":\n            words.reverse()\n            v = first_number_normalized(words)\n        elif location == \"exact\":\n            v = normalize_number(v)\n        else:\n            # location == \"any\": match if any number in the value equals t\n            for number in all_numbers_normalized(words):\n                if number == t:\n                    return number, True\n            return answer, False\n        answer = v\n        return answer, v == t\n"
````

### F064

GSM8K registers Inspect numeric match on generated output.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`
Path: `src/inspect_evals/gsm8k/gsm8k.py` lines 78-91
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/gsm8k/gsm8k.py#L78-L91
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"    # define task\n    return Task(\n        dataset=hf_dataset(\n            path=\"openai/gsm8k\",\n            data_dir=\"main\",\n            split=\"test\",\n            sample_fields=record_to_sample,\n            revision=GSM8K_DATASET_REVISION,\n        ),\n        solver=solver,\n        scorer=match(numeric=True),\n        version=EVAL_VERSION.comparability_version,\n        metadata=EVAL_VERSION.to_metadata(),\n    )\n"
````

### F065

GSM8K postprocessor returns the last number or registered NULL sentinel and its evaluator scores numeric equality.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/datasets/gsm8k.py` lines 43-79
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/datasets/gsm8k.py#L43-L79
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"@TEXT_POSTPROCESSORS.register_module('gsm8k')\ndef gsm8k_postprocess(text: str) -> str:\n    text = text.split('Question:')[0]\n    numbers = re.findall(r'\\-?\\d+\\.\\d+|\\-?\\d+', text)\n    if not numbers:\n        return 'NULL'\n    return numbers[-1]\n\n\nclass Gsm8kEvaluator(BaseEvaluator):\n\n    def is_equal(self, pred, refer):\n        try:\n            if pred == refer or abs(float(pred) - int(refer)) < 1e-6:\n                return True\n        except Exception:\n            pass\n        return False\n\n    def score(self, predictions, references):\n        if len(predictions) != len(references):\n            return {\n                'error': 'predictions and references have different '\n                'length'\n            }\n        correct = 0\n        count = 0\n        details = []\n        for i, j in zip(predictions, references):\n            detail = {'pred': i, 'answer': j, 'correct': False}\n            count += 1\n            if self.is_equal(i, j):\n                correct += 1\n                detail['correct'] = True\n            details.append(detail)\n        result = {'accuracy': 100 * correct / count, 'details': details}\n        return result\n"
````

### F066

Canonical GSM8K dataset config wires gsm8k_postprocess to Gsm8kEvaluator.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`
Path: `opencompass/configs/datasets/gsm8k/gsm8k_gen_1d7fe4.py` lines 23-31
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/configs/datasets/gsm8k/gsm8k_gen_1d7fe4.py#L23-L31
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            ],\n        )),\n    retriever=dict(type=ZeroRetriever),\n    inferencer=dict(type=GenInferencer, max_out_len=512))\n\ngsm8k_eval_cfg = dict(evaluator=dict(type=Gsm8kEvaluator),\n                      pred_postprocessor=dict(type=gsm8k_postprocess),\n                      dataset_postprocessor=dict(type=gsm8k_dataset_postprocess))\n\n"
````

### F067

Olympiad scorer calls the real multi-stage extractor then native edit-distance or positional comparison.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/process_results/math/olympiad/utils.py` lines 27-129
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/process_results/math/olympiad/utils.py#L27-L129
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"def extract_expression_completions_from_generation(generation, debug):\n    numbers = None\n    if 'answer:' in generation.lower():\n        lines = generation.lower().strip().split('\\n')\n        answer_str = None\n        answer_line = None\n        answer_index = None\n        for i, line in enumerate(lines):\n            if 'answer:' in line:\n                answer_line = line\n                answer_index = i\n        answer_str = answer_line.split('answer:')[1].replace('answer:', '').replace('**', '').replace('.', '').strip()\n        if answer_str == '' and answer_index < len(lines) - 1:\n            answer_str = lines[answer_index+1].replace('answer:', '').replace('**', '').replace('.', '').strip()\n        if numbers is None:\n            numbers = []\n        for n in answer_str.split(','):\n            n = n.strip().split(' ')[-1].replace('$', '').replace('{', '').replace('}', '').replace('\\\\', '').replace('boxed', '').replace('<', '').replace('>', '')\n            try:\n                numbers.append(int(n))\n            except:\n                if debug:\n                    print('ERROR', n)\n                numbers.append('NO ANSWER')\n        if len(numbers) == 0 or set(numbers) == {'NO ANSWER'}:\n            numbers = None\n\n    if numbers is None and '\\\\boxed' in generation:\n        boxed = last_boxed_only_string(generation)\n        if boxed is not None:\n            no_box = remove_boxed(boxed)\n            string = no_box\n        else:\n            string = generation\n        string = string.replace('\\\\text{', '').replace('}', '').replace('\\\\', '')\n        numbers = []\n        for n in string.strip().split(','):\n            try:\n                numbers.append(int(n.strip()))\n            except:\n                numbers.append('NO ANSWER')\n        if len(numbers) == 0 or set(numbers) == {'NO ANSWER'}:\n            numbers = None\n\n    if numbers is None:\n        # try just the very last line of the generation\n        last_line = generation.strip().lower().split('\\n')[-1]\n        numbers = []\n        for n in last_line.strip().split(','):\n            n, _ = remove_nonnumeric_chars_at_ends(n)\n            if len(n.strip()) == 0:\n                continue\n            try:\n                numbers.append(int(n.strip()))\n            except:\n                numbers.append('NO ANSWER')\n        if len(numbers) == 0 or set(numbers) == {'NO ANSWER'}:\n            numbers = None\n\n    if numbers is None:\n        # generation has Answer: comma separated list of numbers. I want to extract the last such comma separated list\n        split_string = \"answer:\"\n        numbers = [k.strip() for k in generation.lower().split(split_string)[-1].split(',')]\n\n        # the last number may have some extra non-numeric characters at the end. Those need to be removed\n        new_numbers = []\n        for i, n in enumerate(numbers):\n            n, num_removed = remove_nonnumeric_chars_at_ends(n)\n            if n != '' and n != \"₂\":\n                new_numbers.append(int(n))\n            if (i > 0) and (num_removed > 0):\n                break\n\n        numbers = new_numbers\n    \n    return numbers\n\ndef proof_rearrangement_process_results(ground_truth: str, llm_answer: str, edit_distance=False, debug=False) -> int:\n    ground_truth = [int(n) for n in ground_truth.split(',')]\n\n    completions = extract_expression_completions_from_generation(llm_answer, debug)\n\n    if edit_distance:\n        # `completions` and `ground_truth` are lists of ints (with possible\n        # 'NO ANSWER' sentinels). Use the pure-Python edit distance rather than the\n        # `Levenshtein` package: modern `Levenshtein` (>=0.21) raises\n        # \"TypeError: distance expected two Strings or two Unicodes\" on int lists,\n        # which previously turned every imo/usamo question into an eval_error (score 0).\n        match = levenshtein_distance(completions, ground_truth)\n        # Fraction of the longer sequence that is already correct; guard the empty case.\n        denom = max(len(completions), len(ground_truth))\n        frac_matches = 1 - (match / denom) if denom else 0\n    else:\n        match = [(completions[i] == ground_truth[i]) if i < len(ground_truth) else 0 for i in range(len(completions))]\n        frac_matches = sum(match)/len(match) if len(match) > 0 else 0\n\n    if debug and frac_matches < 1:\n        print('INCORRECT', frac_matches)\n        print('GROUND TRUTH', ground_truth)\n        print('SOLUTION', completions)\n        print('END OF OUTPUT', llm_answer[-1500:])\n\n    return frac_matches\n"
````

### F068

The shipped lm-eval AIME task registers process_results and an explicit 32768-token generation cap.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/tasks/aime/aime.yaml` lines 1-25
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/aime/aime.yaml#L1-L25
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"tag:\n  - math_word_problems\ntask: aime\ndataset_path: gneubig/aime-1983-2024\n# dataset_name: null\noutput_type: generate_until\ntraining_split: train\nfewshot_split: train\ntest_split: train\ndoc_to_text: \"Question: {{Question}}\\nAnswer:\"\ndoc_to_target: \"{{Answer}}\"\nprocess_results: !function utils.process_results\nmetric_list:\n  - metric: exact_match\n    aggregation: mean\n    higher_is_better: true\ngeneration_kwargs:\n  until:\n    - \"Question:\"\n    - \"</s>\"\n    - \"<|im_end|>\"\n    - \"<|eot_id|>\"\n  do_sample: false\n  temperature: 0.0\n  max_gen_toks: 32768\n"
````

### F069

The lm-eval AIME task initializes a dollar-span fallback before optional boxed extraction and returns exact-match scoring.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`
Path: `lm_eval/tasks/aime/utils.py` lines 1-32
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/aime/utils.py#L1-L32
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"import re\nfrom typing import Dict, List\n\n\ndef process_results(doc: dict, results: List[str]) -> Dict[str, int]:\n    retval = 0\n    response = results[0]\n\n    # Try to extract answer from $...$ format first\n    indices = [pos for pos, char in enumerate(response) if char == \"$\"]\n    if len(indices) <= 1:\n        answer = response\n    else:\n        answer = response[indices[0] + 1 : indices[-1]]\n\n    # Extract from \\\\boxed{} if present\n    boxed_answer = last_boxed_only_string(response)\n    if boxed_answer is not None:\n        try:\n            boxed_content = remove_boxed(boxed_answer)\n            if boxed_content is not None:\n                answer = boxed_content\n        except (AssertionError, IndexError):\n            pass\n\n    # Check if answer matches target\n    answer_key = next(k for k in doc.keys() if k.lower() == \"answer\")\n    target = str(doc[answer_key])\n    if is_equiv(answer, target):\n        retval = 1\n\n    return {\"exact_match\": retval}\n"
````

### F070

LiveBench dispatches AIME-shaped tasks to aime_process_results and reserves proof_rearrangement_process_results for IMO and USAMO.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`
Path: `livebench/gen_ground_truth_judgment.py` lines 119-131
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/gen_ground_truth_judgment.py#L119-L131
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````json
"            score = ifbench_process_results(question, llm_answer, debug)\n            category = \"instruction_following\"\n        elif len(splits) > 0 and (splits[0] in [\"amc\", \"smc\", \"aime\", \"imo\", \"usamo\"] or (len(splits) > 1 and splits[1] == \"amc\")):\n            category = \"math\"\n            if splits[0] in [\"amc\", \"smc\"] or (len(splits) > 1 and splits[1] == \"amc\"):\n                score = mathcontest_process_results(ground_truth, llm_answer, question_text, debug)\n                category = \"math\"\n            elif splits[0] == \"aime\":\n                score = aime_process_results(ground_truth, llm_answer, debug)\n                category = \"math\"\n            elif splits[0] in [\"imo\", \"usamo\"]:\n                score = proof_rearrangement_process_results(ground_truth, llm_answer, edit_distance=True, debug=debug)\n            else:\n"
````

## Verification log

Phase 1 receipt gate: `.venv/bin/python ecosystem_audit/validate_receipts.py` (exit 0).

Recorded compound gate exit status: `0` at `2026-08-07T05:11:00.934607+00:00`.

- `PYTHONPATH=trunccheck/src .venv/bin/python -m unittest discover -s trunccheck/tests -v` — exit `0`; 27 tests passed.
- `.venv/bin/python ecosystem_audit/run_executable_audit.py --locked --seed 1729 --check` — exit `0`; two independent regenerations were byte-identical and matched committed outputs.
- `.venv/bin/python ecosystem_audit/verify.py --strict` — exit `0`; 10 targets and 2,950 fixture-pipeline rows verified; full-history clones and receipts checked.
- `MPLCONFIGDIR=/tmp/effort-atlas-mpl PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` — exit `0`; 40 unittest-style tests passed; pre-existing pytest-style tests/test_rescue_analysis.py was not collected.

## Git archaeology and era comparison

`timeline.csv` contains 35 generated setting histories. Status counts: not_traceable=2, verified=33.
Era buckets are generated from author dates: not_traceable=2, o1_to_r1_markers=2, post_r1_marker=16, pre_o1_marker=15. The rows contain 8 evidenced remediation events.

OpenAI o1 (`2024-09`) and DeepSeek R1 (`2025-01`) are supplied contextual era markers, not causal evidence. The history does not support a universal story that every cap predates reasoning models: traced introductions occur both before and after the markers. Several repositories later raised or removed task caps, but their commit messages establish only local motivation, not ecosystem-wide causation.

The supplied local REAP context says o4-mini(high) p90 is 38,125 tokens. That observation is sourced to `TASK.md` only and is not evidence about any external repository’s runtime behavior. It is not compared to `not_traceable` or dynamic settings as if those were numeric caps.

Every verified row preserves exact history commands in `timeline_evidence.json`. OpenCompass AIME and GPQA task-local caps use the required `not found at configs/ searched at ...` form rather than guessing provider defaults.
