# Thinking Cut Short

Working subtitle: Separating token starvation from genuine overthinking in
reasoning models.

## Status

This is a pilot-informed exploratory protocol, not a preregistration. The
original Tinker and OpenRouter sweeps revealed output-limit failures before
this protocol was written. Those historical rows remain unchanged and are the
sampling frame for the paired rescue experiment.

## Core question

When accuracy appears to fall at higher reasoning effort, is the model making
a worse decision after completing its reasoning, or is the response being cut
off before it can state a final answer?

## Primary experiment

For each response that ended at the old output limit, repeat the same item,
model, provider route, prompt, and effort with a larger output limit. The
output limit is the only configured experimental change. Together does not
advertise support for a fixed `seed`, so these are matched stochastic reruns,
not deterministic counterfactual pairs. Tinker and OpenRouter are analyzed
separately; a row from one provider never substitutes for a paired row from
the other.

The primary outcome is cap rescue rate: the number of previously truncated
item-effort pairs that become correct at the larger cap, divided by the number
successfully rerun. We also report how many reruns still end with
`finish_reason == "length"`, fail before producing a result, or complete with
an incorrect answer. Every denominator is shown.

A stronger confirmatory design will randomize old-cap and larger-cap requests
across repeated completions for the same item. This estimates a cap effect in
distribution despite the lack of fixed-seed support. The single-rerun rescue
series remains exploratory and must not be described as a deterministic causal
estimate.

## Failure taxonomy

- Token-starved: the original response ended at its output limit and had no
  gradeable final answer.
- Rescued: the paired larger-cap response completes and grades correct.
- Completed wrong: the larger-cap response ends normally but grades wrong.
- Still censored: the larger-cap response again ends because of length.
- Transport or provider failure: no valid paired observation was returned.

The last two categories are missing or censored evidence, not proof that more
reasoning hurts.

## First checkpoint

The first paid check is Tinker `math_0003` at effort `0.99` with a 49,152-token
cap. Its historical Tinker response stopped at 4,096 tokens and graded wrong.
This one-row check tests billing access, streaming survival, usage reporting,
and whether the endpoint now honors a cap above 4,096. It is not an accuracy
estimate.

If Tinker rejects billing/authentication or still enforces the old cap, Tinker
work stops. The fallback is a provider-pinned OpenRouter rerun of its nine
max-effort math rows that ended at 20,000 tokens, using a fresh cache and
results directory.

## 2026-07-21 checkpoint

Tinker rejected the isolated request with HTTP 402 before generation, so that
path is frozen. The first OpenRouter/Together fallback row was a successful
matched rescue: `math_0003` changed from a 20,000-token length stop with no
answer to a normal stop after 38,603 completion tokens with the correct answer
`240`. This cost $0.156443.

The next row, `math_0008`, ended its stream without a usage event or finish
reason. Its recorded token counts are `-1`, so it is an unaccounted stream and
not a valid observation. The following request was interrupted, and all paid
work is paused. Current exploratory accounting is 1 rescue among 1 valid
matched rerun, 1 unaccounted stream, and 7 missing rows.

## Budget gates

The prior Tinker spend is $2.658340 and the retained Tinker ceiling is $8.00.
One 49,152-token Tinker call has a worst-case completion charge of about $0.23
plus prompt cost. No automatic request retry is enabled for this pilot.

The completed OpenRouter replication conservatively cost $5.732601, and the
historical Tinker work cost $2.658340. The latest user instruction is treated
conservatively as a $10.00 ceiling across both providers. After the successful
$0.156443 rescue pilot, combined study spend is $8.547384 and $1.452616
remains. Spending is recomputed after each batch.

## Follow-up model panel

After the Inkling rescue establishes that the design works, the intended
cross-model panel uses current models with native reasoning-effort controls and
observable termination metadata. Grok 4.5 is the leading second model; a
current GPT-5-class model is a candidate third model only after a smoke test
confirms trace, usage, and finish-reason visibility. The same-model paired
cap-rescue result remains the central claim; cross-model breadth is a
replication question, not a replacement for that control.

Runtime OpenRouter endpoint metadata checked on 2026-07-21 makes the panel more
controlled than Inkling alone:

- `x-ai/grok-4.5` advertises `reasoning`, `reasoning_effort`, `max_tokens`, and
  `seed`, with a standard xAI route listed at $2/M input and $6/M output.
- `openai/gpt-5.6-luna` advertises the same four control parameters, with a
  standard OpenAI route listed at $1/M input and $6/M output.
- Together's Inkling endpoint advertises effort and output-cap controls but not
  `seed`.

Grok 4.5 initially appeared to be the preferred confirmatory second model
because its endpoint advertises `seed`. The paid pilot invalidated that plan:
its native billable reasoning tokens exceeded the requested `max_tokens`, so
the intended cap manipulation did not exist in billable-token space. The prior
$1.26 "worst-case" dry-run bound was therefore invalid and must not be reused.
GPT-5.6 Luna remains a candidate only after a smoke test establishes that its
output limit bounds reasoning-inclusive billed usage.

The request order was fixed with Python's `random.Random(7)` before seeing any
Grok output: `math_0009@20000`, `math_0003@20000`, `math_0009@49152`,
`math_0008@49152`, `math_0003@49152`, and `math_0008@20000`. Every request uses
seed 7001 and max effort. Each job runs as a separate invocation so usage and
combined spend can be checked before the next job starts.

Only the first two scheduled Grok jobs completed. `math_0009@20000` used 5,429
native completion tokens, including 4,727 native reasoning tokens, and cost
$0.032990. `math_0003@20000` used 54,969 native completion tokens, including
53,883 native reasoning tokens, and cost $0.330182 despite the 20,000-token
request. Both ended normally and answered correctly. The remaining four jobs
were not run. Because neither item has both cap conditions, these observations
do not estimate a cap effect.

xAI documents Grok 4.5 effort values `low`, `medium`, and `high`; it does not
document `max`. The two rows retain their requested `max` label, but their
effective native effort is unknown and must not be relabeled after the fact.
