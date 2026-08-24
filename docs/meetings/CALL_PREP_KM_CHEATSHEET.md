# Call prep: the math in one page

## The five ideas

1. **Right-censoring.** A capped response's length is not "cap tokens" — it is "> cap, unknown." Like a race timer that shuts off at 60 min: finishers get times, everyone else gets "more than 60."

2. **Both naive fixes are biased.** Drop capped rows → you dropped exactly the long ones (toy: says 100% finish by 256). Treat cap as the true length → inflates "done by t" (it's actually the worst-case upper bound on the truth).

3. **Kaplan-Meier = multiply survival fractions.** At each length where some response finished, take (still-at-risk − finishers)/(still-at-risk), using only responses still observable there. Capped rows count in denominators until they drop out — never as finishers.

4. **No mean, no median when the curve doesn't reach zero.** Longest observation censored → tail unknown → mean (area under curve to ∞) unidentified; curve stalls at 0.547 > 0.5 → median unidentified. Fix: restricted mean — area under the curve up to a prespecified horizon τ.

5. **KM never touches correctness.** A capped run has a true latent *length* (censored). It has no true latent *answer* — a bigger-cap rerun is a new draw, not a continuation. Length → survival analysis. Correctness under a bigger cap → new experiment (the 2×2). This asymmetry is the whole paper.

## The toy, cold

8 responses. Natural finishes at 128, 192, 256. Capped at 128, 192, 256, 256, 384.

| Checkpoint | At risk | Finish | Survive |
|---|---|---|---|
| 128 | 8 | 1 | 7/8 |
| 192 | 6 | 1 | 5/6 |
| 256 | 4 | 1 | 3/4 |

S(256) = (7/8)(5/6)(3/4) = 0.547 → **F(256) = 0.453**.

Tie rule: rows capped *at* 256 stay in the risk set at 256 — producing 256 tokens without stopping means they survived through 256. This choice alone moves the answer by 0.20, hence it must be stated.

## The independence assumption (his Helpfulness experiment)

KM is valid only if being capped carries no extra information about the would-be length. His cap is 512 − prompt length → long prompts capped early → if prompt length relates to response length, the assumption breaks. Fix: estimate within prompt-length strata, then average (race analogy: earlier cutoffs for older runners → analyze within age groups). That's all "stratification" means.

## Your experiment, one breath

Same 30 AIME items, 2 effort settings × 2 output caps, pinned routes, one generation per cell. Effort slope D_c = accuracy(high) − accuracy(low) at cap c. Interaction I = D_large − D_small. If the slope shrinks when there's room to finish — and the shrinkage tracks capped-with-no-answer responses — that's evidence the small-cap "overthinking" curve was partly token starvation. A slope that survives at the large cap is reported as completed negative scaling, never as proven overthinking.

## Likely questions → one-line answers

- "Walk me through 0.453." → the table above, out loud.
- "Why is the mean not identified?" → longest observation censored; tail unknown; use restricted mean.
- "Why not apply KM to accuracy?" → an unwritten answer is nonexistent, not hidden; reruns are new draws, not continuations.
- "What does one generation per cell buy you?" → a narrow fixed-benchmark route audit; no estimate of run-to-run variance; that's why repeats are an open question for us.
- "Why medium vs max and not adjacent levels?" → the exploratory contrast we observed the effect at; worth revisiting together.

## When out of depth

"I verified that numerically, but I can't derive it — can you walk me through it?"
