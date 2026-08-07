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

Extraction is reported separately from correctness. A returned nonempty value on a truncated fixture is the operational answer-returned event; it is not by itself evidence that answer text was newly invented. Native correctness is used only where the actual downstream path is runnable.

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
| livebench | 5 |
| lm-evaluation-harness | 5 |
| math-verify | 4 |
| matharena | 9 |
| opencompass | 6 |
| simple-evals | 7 |

## Receipt ledger

### F001

Global generation default is 256 tokens and default_gen_kwargs propagates it.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`  
Path: `lm_eval/defaults.py` lines 5-6  
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/defaults.py#L5-L6  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
DEFAULT_MAX_LENGTH = 2048
DEFAULT_MAX_GEN_TOKS = 256
````

### F002

Default generation kwargs place the cap in max_gen_toks.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`  
Path: `lm_eval/defaults.py` lines 38-46  
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/defaults.py#L38-L46  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def default_gen_kwargs(
    until: str | list[str] | None, max_gen_toks: int = DEFAULT_MAX_GEN_TOKS
) -> dict[str, Any]:
    """Returns default generation kwargs for LM evaluation."""
    _gen = {
        "temperature": 0.0,
        "do_sample": False,
        "max_gen_toks": max_gen_toks,
    }
````

### F003

GSM8K CoT omits max_gen_toks and therefore inherits the default through task resolution.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`  
Path: `lm_eval/tasks/gsm8k/gsm8k-cot.yaml` lines 58-63  
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/gsm8k/gsm8k-cot.yaml#L58-L63  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
generation_kwargs:
  do_sample: false
  until:
  - 'Q:'
  - </s>
  - <|im_end|>
````

### F004

GSM8K flexible extraction selects the last regex match with group_select -1.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`  
Path: `lm_eval/tasks/gsm8k/gsm8k-cot.yaml` lines 46-57  
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/tasks/gsm8k/gsm8k-cot.yaml#L46-L57  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
filter_list:
- filter:
  - function: regex
    regex_pattern: The answer is (\-?[0-9\.\,]+).
  - function: take_first
  name: strict-match
- filter:
  - function: regex
    group_select: -1
    regex_pattern: (-?[$0-9.,]{2,})|(-?[0-9]+)
  - function: take_first
  name: flexible-extract
````

### F005

RegexFilter executes findall, indexed selection, tuple collapse, and fallback.

Repository: `EleutherAI/lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`  
Path: `lm_eval/filters/extraction.py` lines 39-58  
Permalink: https://github.com/EleutherAI/lm-evaluation-harness/blob/f4d4b3de3ee6741a7151a9fe74945ee515262f4c/lm_eval/filters/extraction.py#L39-L58  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def apply(
        self, resps: Iterable[Sequence[str]], docs: Sequence[dict[str, Any]]
    ) -> Iterable[list[str]]:
        def filter_set(inst: Sequence[str]) -> list[str]:
            filtered = []
            for resp in inst:
                if not isinstance(resp, str):
                    resp = ""
                match = self.regex.findall(resp)
                if match:
                    match = match[self.group_select]
                    if isinstance(match, tuple):
                        match = [m for m in match if m]
                        if match:
                            match = match[0]
                        else:
                            match = self.fallback
                    match = match.strip()
                else:
                    match = self.fallback
````

### F006

LiteLLM adapter generation defaults max_out_len to 512.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/models/litellm_api.py` lines 106-118  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/litellm_api.py#L106-L118  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def generate(
        self,
        inputs: List[PromptType],
        max_out_len: int = 512,
        **gen_kwargs,
    ) -> List[str]:
        """Generate responses for a batch of inputs.

        Args:
            inputs: list of strings or ``PromptList`` messages.
            max_out_len: max output tokens per response. Defaults to 512.
            **gen_kwargs: extra per-call generation kwargs forwarded to
                LiteLLM, except core request fields managed by this wrapper.
````

### F007

LiteLLM adapter sends max_out_len as max_tokens.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/models/litellm_api.py` lines 234-241  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/litellm_api.py#L234-L241  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
        call_kwargs: Dict = {
            **safe_extra_body,
            **safe_gen_kwargs,
            'model': self.path,
            'messages': messages,
            'max_tokens': max_out_len,
            'drop_params': True,
        }
````

### F008

MATH postprocessor prefers boxed output then final-answer segments then the first period-delimited segment.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/datasets/math.py` lines 190-201  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/datasets/math.py#L190-L201  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
@TEXT_POSTPROCESSORS.register_module('math_postprocess_v2')
def math_postprocess_v2(text: str) -> str:

    cand_ans = extract_boxed_answer(text, strip_double_curly_brace=True)
    if cand_ans:
        return cand_ans

    for maybe_ans in text.split('.'):
        # if 'final answer' in maybe_ans.lower():
        if re.search('final answer|answer is', maybe_ans.lower()):
            return normalize_final_answer(maybe_ans)
    return normalize_final_answer(text.split('.')[0])
````

### F009

Boxed extraction returns None for an unmatched closing brace.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/datasets/math.py` lines 16-41  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/datasets/math.py#L16-L41  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def last_boxed_only_string(string):
    idx = string.rfind('\\boxed')
    if idx < 0:
        idx = string.rfind('\\fbox')
        if idx < 0:
            return None

    i = idx
    right_brace_idx = None
    num_left_braces_open = 0
    while i < len(string):
        if string[i] == '{':
            num_left_braces_open += 1
        if string[i] == '}':
            num_left_braces_open -= 1
            if num_left_braces_open == 0:
                right_brace_idx = i
                break
        i += 1

    if right_brace_idx is None:
        retval = None
    else:
        retval = string[idx:right_brace_idx + 1]

    return retval
````

### F010

Streaming OpenAI adapter captures and logs finish_reason.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/models/openai_streaming.py` lines 257-267  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/models/openai_streaming.py#L257-L267  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
                # Check if streaming is finished
                if chunk.choices[0].finish_reason is not None:
                    finish_reason = chunk.choices[0].finish_reason
                    if self.verbose:
                        print()  # Add newline after streaming complete
                        elapsed = current_time - start_time
                        log_with_thread(
                            f'Streaming finished with reason: '
                            f'{chunk.choices[0].finish_reason}, '
                            f'chunks: {chunk_count}, elapsed: {elapsed:.1f}s')
                    break
````

### F011

OpenICL evaluator aggregates finish reasons into results.

Repository: `open-compass/opencompass` at `96263b1a16899260586c8e945eea06934c43c225`  
Path: `opencompass/tasks/openicl_eval.py` lines 384-400  
Permalink: https://github.com/open-compass/opencompass/blob/96263b1a16899260586c8e945eea06934c43c225/opencompass/tasks/openicl_eval.py#L384-L400  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
            for pred_sample in replica_pred_strs:
                replica_total_neg_logprob += pred_sample['rollout'][
                    'sum_neg_logprob']
                replica_total_tokens += pred_sample['rollout']['num_tokens']
                replica_finish_counts[pred_sample['rollout']
                                      ['finish_reason']] += 1
                if pred_sample['rollout']['num_tokens'] > 0:
                    replica_successful_samples += 1

            replica_entropy_nats = replica_total_neg_logprob / replica_total_tokens
            replica_avg_length = replica_total_tokens / replica_successful_samples if replica_successful_samples > 0 else 0.0

            result[f'{i}_th rollout results'] = dict(
                total_neg_logprob=replica_total_neg_logprob,
                total_tokens=replica_total_tokens,
                finish_reason=replica_finish_counts,
                successful_samples=replica_successful_samples,
````

### F012

Request schema defaults max_tokens to 100.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/common/request.py` lines 39-43  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/common/request.py#L39-L43  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    top_k_per_token: int = 1
    """Take this many highest probability candidates per token in the completion"""

    max_tokens: int = 100
    """Maximum number of tokens to generate (per completion)"""
