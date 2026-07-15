# Inkling Playground pilot findings

## Run status

- Date: 2026-07-15
- Playground: `https://tinker.thinkingmachines.ai/playground`
- Model: Inkling
- Completed: 45/45 valid runs
- Overall accuracy: 45/45 (100%)
- Visible response length: 45 short, 0 medium, 0 long

## Protocol

The original pilot protocol was followed:

- 15 fixed prompts: five math and ten structured extraction
- Three exact reasoning-effort values per prompt: 0.2, 0.6, and 0.99
- A fresh Playground tab for every run, preventing context bleed
- Web search disabled for every run
- Default system prompt and 32,768 max-token setting retained
- Only the visible final answer was graded; the collapsed Thought trace was ignored
- Full visible responses and rough UI-observed latency were recorded in `pilot/playground_results.jsonl`

## Pre-run sample audit

Two of the five math gold labels were wrong and were corrected before testing:

| Item | Original gold | Correct gold | Check |
| --- | ---: | ---: | --- |
| `math_0000` | 735 | 280 | Valid values are 14, 35, 56, 77, and 98; their sum is 280. |
| `math_0002` | 76 | 1 | Euler's theorem gives `2^100 ≡ 1 (mod 125)`. |

The other math labels and all ten extraction labels were independently checked against their prompts.

## Results

| Domain | Effort | Accuracy | Mean rough UI latency |
| --- | ---: | ---: | ---: |
| Math | 0.2 | 5/5 (100%) | 3.7 s (n=4 timed) |
| Math | 0.6 | 5/5 (100%) | 4.8 s |
| Math | 0.99 | 5/5 (100%) | 7.9 s |
| Extraction | 0.2 | 10/10 (100%) | 1.6 s |
| Extraction | 0.6 | 10/10 (100%) | 1.8 s |
| Extraction | 0.99 | 10/10 (100%) | 2.8 s |

The first `math_0000` effort-0.2 run was completed and scored but its timing was not captured, so that cell averages the other four math runs.

## Findings

1. **No accuracy benefit appeared in this pilot.** Math was 15/15 and extraction was 30/30 across all effort values.
2. **The pilot has a ceiling effect.** These five math questions are too easy for Inkling, and the extraction prompts are deliberately mechanical. The results do not identify a math effort knee.
3. **Higher effort increased latency without improving answers.** Mean observed math latency rose from 3.7 s at effort 0.2 to 7.9 s at 0.99, roughly 2.1x. Extraction rose from 1.6 s to 2.8 s, roughly 1.8x.
4. **Visible answer length stayed short.** Higher effort generally moved work into the collapsed Thought section rather than producing longer final answers. Visible response length is therefore not a proxy for reasoning-token use.
5. **The Playground does not expose usage counts in the raw assistant message.** Its raw view contains only the assistant role, content, and request ID. This pilot supports rough latency observations, not token-efficiency or cost claims.
6. **The current Playground cannot test the multimodal hypothesis.** The Attach images and Record audio controls are disabled and marked “coming soon.” Audio and chart sweeps require API/cookbook access or a future Playground update.

## Interpretation

The honest pilot conclusion is narrower than the original hypothesis: **easy math and structured extraction are already saturated at effort 0.2, while maximum effort adds latency and no observed accuracy.** This is a useful negative result, but it is not evidence that effort never helps math. The next text sweep should use genuinely difficult competition problems, and publishable efficiency curves must use provider-reported token counts from the API.

## Artifacts

- `pilot/tally.csv`: completed 45-row score sheet
- `pilot/playground_results.jsonl`: full visible responses, final answers, grades, length buckets, and rough UI latency
- `pilot/pilot_prompts.md`: corrected prompts and gold labels