````

### F013

Together client copies provider finish_reason into GeneratedOutput.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/clients/together_client.py` lines 307-315  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/clients/together_client.py#L307-L315  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
            raw_finish_reason: Optional[str] = raw_completion.get("finish_reason")
            finish_reason: Optional[Dict] = {"reason": raw_finish_reason} if raw_finish_reason else None

            completion = GeneratedOutput(
                text=cleanup_str(raw_completion["text"], "together"),
                logprob=sequence_logprob,
                tokens=tokens,
                finish_reason=finish_reason,
            )
````

### F014

Basic metrics expose length, stop, endoftext, and unknown finish-reason counters.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/metrics/basic_metrics.py` lines 432-451  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/basic_metrics.py#L432-L451  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def _compute_finish_reason_metrics(
    adapter_spec: AdapterSpec, request_state: RequestState, metric_service: MetricService
) -> List[Stat]:
    """Record how often generation finished due to reaching token limit, stop token(s), or end of text"""
    assert request_state.result is not None
    sequence = request_state.result.completions[0]
    valid_reasons = [
        "length",
        "stop",
        "endoftext",
        "unknown",
    ]
    if sequence.finish_reason is None or sequence.finish_reason["reason"] not in valid_reasons:
        reason = "unknown"
    else:
        reason = sequence.finish_reason["reason"]
    return [
        Stat(MetricName(f"finish_reason_{valid_reason}")).add(int(reason == valid_reason))
        for valid_reason in valid_reasons
    ]
````

### F015

BasicGenerationMetric invokes reference metrics on generated request state.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/metrics/basic_metrics.py` lines 199-215  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/basic_metrics.py#L199-L215  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def evaluate_generation(
        self,
        adapter_spec: AdapterSpec,
        request_state: RequestState,
        metric_service: MetricService,
        eval_cache_path: str,
    ) -> List[Stat]:
        """Compute all metrics."""
        stats: List[Stat] = []
        stats.extend(compute_request_state_metrics(self.efficiency_metric, adapter_spec, request_state, metric_service))

        if len(request_state.instance.references) > 0:
            stats.extend(compute_reference_metrics(self.names, adapter_spec, request_state, metric_service))

        stats.extend(compute_language_modeling_metrics(adapter_spec, request_state, metric_service))

        return stats
````

### F016

GenerateConfig leaves max_tokens unset and delegates the default to the model.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`  
Path: `src/inspect_ai/model/_generate_config.py` lines 198-220  
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_generate_config.py#L198-L220  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
class GenerateConfig(BaseModel):
    """Model generation options."""

    max_retries: int | None = Field(default=None)
    """Maximum number of times to retry request, so e.g. 1 allows two attempts total (defaults to unlimited)."""

    timeout: int | None = Field(default=None)
    """Timeout (in seconds) for an entire request (including retries)."""

    attempt_timeout: int | None = Field(default=None)
    """Timeout (in seconds) for any given attempt (if exceeded, will abandon attempt and retry according to max_retries)."""

    max_connections: int | None = Field(default=None)
    """Maximum number of concurrent connections to Model API (default is model specific)."""

    adaptive_connections: bool | int | AdaptiveConcurrency | None = Field(default=None)
    """Adaptive concurrency for model API connections. Defaults to enabled (`None` and `True` both resolve to `AdaptiveConcurrency()` defaults: min=10, start=20, max=100). Pass `False` to opt out (uses static concurrency). Pass an integer `N` as shorthand for `AdaptiveConcurrency(max=N)`. Pass an `AdaptiveConcurrency` to fully customize bounds and tuning (cooldown_seconds, decrease_factor, scale_up_percent). An explicit `max_connections` or `batch=True` takes precedence and uses static concurrency."""

    system_message: str | None = Field(default=None)
    """Override the default system message."""

    max_tokens: int | None = Field(default=None)
    """The maximum number of tokens that can be generated in the completion (default is model specific)."""
````

### F017

Model output stores stop_reason and normalizes legacy length to max_tokens.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`  
Path: `src/inspect_ai/model/_model_output.py` lines 224-256  
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_model_output.py#L224-L256  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
class ChatCompletionChoice(BaseModel):
    """Choice generated for completion."""

    message: ChatMessageAssistant
    """Assistant message."""

    stop_reason: StopReason = Field(default="unknown")
    """Reason that the model stopped generating."""

    stop_details: StopDetails | None = Field(default=None)
    """Additional detail about the stop reason (e.g. refusal category/explanation), when provided."""

    logprobs: Logprobs | None = Field(default=None)
    """Logprobs."""

    prompt_logprobs: Logprobs | None = Field(default=None)
    """Per-prompt-token log probabilities (vLLM only).

    Placed on the choice (not ``ModelOutput``) so scorers access prompt
    and output logprobs uniformly via ``choices[0]``.  Perplexity evals
    use ``num_choices=1``, so there is no duplication in practice."""

    @model_validator(mode="before")
    @classmethod
    def migrate_stop_reason(cls: Type["ChatCompletionChoice"], values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        if "stop_reason" in values:
            stop_reason = values["stop_reason"]
            if stop_reason == "length":
                values["stop_reason"] = "max_tokens"

        return values
````

### F018

Core match supports end-position numeric scoring after normalization.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`  
Path: `src/inspect_ai/scorer/_match.py` lines 9-42  
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/scorer/_match.py#L9-L42  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def match(
    location: Literal["begin", "end", "any", "exact"] = "end",
    *,
    ignore_case: bool = True,
    numeric: bool = False,
) -> Scorer:
    """Scorer which matches text or a number.

    Args:
       location: Location to match at. "any" matches anywhere in the
          output; "exact" requires the output be exactly
          equal to the target (module whitespace, etc.)
       ignore_case: Do case insensitive comparison.
       numeric: Is this a numeric match? When True, currency symbols
          (`$`, `€`, `£`), thousands separators (`,`), and formatting
          markers (`*`, `_`) are stripped before numbers are normalized
          and compared. The percent sign is not stripped: `60%` is
          ambiguous (it could mean `60` or `0.6`), so an answer of `60%`
          will not match a numeric target of `60`. To accept a
          percentage-formatted answer, pass both forms as targets, e.g.
          `Target(["60", "60%"])`, where the non-numeric `"60%"` is
          matched as a string.
    """

    def check(value: str, target: str) -> tuple[str, bool]:
        return match_str(
            value=value,
            target=target,
            location=location,
            ignore_case=ignore_case,
            numeric=numeric,
        )

    return str_match_scorer(check)
````

### F019

AIME 2026 task provides no GenerateConfig, so core model-specific cap resolution applies.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`  
Path: `src/inspect_evals/aime2026/aime2026.py` lines 16-34  
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/aime2026/aime2026.py#L16-L34  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
@task
def aime2026() -> Task:
    """Inspect Task implementation for the AIME 2026 benchmark."""
    dataset = hf_dataset(
        path=DATASET_PATH,
        split="test",
        sample_fields=record_to_sample,
        revision=AIME2026_DATASET_REVISION,
    )

    return Task(
        dataset=dataset,
        solver=aime_solver(),
        scorer=[
            aime_scorer(),
        ],
        version=EVAL_VERSION.comparability_version,
        metadata=EVAL_VERSION.to_metadata(),
    )
````

### F020

AIME scorer takes the last nonempty line, removes boxed syntax, and invokes numeric match; empty output is incorrect.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`  
Path: `src/inspect_evals/utils/aime_common.py` lines 37-59  
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/utils/aime_common.py#L37-L59  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
@scorer(metrics=[accuracy(), stderr()])
def aime_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        raw = state.output.completion
        lines = raw.strip().splitlines()
        if not lines:
            return Score(
                value=INCORRECT,
                explanation="Model produced empty completion",
            )
        last_line = lines[-1]
        cleaned = remove_boxed_from_ans(last_line)
        state.output.completion = cleaned

        result = await match(numeric=True)(state, target)
        if result is None:
            raise ValueError("No result found")

        result.metadata = {"unprocessed_answer": raw, "cleaned_answer": cleaned}

        return result

    return score
````

### F021

TAC explicitly raises the task cap to 16384 at medium reasoning effort.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`  
Path: `src/inspect_evals/tac/tac.py` lines 48-58  
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/tac/tac.py#L48-L58  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
            confirm_to_complete(),
        ],
        scorer=tac_scorer(),
        epochs=3,
        max_messages=30,
        version=EVAL_VERSION.comparability_version,
        metadata=EVAL_VERSION.to_metadata(),
        config=GenerateConfig(
            max_tokens=16384,
            reasoning_effort="medium",
        ),
````

### F022

ChatCompletionSampler defaults max_tokens to 1024.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `sampler/chat_completion_sampler.py` lines 21-34  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/sampler/chat_completion_sampler.py#L21-L34  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        system_message: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ):
        self.api_key_name = "OPENAI_API_KEY"
        self.client = OpenAI()
        # using api_key=os.environ.get("OPENAI_API_KEY")  # please set your API_KEY
        self.model = model
        self.system_message = system_message
        self.temperature = temperature
        self.max_tokens = max_tokens
````

### F023

MATH extracts ANSWER_PATTERN group 1 or None and passes it to the equality checker.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `math_eval.py` lines 45-60  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/math_eval.py#L45-L60  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def __call__(self, sampler: SamplerBase) -> EvalResult:
        def fn(row: dict):
            prompt_messages = [
                sampler._pack_message(content=QUERY_TEMPLATE.format(**row), role="user")
            ]
            sampler_response = sampler(prompt_messages)
            response_text = sampler_response.response_text
            actual_queried_prompt_messages = sampler_response.actual_queried_message_list
            match = re.search(ANSWER_PATTERN, response_text)
            extracted_answer = match.group(1) if match else None
            score = float(check_equality(self.equality_checker, row["Answer"], extracted_answer))
            html = common.jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=actual_queried_prompt_messages,
                next_message=dict(content=response_text, role="assistant"),
                score=score,
                correct_answer=row["Answer"],
````

### F024

GPQA extracts one regex group or None and compares it to the shuffled correct letter.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `gpqa_eval.py` lines 56-67  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/gpqa_eval.py#L56-L67  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
            sampler_response = sampler(prompt_messages)
            response_text = sampler_response.response_text
            actual_queried_prompt_messages = sampler_response.actual_queried_message_list
            match = re.search(ANSWER_PATTERN_MULTICHOICE, response_text)
            extracted_answer = match.group(1) if match else None
            score = 1.0 if extracted_answer == correct_answer else 0.0
            html = common.jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=actual_queried_prompt_messages,
                next_message=dict(content=response_text, role="assistant"),
                score=score,
                correct_answer=correct_answer,
                extracted_answer=extracted_answer,
````

### F025

Task generation_size defaults to None.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/lighteval_task.py` lines 137-140  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/lighteval_task.py#L137-L140  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    # Generation args
    generation_size: int | None = None
    generation_grammar: TextGenerationInputGrammarType | None = None
    stop_sequence: ListLike[str] | None = None
````

### F026

Transformers resolves max_new_tokens from model generation parameters or task generation_size.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/models/transformers/transformers_model.py` lines 559-564  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/models/transformers/transformers_model.py#L559-L564  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
                # stop_tokens and max_tokens genrated) which is not necessarily
                # the case! Because of that we only use batch size of 1
                stop_tokens = split[0].stop_sequence

            max_new_tokens = self.config.generation_parameters.max_new_tokens or split[0].generation_size
            returns_logits = split[0].use_logits
````

### F027

AIME 24 explicitly leaves generation_size None.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/aime.py` lines 64-78  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/aime.py#L64-L78  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
aime24 = LightevalTaskConfig(
    name="aime24",
    prompt_function=aime_prompt,
    sample_fields=record_to_sample,
    solver=[prompt_template(MATH_PROMPT_TEMPLATE), generate(cache=True)],
    scorer=math_scorer(),
    hf_repo="HuggingFaceH4/aime_2024",
    hf_subset="default",
    hf_avail_splits=["train"],
    evaluation_splits=["train"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=None,
    metrics=[Metrics.pass_at_k_math(sample_params={"k": 1}), Metrics.avg_at_n_math(sample_params={"n": 1})],
    version=2,
````

### F028

GPQA multiple choice sets generation_size to one and a newline stop.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/gpqa.py` lines 108-124  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gpqa.py#L108-L124  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
gpqa = LightevalTaskConfig(
    name="gpqa:mc",
    prompt_function=gpqa_prompt,
    sample_fields=record_to_sample,
    sample_to_fewshot=sample_to_fewshot,
    solver=[multiple_choice(cache=True)],
    scorer=choice(),
    hf_repo="Idavidrein/gpqa",
    hf_subset="gpqa_main",
    hf_avail_splits=["train"],
    evaluation_splits=["train"],
    few_shots_split=None,
    few_shots_select="random_sampling",
    generation_size=1,
    metrics=[Metrics.loglikelihood_acc],
    stop_sequence=["\n"],
    version=0,
````

### F029

Extractive match sorts matches rightmost-first and can append the first failed-parse string fallback.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/metrics/utils/extractive_match_utils.py` lines 590-632  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/metrics/utils/extractive_match_utils.py#L590-L632  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    # Get all patterns and sort by priority
    all_patterns = [
        (pattern, target_type, priority)
        for target_patterns, target_type in target_res
        for pattern, priority in target_patterns
    ]
    match_found = False

    # Group patterns by priority using itertools.groupby
    for _, patterns_group in groupby(sorted(all_patterns, key=lambda x: x[2]), key=lambda x: x[2]):
        # Find all matches for each pattern in this priority group
        matches_with_pos = (
            (match, match.start(), match.end(), target_type)
            for pattern, target_type, _ in patterns_group
            for match in pattern.finditer(pred)
        )

        # Sort matches by end position (rightmost first) and then by start position (leftmost first)
        matches_with_pos = sorted(matches_with_pos, key=lambda x: (x[2], -x[1]), reverse=True)

        # Try to extract from each match, starting from rightmost
        for match, _, _, target_type in matches_with_pos:
            extracted_match, str_fallback = extract_match(match, target_type, timeout_seconds)
            match_found = True

            if str_fallback:
                fallbacks.append(str_fallback)

            if extracted_match is not None:
                extracted_predictions.append(extracted_match)
                break

            if extraction_mode == "first_match":
                break

        # If we found something and we're in first_match mode, stop processing other priorities
        if extracted_predictions or (match_found and extraction_mode == "first_match"):
            break

    if fallback_mode == "first_match" and fallbacks:
        extracted_predictions += [fallbacks[0]]

    return extracted_predictions
````

### F030

Generation CLI defaults the maximum new-token allowance to 4096.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`  
Path: `livebench/gen_api_answer.py` lines 380-388  
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/gen_api_answer.py#L380-L388  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    parser.add_argument(
        "--force-temperature", type=float, help="Forcibly set a sampling temperature."
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="The maximum number of new generated tokens.",
    )
````

### F031

AIME scoring marks correct when gold occurs anywhere in the last 50 characters.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`  
Path: `livebench/process_results/math/math_competitions/utils.py` lines 87-104  
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/process_results/math/math_competitions/utils.py#L87-L104  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def aime_process_results(ground_truth: str, llm_answer: str, debug=False) -> int:
    score = 0

    # extract text from <solution></solution> tags
    solution_matches = re.findall(r'<solution>(.*?)</solution>', llm_answer)
    if len(solution_matches) > 0:
        solution_match = solution_matches[-1]
        if len(set(solution_match)) == 1 and next(iter(set(solution_match))).lower() == ground_truth.lower():
            score = 1

    if score == 0 and ground_truth in llm_answer[-50:]:
        score = 1

    if debug and score == 0:
        print('INCORRECT')
        print('GROUND TRUTH', ground_truth)
        print('SOLUTION', llm_answer[-200:])
    return score
````

### F032

Math contest scoring includes last-boxed, trailing-value, and last-line/parenthesis fallbacks.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`  
Path: `livebench/process_results/math/math_competitions/utils.py` lines 22-50  
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/process_results/math/math_competitions/utils.py#L22-L50  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    parsed_answer = None

    allow_boxed = True
    if score == 0 and allow_boxed:
        llm_answer = llm_answer.replace("\\\\fbox{", "\\\\boxed{")
        last_boxed = last_boxed_only_string(llm_answer)
        if last_boxed:
            last_boxed_res = remove_boxed(last_boxed).replace('\\text{', '').replace('}', '').replace('\\', '').lower()
            if last_boxed_res in {'a', 'b', 'c', 'd', 'e'}:
                parsed_answer = last_boxed_res
            if parsed_answer == ground_truth.lower():
                score = 1

    allow_answer_values = True
    if score == 0 and allow_answer_values:
        value = extract_answer(question_text, ground_truth)
        length_to_check = 20 + len(value)
        if value in llm_answer[-length_to_check:]:
            score = 1

    allow_last_line = True
    if score == 0 and allow_last_line:
        last_line = llm_answer.strip().split('\n')[-1]
        if last_line.strip().replace('*', '').lower() == ground_truth.lower():
            score = 1
        elif '(' in last_line and ')' in last_line:
            val = last_line.split('(')[1].split(')')[0]
            if val.lower() == ground_truth.lower():
                score = 1
````

### F033

Anthropic completion path records an empty answer with token_exhaustion instead of retrying when reasoning consumes the cap.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`  
Path: `livebench/model/completions.py` lines 578-587  
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/model/completions.py#L578-L587  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    text_messages = [c for c in message if c['type'] == 'text' and c.get('text', '').strip()]
    if len(text_messages) == 0:
        block_types = [c['type'] for c in message]
        if stop_reason == 'max_tokens':
            # Token exhaustion: the entire max_tokens budget went to the thinking
            # block, leaving no final answer. Match the litellm path -- record an
            # empty answer + eval_status so it grades as a genuine 0 (a real model
            # failure), not a hard infra $ERROR$. Do NOT retry-chase token limits.
            _md: dict[str, Any] = {'eval_status': 'token_exhaustion'}
            _out = -1
````

### F034

Public parse defaults to LaTeX/expression extraction and first-match string fallback.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`  
Path: `src/math_verify/parser.py` lines 649-682  
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/parser.py#L649-L682  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def parse(
    pred: str,
    extraction_config: Sequence[ExtractionTarget] = [
        LatexExtractionConfig(),
        ExprExtractionConfig(),
    ],
    fallback_mode: Literal["no_fallback", "first_match"] = "first_match",
    extraction_mode: Literal["first_match", "any_match"] = "any_match",
    parsing_timeout: int = 5,
    raise_on_error: bool = False,
):
    """Extracts and parses mathematical expressions from a prediction string.

    This function attempts to extract mathematical expressions from text using various strategies
    (LaTeX, plain expressions, etc.) and converts them to SymPy objects.

    Args:
        pred (str): The prediction string to parse.
        extraction_config (Sequence[ExtractionTarget], optional): Configuration for what types of expressions
            to extract and how to extract them. Defaults to [LatexExtractionConfig(), ExprExtractionConfig()].
        fallback_mode (Literal["no_fallback", "first_match"], optional): How to handle extraction failures. Defaults to "first_match".
            - "no_fallback": Return only successfully parsed expressions
            - "first_match": Include the first string match even if parsing failed
        extraction_mode (Literal["first_match", "any_match"], optional): Strategy for extracting matches. Defaults to "any_match".
            - "first_match": Stop after finding the first match
            - "any_match": Try to extract all possible matches, stops after first sucesful parsing attempt
        parsing_timeout (int, optional): Maximum time in seconds to spend parsing each expression. Defaults to 3. Any timeout seconds > 0 or not None will result in the function to raise a ValueError if it's called in a threaded environment.
        raise_on_error (bool, optional): Whether to raise an exception if an error occurs during parsing or return an empty list. Defaults to False.

    Returns:
        list: List of extracted predictions. Each prediction can be:
            - SymPy expression (for successfully parsed mathematical expressions)
            - String (for fallback matches when fallback_mode="first_match")
            Empty list if no matches are found.
````

### F035

Public parse invokes the real regex/extraction pipeline under a timeout.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`  
Path: `src/math_verify/parser.py` lines 700-706  
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/parser.py#L700-L706  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    try:
        target_res = get_extraction_regexes(extraction_config)
        return timeout(timeout_seconds=parsing_timeout)(extract_target_from_pred)(
            pred,
            target_res,
            fallback_mode=fallback_mode,
            extraction_mode=extraction_mode,
````

### F036

Public verify compares parsed gold and target with native mathematical strategies.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`  
Path: `src/math_verify/grader.py` lines 755-773  
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/grader.py#L755-L773  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def verify(
    gold: list[Basic | MatrixBase | str] | Basic | MatrixBase | str,
    target: list[Basic | MatrixBase | str] | Basic | MatrixBase | str,
    float_rounding: int = 6,
    numeric_precision: int = 15,
    strict: bool = True,
    allow_set_relation_comp: bool = False,
    timeout_seconds: int | None = 5,
    raise_on_error: bool = False,
) -> bool:
    """Verifies if the target expression matches the gold expression using multiple comparison strategies.

    This function implements a comprehensive comparison system for mathematical expressions,
    handling various types of mathematical objects (numbers, expressions, sets, matrices, etc.)
    with multiple fallback strategies.

    Note:
        - It's expected that both gold and pred has been parsed with math_verify.parse function.
        - Function is not symmetric, gold answer should be passed as gold and prediction as pred. The non-symmetric nature appears at assignment simplification and equation interval conversion.
````

### F037

DeepSeek R1 model config sets max_tokens to 32000.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `configs/models/deepseek/deepseek_r1.yaml` lines 1-5  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/configs/models/deepseek/deepseek_r1.yaml#L1-L5  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
model: deepseek-ai/DeepSeek-R1
api: together
max_tokens: 32000
temperature: 0.6
top_p: 0.95
````

### F038

Non-strict parser falls back to the last integer; strict parsing suppresses that fallback.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/parser.py` lines 346-395  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/parser.py#L346-L395  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def extract_last_integer(text: str) -> Optional[int]:
    """Extracts the last integer from a string.

    Args:
        text (str): The string to search.

    Returns:
        tuple: A tuple containing the last integer and a warning level.
    """
    pattern = r"\b\d+\b"
    matches = list(regex.finditer(pattern, text))
    if not matches:
        return None, WarningType.MAJOR
    try:
        return int(matches[-1].group()), WarningType.MAJOR
    except Exception as e:
        logger.warning(f"Error extracting last integer: {e}")
        return None, WarningType.MAJOR


def extract_answer(
    text: str, strict_parsing: bool = True, parse: bool = True, list_answer: bool = False, typed_delimiters: bool = True
):
    """Extracts and parses the final answer from a string.

    Args:
        text (str): The string to search.
        strict_parsing (bool, optional): Whether to use strict parsing. Defaults to True.
        parse (bool, optional): Whether to parse the answer. Defaults to True.
        list_answer (bool, optional): Whether to expect a list of answers. Defaults to False.

    Returns:
        tuple: A tuple containing the parsed answer and a warning level.
    """
    if text is None or len(text) == 0:
        return None, WarningType.MAJOR
    warning_old = WarningType.NONE
    if text in complete_mapper:
        text = complete_mapper[text]
        warning_old = WarningType.MAJOR
    text, warning = replace_unicode(text)
    warning = max(warning, warning_old)
    answer, warning_new = extract_boxed_answer_parse(text, parse, list_answer, typed_delimiters=typed_delimiters)
    if isinstance(answer, AnswerList) and len(answer.answers) == 1:
        answer = answer.answers[0]
    warning = max(warning, warning_new)
    if answer is not None or strict_parsing:
        return answer, warning

    return extract_last_integer(text)
````

### F039

Competition grader sends the last assistant message through the configured real parser.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/grader.py` lines 152-189  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/grader.py#L152-L189  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def extract_and_grade(messages, output_tokens, gold_answer, competition_config, problem=None, debug_info=""):
    """
    Grade the model's messages against the gold answer.

    Args:
        messages (list): The list of message dictionaries from the model (clean format).
        gold_answer (str): The gold answer as string.

    Returns:
        tuple: (answer, is_correct, warning)
    """

    is_final_answer = competition_config.get("final_answer", True)
    is_lean_comp = competition_config.get("lean", False)
    use_strict_parsing = competition_config.get("strict_parsing", False)
    use_exact_match = competition_config.get("exact_match_parsing", False)
    use_typed_delimiters = competition_config.get("typed_delimited_answers", True)

    is_broken, reason = is_conversation_broken(messages)
    if is_broken:
        raise ValueError(f"Message list is broken: {reason}")

    if is_lean_comp:
        return grade_lean_submission(messages, competition_config, problem, debug_info=debug_info)

    gold_answer_is_list = is_final_answer and "," in gold_answer

    last_message = messages[-1]["content"]
    if use_exact_match:
        model_answer, warning = extract_boxed_answer(last_message, list_answer=gold_answer_is_list)
    else:
        model_answer, warning = extract_answer(
            last_message,
            strict_parsing=use_strict_parsing,
            parse=True,
            list_answer=gold_answer_is_list,
            typed_delimiters=use_typed_delimiters,
        )
````

### F040

Shipped MATH-Hard task sets generation_size to 1024 and uses the public parser-backed metric.

Repository: `huggingface/Math-Verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`  
Path: `src/math_verify/tasks.py` lines 167-190  
Permalink: https://github.com/huggingface/Math-Verify/blob/ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b/src/math_verify/tasks.py#L167-L190  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
math_hard_lighteval = [
    LightevalTaskConfig(
        name=f"math_hard:{subset}",
        suite=["lighteval", "math"],
        prompt_function=math_hard_prompt_function,
        hf_repo="lighteval/MATH-Hard",
        hf_subset=subset,
        evaluation_splits=["test"],
        few_shots_split="train",
        generation_size=1024,
        metric=[
            as_lighteval_metric(
                math_metric(
                    gold_extraction_target=(
                        LatexExtractionConfig(boxed_match_priority=0),
                    ),
                    pred_extraction_target=(
                        LatexExtractionConfig(),
                        ExprExtractionConfig(),
                    ),
                )
            ),
        ],
        stop_sequence=["\nQuestion:", "\nProblem:", "\nquestion:", "\nproblem:"],
````

### F041

APIClient has no numeric max-token default.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/api_client.py` lines 51-56  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L51-L56  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def __init__(
        self,
        model,
        timeout=30000,
        max_tokens=None,
        api="openai",
````

### F042

MathArena maps reasoning model token fields and injects a cap only when model configuration is non-null.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/api_client.py` lines 125-150  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L125-L150  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
        # Adapt model name and other args to the model
        if "--" in model:
            model, reasoning_effort = model.split("--")
            logger.info(f"Model: {model}, Reasoning effort: {reasoning_effort}")
        if (api not in ["anthropic", "openai"] or self.tool_calls_allowed) and batch_processing:
            logger.warning("Batch processing is only supported for the Anthropic API and OpenAI API without tool calling.")
            batch_processing = False
        if ("o1" in model or "o3" in model or "o4" in model or "gpt-5" in model) and api == "openai":
            logger.info("Not using system messages for o1/o3/o4 model.")
            no_system_messages = True  # o1 model cannot handle system messages
            if not use_openai_responses_api:
                max_tokens_param = "max_completion_tokens"
        if use_openai_responses_api and not batch_processing:
            max_tokens_param = "max_output_tokens"
        if self.tool_calls_allowed and not use_openai_responses_api and not api == "anthropic":
            max_tokens_param = "max_completion_tokens"
        self._kwarg_remover(api, model, kwargs)

        self.model = model
        self.kwargs = kwargs
        self.max_tokens_param = max_tokens_param
        self.context_limit = context_limit
        self.max_tokens = max_tokens
        if max_tokens is not None:
            self.kwargs[max_tokens_param] = max_tokens
        self.timeout = timeout
````

### F043

AIME 2025 sets non-strict parsing but no competition-level generation cap.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `configs/competitions/aime/aime_2025.yaml` lines 1-5  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/configs/competitions/aime/aime_2025.yaml#L1-L5  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
instruction: "Put your final answer within \\boxed{{}}.\nThe answer is an integer between 0 and 999 inclusive."
strict_parsing: false
n_problems: 30
date: "2025-02-12"
dataset_path: MathArena/aime_2025
````

### F044

GSM8K sets generation_size to 256.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/gsm8k.py` lines 67-85  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gsm8k.py#L67-L85  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
gsm8k = LightevalTaskConfig(
    name="gsm8k",
    prompt_function=gsm8k_prompt,
    sample_fields=record_to_sample,
    sample_to_fewshot=sample_to_fewshot,
    solver=[prompt_template(MATH_PROMPT_TEMPLATE), generate(cache=True)],
    scorer=math_scorer(),
    hf_repo="openai/gsm8k",
    hf_subset="main",
    hf_avail_splits=["train", "test"],
    evaluation_splits=["test"],
    few_shots_split=None,
    few_shots_select="random_sampling_from_train",
    generation_size=256,
    metrics=[
        Metrics.expr_gold_metric,
    ],
    stop_sequence=["Question:"],
    version=0,
````

### F045

Legacy MATH algebra sets generation_size to 2048.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/math.py` lines 35-56  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/math.py#L35-L56  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
math_algebra = LightevalTaskConfig(
    name="math:algebra",
    prompt_function=math_prompt,
    hf_repo="DigitalLearningGmbH/MATH-lighteval",
    hf_subset="algebra",
    hf_avail_splits=["train", "test"],
    evaluation_splits=["test"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=2048,
    metrics=[
        Metrics.maj_at_n(
            sample_params={
                "n": 4,
                "strip_strings": True,
                "normalize_pred": math_normalizer,
                "normalize_gold": math_normalizer,
            }
        ),
    ],
    stop_sequence=["\n"],
    version=1,
````

### F046

MATH-500 sets generation_size to 32768.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/math_500.py` lines 58-75  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/math_500.py#L58-L75  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
math_500 = LightevalTaskConfig(
    name="math_500",
    prompt_function=math_500_prompt,
    hf_repo="HuggingFaceH4/MATH-500",
    hf_subset="default",
    hf_avail_splits=["test"],
    evaluation_splits=["test"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=32768,
    metrics=[
        Metrics.pass_at_k_math(sample_params={"k": 1, "n": 1}),
    ],
    version=2,
    sample_fields=record_to_sample,
    solver=[prompt_template(MATH_QUERY_TEMPLATE), generate(cache=True)],
    scorer=model_graded_fact(),
)
````

### F047

Generative GPQA variants set generation_size to 32768 for reasoning models.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/tasks/tasks/gpqa.py` lines 127-180  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/tasks/tasks/gpqa.py#L127-L180  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
gpqa_diamond_instruct = LightevalTaskConfig(
    name="gpqa:diamond",
    prompt_function=gpqa_instruct_prompt,
    sample_fields=record_to_sample,
    sample_to_fewshot=sample_to_fewshot,
    solver=[multiple_choice(cache=True)],
    scorer=choice(),
    hf_repo="Idavidrein/gpqa",
    hf_subset="gpqa_diamond",
    hf_avail_splits=["train"],
    evaluation_splits=["train"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=32768,  # needed for reasoning models like R1
    metrics=[Metrics.gpqa_instruct_pass_at_k(sample_params={"k": 1})],
    stop_sequence=[],  # no stop sequence, will use eos token
    version=1,
)

gpqa_extended_instruct = LightevalTaskConfig(
    name="gpqa:extended",
    prompt_function=gpqa_instruct_prompt,
    sample_fields=record_to_sample,
    sample_to_fewshot=sample_to_fewshot,
    solver=[multiple_choice(cache=True)],
    scorer=choice(),
    hf_repo="Idavidrein/gpqa",
    hf_subset="gpqa_extended",
    hf_avail_splits=["train"],
    evaluation_splits=["train"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=32768,  # needed for reasoning models like R1
    metrics=[Metrics.gpqa_instruct_metric],
    stop_sequence=[],  # no stop sequence, will use eos token
    version=0,
)

gpqa_main_instruct = LightevalTaskConfig(
    name="gpqa:main",
    prompt_function=gpqa_instruct_prompt,
    sample_fields=record_to_sample,
    sample_to_fewshot=sample_to_fewshot,
    solver=[multiple_choice(cache=True)],
    scorer=choice(),
    hf_repo="Idavidrein/gpqa",
    hf_subset="gpqa_main",
    hf_avail_splits=["train"],
    evaluation_splits=["train"],
    few_shots_split=None,
    few_shots_select=None,
    generation_size=32768,  # needed for reasoning models like R1
    metrics=[Metrics.gpqa_instruct_metric],
    stop_sequence=[],  # no stop sequence, will use eos token
````

### F048

Main runner overrides sampler caps to 2048 for GPT-4.1 configurations.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `simple_evals.py` lines 213-223  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/simple_evals.py#L213-L223  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
        # GPT-4.1 models
        "gpt-4.1": ChatCompletionSampler(
            model="gpt-4.1-2025-04-14",
            system_message=OPENAI_SYSTEM_MESSAGE_API,
            max_tokens=2048,
        ),
        "gpt-4.1-temp-1": ChatCompletionSampler(
            model="gpt-4.1-2025-04-14",
            system_message=OPENAI_SYSTEM_MESSAGE_API,
            max_tokens=2048,
            temperature=1.0,
````

### F049

RequestLogger can persist a redacted raw provider response.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/request_logger.py` lines 100-129  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/request_logger.py#L100-L129  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def log_response(self, ts, batch_idx, response=None, **info):
        if not self.enabled:
            return
        try:
            problem_idx, logfile = self._logfile(ts, batch_idx)
            if not os.path.exists(logfile):
                logger.warning(f"Can't log response, log file does not exist: {logfile}")
                return

            try:
                with open(logfile, "r", encoding="utf-8") as f:
                    data = json.load(f, object_pairs_hook=OrderedDict)
            except Exception as exc:
                logger.warning(f"Recovering response log after unreadable request log {logfile}: {exc}")
                data = OrderedDict(
                    {
                        "comp_name": self.comp_name,
                        "solver_name": self.solver_name,
                        "timestamp": ts,
                        "problem_idx": problem_idx,
                        "batch_idx": batch_idx,
                        "request_log_error": str(exc),
                    }
                )

            # Update the data with the response information
            data["response_info"] = info
            if response is not None:
                data["response"] = self._redact_for_logging(response)
            self._write_json(logfile, data)
````

### F050

Semantic InternalRequestResult drops finish reason and retains only conversation, token counts, retries, and time.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/api_client.py` lines 332-342  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/api_client.py#L332-L342  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    class InternalRequestResult:
        """A class to hold the result of a request internally (below run_queries)."""

        def __init__(self, conversation, input_tokens, output_tokens, cached_input_tokens=0, cached_write_tokens=0, n_retries=0, time=0):
            self.conversation = conversation
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.cached_input_tokens = cached_input_tokens
            self.cached_write_tokens = cached_write_tokens
            self.n_retries = n_retries
            self.time = time
````

### F051

Grader warns on suspicious power-of-two/ten output lengths only after an incorrect score.

Repository: `eth-sri/matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`  
Path: `src/matharena/grader.py` lines 215-224  
Permalink: https://github.com/eth-sri/matharena/blob/a11194deff8c67a232974a383795e8a2776b4c6f/src/matharena/grader.py#L215-L224  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
        typed_gold_answer, _ = parse_answer(
            gold_answer, list_answer=gold_answer_is_list, typed_delimiters=use_typed_delimiters
        )
        is_correct = check_answers(model_answer, typed_gold_answer)

    if not is_correct and check_output_length(output_tokens):
        logger.warning(
            f"[{debug_info}] Model output length {output_tokens} is of the form 10**k * 2**n. This might indicate it hit the token limit."
        )
        warning = WarningType.MINOR  # model just didn't have time, any error could have been caused by this
````

### F052

LiteLLM response conversion retains content and reasoning but drops choice finish reason.

Repository: `huggingface/lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`  
Path: `src/lighteval/models/endpoints/litellm_model.py` lines 363-375  
Permalink: https://github.com/huggingface/lighteval/blob/64f4f5ae173626509fad6e477ca4ee56ebb26129/src/lighteval/models/endpoints/litellm_model.py#L363-L375  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
            for response, context in zip(responses, contexts):
                result: list[str] = [choice.message.content for choice in response.choices]
                reasonings: list[str | None] = [
                    getattr(choice.message, "reasoning_content", None) for choice in response.choices
                ]

                cur_response = ModelResponse(
                    # In empty responses, the model should return an empty string instead of None
                    text=result if result[0] else [""],
                    reasonings=reasonings,
                    input=context,
                )
                results.append(cur_response)
````

### F053

Ground-truth judgment forces zero only for recognized coarse eval_status failures.

Repository: `LiveBench/LiveBench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`  
Path: `livebench/gen_ground_truth_judgment.py` lines 108-116  
Permalink: https://github.com/LiveBench/LiveBench/blob/00eae856aa1c1a9e9d058a65a9a94d85884034c4/livebench/gen_ground_truth_judgment.py#L108-L116  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    eval_status = answer.get("eval_status")

    splits = task_or_subtask.split('_')

    eval_error = None
    try:
        if eval_status in FAILURE_EVAL_STATUSES:
            score = 0
            category = question.get("category", task)
````

### F054

Bare AdapterSpec defaults max_tokens to 100.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/adaptation/adapter_spec.py` lines 112-124  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/adaptation/adapter_spec.py#L112-L124  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    # Decoding parameters (inherited by `Request`)

    model_deployment: str = ""
    """Name of the language model deployment (<host_organization>/<model name>) to send requests to."""

    model: str = ""
    """Name of the language model (<creator_organization>/<model name>) to send requests to."""

    temperature: float = 1
    """Temperature parameter used in generation."""

    max_tokens: int = 100
    """Maximum number of tokens to generate."""
````

### F055

Generic generation helper instead defaults max_tokens to 5, so default is construction-path specific.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/adaptation/common_adapter_specs.py` lines 276-289  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/adaptation/common_adapter_specs.py#L276-L289  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def get_generation_adapter_spec(
    instructions: str = "",
    input_noun: Optional[str] = None,
    newline_after_input_noun: bool = False,
    output_noun: Optional[str] = None,
    newline_after_output_noun: bool = False,
    max_train_instances: int = 5,
    num_outputs: int = 1,
    max_tokens: int = 5,
    stop_sequences: Optional[List] = None,  # default value of `stop_sequences` is ["\n"]
    temperature: float = 0.0,
    multi_label: bool = False,
    sample_train: bool = True,
) -> AdapterSpec:
````

### F056

GSM8K sets 400; MATH sets 400 for CoT and 20 otherwise.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/run_specs/lite_run_specs.py` lines 137-224  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/run_specs/lite_run_specs.py#L137-L224  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
@run_spec_function("gsm")
def get_gsm_spec() -> RunSpec:
    scenario_spec = ScenarioSpec(class_name="helm.benchmark.scenarios.gsm_scenario.GSM8KScenario", args={})

    # Create AdapterSpec based on the GSM8K paper: https://arxiv.org/pdf/2110.14168.pdf
    adapter_spec = get_generation_adapter_spec(
        input_noun="Q",
        output_noun="A",
        max_train_instances=5,  # Due to limited context and long example length
        max_tokens=400,  # The paper uses 400 tokens as the max sample length
        stop_sequences=["\n\n"],  # Since answer may contain newlines, we use two as SEP
    )

    return RunSpec(
        name="gsm",
        scenario_spec=scenario_spec,
        adapter_spec=adapter_spec,
        metric_specs=get_basic_generation_metric_specs(["exact_match_indicator", "final_number_exact_match"])
        + get_generic_metric_specs()
        + get_generative_harms_metric_specs(),
        groups=["gsm"],
    )


@run_spec_function("math")
def get_math_spec(
    subject: str,
    level: str,
    use_official_examples: str = "False",
    use_chain_of_thought: str = "False",
) -> RunSpec:
    # Convert to bools and remove the str versions
    use_official_examples_bool: bool = use_official_examples.lower() == "true"
    use_chain_of_thought_bool: bool = use_chain_of_thought.lower() == "true"
    del use_official_examples
    del use_chain_of_thought

    if use_chain_of_thought_bool:
        assert not use_official_examples_bool, "Cannot use official examples when use_chain_of_thought is True."
    scenario_spec = ScenarioSpec(
        class_name="helm.benchmark.scenarios.math_scenario.MATHScenario",
        args={
            "subject": subject,
            "level": level,
            "use_official_examples": use_official_examples_bool,
            "use_chain_of_thought": use_chain_of_thought_bool,
        },
    )

    if use_chain_of_thought_bool:  # Include the solution in the output as per https://arxiv.org/abs/2201.11903
        output_prefix = "Answer: "  # Don't include LaTeX '$' delimiters
        output_suffix = "\n"
        instance_prefix = "###\n"  # Don't include LaTeX '$' delimiters
        max_tokens = 400  # Increase the number of tokens to generate
        stop_sequences = ["###"]  # Break at the next instance; extraneous output will be stripped out
        groups = ["math_chain_of_thought"]
    else:
        output_prefix = "Answer: $"
        output_suffix = "$\n"
        instance_prefix = "###\n"
        max_tokens = 20
        stop_sequences = ["$"]  # Break at the nearest LaTeX closing delimiter
        groups = ["math_regular"]

    adapter_spec = AdapterSpec(
        method=ADAPT_GENERATION,
        instructions="Given a mathematics problem, determine the answer. Simplify your answer as much as possible.\n",
        max_train_instances=8,
        num_outputs=1,
        temperature=0.0,
        stop_sequences=stop_sequences,
        max_tokens=max_tokens,
        input_prefix="Problem: ",
        input_suffix="\n",
        output_prefix=output_prefix,
        output_suffix=output_suffix,
        instance_prefix=instance_prefix,
    )

    return RunSpec(
        name=f"math:subject={subject},level={level},"
        f"use_official_examples={use_official_examples_bool},use_chain_of_thought={use_chain_of_thought_bool}",
        scenario_spec=scenario_spec,
        adapter_spec=adapter_spec,
        metric_specs=get_basic_metric_specs(
            ["math_equiv_chain_of_thought" if use_chain_of_thought_bool else "math_equiv"]
        )
        + get_generative_harms_metric_specs(),
````

### F057

GSM scorer extracts the final numeric regex match from both gold and prediction.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/metrics/evaluate_reference_metrics.py` lines 145-161  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/metrics/evaluate_reference_metrics.py#L145-L161  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def final_number_exact_match(gold: str, pred: str) -> float:
    """
    Returns 1 iff the final number in gold and pred match.
    Similar to exact_match_indicator.
    Example:
    - gold = "The answer is 15."
    - pred = "The answer is 15 eggs."
    - Returns 1
    """

    def get_final_number(x: str) -> str:
        matches = re.findall(r"-?[\d,]+(?:.\d+)?", x)
        if not matches:
            return ""
        return matches[-1].replace(",", "")

    return exact_match(get_final_number(gold), get_final_number(pred))
````

### F058

MATH get_answer selects the last complete box and native equivalence compares extracted answers.

Repository: `stanford-crfm/helm` at `63754d05db6f874e41a395880fb573890a13e791`  
Path: `src/helm/benchmark/scenarios/math_scenario.py` lines 253-293  
Permalink: https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/scenarios/math_scenario.py#L253-L293  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def get_answer(solution: Optional[str]) -> Optional[str]:
    if solution is None:
        return None
    last_boxed = last_boxed_only_string(solution)
    if last_boxed is None:
        return None
    answer = remove_boxed(last_boxed)
    if answer is None:
        return None
    return answer


def is_equiv(str1: Optional[str], str2: Optional[str]) -> float:
    """Returns (as a float) whether two strings containing math are equivalent up to differences of formatting in
    - units
    - fractions
    - square roots
    - superfluous LaTeX.

    Source: https://github.com/hendrycks/math
    """
    if str1 is None and str2 is None:
        print("WARNING: Both None")
        return 1.0
    if str1 is None or str2 is None:
        return 0.0

    try:
        ss1 = _strip_string(str1)
        ss2 = _strip_string(str2)
        return float(ss1 == ss2)
    except Exception:
        return float(str1 == str2)


def is_equiv_chain_of_thought(str1: str, str2: str) -> float:
    """Strips the solution first before calling `is_equiv`."""
    ans1 = get_answer(str1)
    ans2 = get_answer(str2)

    return is_equiv(ans1, ans2)
````

### F059

MGSM requires an answer prefix then returns the last numeric regex match.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `mgsm_eval.py` lines 83-100  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/mgsm_eval.py#L83-L100  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
def parse_answer(answer: str, answer_prefix: str) -> str:
    if answer_prefix not in answer:
        return ""

    answer_text = answer.split(answer_prefix)[-1].strip()

    # find all the numbers (including decimals) in the string
    numbers = re.findall(r"\d+\.?\d*", answer_text.replace(",", ""))

    # return the first number (removing trailing decimal point if present),
    # or an empty string if there were no numbers
    return numbers[-1].rstrip(".") if numbers else ""


def score_mgsm(target: str, prediction: str) -> bool:
    if "." in prediction:
        prediction = prediction.rstrip("0").rstrip(".")
````

### F060

MGSM task calls the real parser then local scorer.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `mgsm_eval.py` lines 154-181  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/mgsm_eval.py#L154-L181  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def __call__(self, sampler: SamplerBase) -> EvalResult:
        def fn(example: dict[str, str]):
            language = example["lang"]
            latin_language = "group_latin" if language in LATIN_LANGUAGES else "group_non_latin"
            correct_answer = example["targets"]
            instruction = LANG_TO_INSTRUCTIONS[language]
            prompt_messages = [
                sampler._pack_message(
                    content=instruction.format(input=example["inputs"]), role="user"
                )
            ]
            try:
                sampler_response = sampler(prompt_messages)
                response_text = sampler_response.response_text
                actual_queried_prompt_messages = sampler_response.actual_queried_message_list
            except Exception as e:
                response_text = ""

            answer_prefix = LANG_TO_ANSWER_PREFIX[language]
            extracted_answer = parse_answer(response_text, answer_prefix)

            score = score_mgsm(correct_answer, extracted_answer)
            html = common.jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=actual_queried_prompt_messages,
                next_message=dict(content=response_text, role="assistant"),
                score=score,
                correct_answer=correct_answer,
                extracted_answer=extracted_answer or None,
````

### F061

Responses sampler retains output text and usage but not incomplete or finish metadata.

Repository: `openai/simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`  
Path: `sampler/responses_sampler.py` lines 55-85  
Permalink: https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/sampler/responses_sampler.py#L55-L85  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    def __call__(self, message_list: MessageList) -> SamplerResponse:
        if self.system_message:
            message_list = [
                self._pack_message("developer", self.system_message)
            ] + message_list
        trial = 0
        while True:
            try:
                if self.reasoning_model:
                    reasoning = (
                        {"effort": self.reasoning_effort}
                        if self.reasoning_effort
                        else None
                    )
                    response = self.client.responses.create(
                        model=self.model,
                        input=message_list,
                        reasoning=reasoning,
                    )
                else:
                    response = self.client.responses.create(
                        model=self.model,
                        input=message_list,
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                    )
                return SamplerResponse(
                    response_text=response.output_text,
                    response_metadata={"usage": response.usage},
                    actual_queried_message_list=message_list,
                )
````

### F062

Generation resolves an unset cap from the model API config then provider default.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`  
Path: `src/inspect_ai/model/_model.py` lines 813-817  
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/model/_model.py#L813-L817  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
        # provide max_tokens from the model api if required
        if config.max_tokens is None:
            config.max_tokens = self.api.max_tokens_for_config(config)
            if config.max_tokens is None:
                config.max_tokens = self.api.max_tokens()
````

### F063

Numeric end matching scans whitespace tokens backward and takes the first parseable number.

Repository: `UKGovernmentBEIS/inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`  
Path: `src/inspect_ai/scorer/_common.py` lines 59-83  
Permalink: https://github.com/UKGovernmentBEIS/inspect_ai/blob/f10dc46f20df0738a9acbfb4c4be0bd3d60601ed/src/inspect_ai/scorer/_common.py#L59-L83  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    if numeric:
        t = strip_numeric_punctuation(t)
    if numeric and _is_number(t):
        # the target is a number: extract the relevant number(s) from the
        # value, normalize both, and compare for numeric equality. we do
        # NOT fall through to the text comparison below because e.g.
        # "25".endswith("5") is True but 25 != 5.
        v = strip_numeric_punctuation(v)
        t = normalize_number(t)
        words = re.split(r"\s+", v)
        if location == "begin":
            v = first_number_normalized(words)
        elif location == "end":
            words.reverse()
            v = first_number_normalized(words)
        elif location == "exact":
            v = normalize_number(v)
        else:
            # location == "any": match if any number in the value equals t
            for number in all_numbers_normalized(words):
                if number == t:
                    return number, True
            return answer, False
        answer = v
        return answer, v == t
````

### F064

GSM8K registers Inspect numeric match on generated output.

Repository: `UKGovernmentBEIS/inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`  
Path: `src/inspect_evals/gsm8k/gsm8k.py` lines 78-91  
Permalink: https://github.com/UKGovernmentBEIS/inspect_evals/blob/b31daf3f6f74ce48cb905d185a4c2afc524205b2/src/inspect_evals/gsm8k/gsm8k.py#L78-L91  
Encoding/line endings: `utf-8` / `LF`; generated file: `false`.

````text
    # define task
    return Task(
        dataset=hf_dataset(
            path="openai/gsm8k",
            data_dir="main",
            split="test",
            sample_fields=record_to_sample,
            revision=GSM8K_DATASET_REVISION,
        ),
        solver=solver,
        scorer=match(numeric=True),
        version=EVAL_VERSION.comparability_version,
        metadata=EVAL_VERSION.to_metadata(),
    )
````

## Verification log

Phase 1 receipt gate: `.venv/bin/python ecosystem_audit/validate_receipts.py` (exit 0).

Full offline, strict, executable-reproduction, root-suite, and PR gates are recorded here only after they run successfully.
