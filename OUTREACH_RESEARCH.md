# Outreach research for *Thinking Cut Short*

**Research completed:** 2026-07-22  
**Researcher identity for future correspondence:** Connor Klann, Independent Researcher, [ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)  
**Status:** Research and drafts only. No message has been sent, no paid confirmatory call has been made, and new-study spend remains **$0.00**.

## Executive assessment

This is a plausible paper, but only with a narrow claim. Token starvation, output
truncation, negative test-time-compute scaling, and harmful overthinking all have
substantial prior art. The defensible contribution is the experimental cross that
the current literature usually does not perform:

> A controlled, route-specific audit that crosses a model's native reasoning-effort
> setting with its external output allowance on the same items, then separates
> correct completions, completed wrong answers, and cap-hit/no-answer outcomes.

The corresponding cautious novelty sentence is:

> To our knowledge, this is the first controlled factorial audit of how a native
> reasoning-effort setting interacts with an external output allowance, separating
> apparent performance loss caused by interrupted generation from errors produced
> by completed responses.

That sentence must remain qualified by “to our knowledge,” must be rechecked before
submission, and must name the exact model, provider route, API, and observation date
when describing results. The paper must **not** claim to be the first study of token
starvation, truncation, output budgets, reasoning efficiency, or overthinking.

### The most important pre-experiment finding

The existing preregistration plans one stochastic generation per item and cell. That
can describe one randomized operational evaluation on a fixed 30-item benchmark,
but it cannot estimate within-item generation variability or support a broad claim
about stable model behavior. NIST's current guidance distinguishes fixed-benchmark
from generalized accuracy and emphasizes that LLM evaluation is stochastic; more
than one trial per item enables the within-item component to be measured rather than
assumed away ([NIST AI 800-3](https://doi.org/10.6028/NIST.AI.800-3)).

This is not an automatic fatal flaw. It creates a choice that should be made before
the first paid call:

1. **Keep the present $30.06 plan.** Frame the result narrowly as a single-sample,
   fixed-benchmark, route-specific factorial audit. Do not generalize small
   differences as stable model behavior.
2. **Strengthen the stochastic claim.** Add at least a second generation per cell.
   Doubling both preregistered model panels raises their worst-case exposure from
   about $26.75 to about $53.50. Keeping the existing $3.06 margin would require an
   account balance of roughly **$56.56**, about **$26.50 more** than the current
   $30.06. This is a planning bound, not a request to spend now.
3. **Reallocate rather than top up.** Use the present budget for fewer items or one
   model with repeats. This improves within-item reliability but weakens benchmark
   coverage or cross-model replication. It requires a committed preregistration
   amendment before any paid response.

The best next action is to ask two or three methods specialists the precise question
above, then amend or reaffirm the design before spending. The experiment remains
paused until Connor approves that decision.

## What the literature already establishes

### Output limits can erase answers

- [Sun et al., *An Empirical Study of LLM Reasoning Ability Under Strict Output
  Length Constraint*](https://aclanthology.org/2025.emnlp-main.389/) evaluates
  multiple output budgets and shows that abrupt termination can underestimate
  performance because a response is stopped before it concludes. Their “Time's Up”
  intervention changes the generation by reserving room for an answer; it is not the
  native-effort-by-cap experiment proposed here.
- [Kaiser et al., *Beyond Accuracy: Decomposing the Reasoning Efficiency of
  LLMs*](https://arxiv.org/abs/2602.09805) separates clean completion, correctness
  conditional on completion, and token consumption. This means the completion
  decomposition itself is prior art. Their study does not cross native effort with
  output allowance or estimate the interaction.
- [Gao et al., *How Far Are We from Optimal Reasoning
  Efficiency?*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html)
  recognizes that naive truncation produces incomplete responses and uses an answer
  fallback. It studies efficiency frontiers, not hosted-API censoring under crossed
  native controls.
- [Saurabh Srivastava et al., *Reasoning Under
  Constraint*](https://openreview.net/forum?id=SNQbmwO2rb) explicitly reports
  reasoning loops that exhaust a token budget without an answer. It studies batch
  prompting as a mitigation, not a cap-by-effort identification design.
- The debate around Apple's [*The Illusion of
  Thinking*](https://machinelearning.apple.com/research/illusion-of-thinking) also
  makes the broad artifact claim unavailable as a novelty claim. A [public
  comment](https://arxiv.org/abs/2506.09250) argued that some reported failures
  exceeded output limits, while [subsequent work](https://arxiv.org/abs/2507.01231)
  found that the failures were not explained solely by those limits. The appropriate
  question is therefore how much of a measured decline is attributable to each
  mechanism, not whether truncation can matter at all.

### Genuine completed overthinking also exists

- [Zhou et al., *When More Thinking
  Hurts*](https://aclanthology.org/2026.findings-acl.1199/) tracks correct-to-wrong
  flips over forced token budgets. Its forced end-of-thinking mechanism still gives
  the model an answer opportunity, unlike a hard API cutoff that may produce no
  answer.
- [Song et al., *ThinkBrake*](https://aclanthology.org/2026.findings-acl.1095/)
  defines a strong form of overthinking: a trajectory reaches a correct intermediate
  result, continues, and overwrites it with a wrong final answer. It uses deliberate
  stop interventions at sentence boundaries.
- [Caldarella et al., *Thinking Past the
  Answer*](https://arxiv.org/abs/2606.02835) distinguishes harmless verbosity from
  harmful overthinking with prefix-level trajectory evaluation.
- [Gema et al., *Inverse Scaling in Test-Time
  Compute*](https://arxiv.org/abs/2507.14417) constructs tasks on which longer
  reasoning genuinely lowers accuracy through distraction, overfitting, and other
  completed-generation failure modes.
- [Chen et al., *Do NOT Think That Much for
  2+3=?*](https://arxiv.org/abs/2412.21187) is early comprehensive prior work on
  unnecessary reasoning and efficiency loss.

Therefore, a high-effort response that ends normally but is wrong is only a
**candidate completed negative-scaling case**. Calling it genuine overthinking
requires stronger evidence, such as an earlier correct conclusion later abandoned,
a forced-continuation or forced-stop intervention, or repeated correct-to-wrong
transitions. A completed wrong answer by itself is not enough.

### Native effort is not the same intervention as a token budget

- [Ballon, Algaba, and Ginis, *The relationship between reasoning and performance
  in large language models*](https://www.nature.com/articles/s41598-026-50923-2)
  compares native medium and high effort for o3-mini. The conditions used different
  maximum ceilings, so effort and allowance were not fully crossed. This is the
  closest published motivation for the proposed factorial design.
- [Hu and Wang, *Effort as Ceiling, Not
  Dial*](https://arxiv.org/abs/2605.16938) finds that native effort can act like an
  upper allowance rather than proportional compute. This cautions against treating
  effort labels as a universal quantitative scale.
- [Snell et al., *Scaling LLM Test-Time Compute
  Optimally*](https://arxiv.org/abs/2408.03314), [Muennighoff et al.,
  *s1*](https://arxiv.org/abs/2501.19393), and [Aggarwal and Welleck,
  *L1*](https://arxiv.org/abs/2503.04697) establish the importance of test-time
  allocation and length control. Their learned or forced controls are not identical
  to a provider's native effort setting.
- [Wang et al., *Reasoning in Token
  Economies*](https://aclanthology.org/2024.emnlp-main.1112/) shows why performance
  comparisons must account for unequal compute.

### Gateways and providers are part of the treatment

- [Lin et al., *Behavioral Consistency and Transparency Analysis on Large Language
  Model API Gateways*](https://arxiv.org/abs/2604.21083) audits gateway-level model
  substitution, silent truncation, billing inconsistencies, and latency. Silent
  gateway truncation is therefore not a novel topic by itself.
- [Epoch AI, *Why benchmarking is
  hard*](https://epoch.ai/gradient-updates/why-benchmarking-is-hard) reports
  provider-dependent benchmark variance, responses cut below requested limits, and
  a route that failed to transmit a reasoning-effort setting.
- [OpenRouter's reasoning
  documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
  explains that mappings differ by model and provider and that reasoning consumes
  output tokens. [Inspect's reasoning
  documentation](https://inspect.aisi.org.uk/reasoning.html) likewise records
  provider-specific mappings.

The estimand must consequently be phrased as the effect of requested effort and
allowance for model **M**, through provider route **P**, under the API behavior
observed on date **D**. An OpenRouter-to-Together result is not automatically a claim
about the underlying checkpoint or its developer's direct endpoint.

### “Censoring” needs precise use

[Chirag Nagpal's generation-length note](https://chiragnagpal.github.io/papers/llm_length_kaplan_meier_25.pdf)
formally treats truncated generation length as right-censored. That supports the
language for **length**. Correctness is different:

- At the tested cap, a no-answer response is an observed operational failure and may
  properly count as wrong for endpoint utility.
- Its counterfactual correctness under a larger allowance is unobserved.
- Completed-only accuracy is selection-biased because difficult or verbose cases
  are more likely to be excluded.
- Bounds such as `[observed correct / n, (observed correct + cap hits) / n]` show
  what cap-hit outcomes leave unidentified.
- Kaplan-Meier is appropriate for a censored length distribution. It should not be
  applied mechanically to correctness without a justified statistical model.

## What remains unresolved

1. How much of a negative **native-effort** accuracy slope is due to cap-hit/no-answer
   outcomes rather than completed wrong responses.
2. Whether extra output room benefits high effort more than medium effort on the
   same items and route.
3. Whether any interaction replicates across model families and direct versus
   gateway endpoints.
4. Whether a provider maps a larger `max_tokens` value into a larger internal
   reasoning allocation. If so, cap and effort are not implementation-independent
   even though they remain two requested factors.
5. Whether `finish_reason`, usage, and billing receipts expose every effective
   cutoff honestly.
6. Whether completed high-effort errors are genuine answer abandonment, failed
   search, or ordinary sampling variation.
7. How stable the interaction is across repeat generations.

This unresolved set is the real opening for *Thinking Cut Short*.

## Candidate-ranking method

Each score is a 1–5 judgment, not a measured fact:

- **R:** technical relevance;
- **I:** likely intellectual interest;
- **D:** potential design/statistics contribution;
- **C:** collaboration, review, or replication fit;
- **P:** inferred probability of a thoughtful cold response; and
- **V:** potential credibility, visibility, adoption, compute, or funding value.

Ranking is portfolio-based rather than a mechanical sum. It prioritizes people who
answer distinct immediate questions. Current roles and contacts are facts only where
the linked source states them. “Likely to respond” and recommended strategy are
inferences.

## Ranked scientific contacts

| Rank | Person and group | Verified current role or affiliation | Closest work and exact connection | Verified professional contact | Best initial request | R/I/D/C/P/V |
|---:|---|---|---|---|---|---|
| 1 | **Daniel Kaiser** — evaluation/censoring framework | PhD Fellow, UiT and Integreat | [*Beyond Accuracy*](https://arxiv.org/abs/2602.09805) gives the closest completion/correctness/token decomposition. Our novel element would be crossing effort and allowance. | `daniel.kaiser@uit.no`, [official UiT profile](https://en.uit.no/ansatte/person?p_document_id=856406) | Ten-minute review of the three-outcome decomposition and interaction estimand | 5/5/5/5/4/4 |
| 2 | **Marthe Ballon** — native effort | PhD student, Data Analytics Lab, Vrije Universiteit Brussel | [o3-mini native-effort study](https://www.nature.com/articles/s41598-026-50923-2) is the closest published comparison; its medium and high conditions used different ceilings rather than a crossed design. | `marthe.ballon@vub.be`, [official lab page](https://data.research.vub.be/marthe-ballon) | Ask whether the crossed design resolves a limitation she considers material | 5/5/5/5/4/4 |
| 3 | **Chirag Nagpal** — censoring/statistics | AI Research Scientist, Meta; self-described member of GenAI Safety Alignment and Post-training | [Generation-length censoring note](https://chiragnagpal.github.io/papers/llm_length_kaplan_meier_25.pdf) plus survival-analysis expertise directly addresses the paper's terminology and bounds. | `chiragn@alumni.cmu.edu`, [current personal page](https://chiragnagpal.github.io/) | Check the distinction between censored length, observed capped utility, and unobserved high-cap correctness | 5/5/5/4/3/5 |
| 4 | **Simone Caldarella** — genuine overthinking/trace analysis | AI and computer-vision PhD student, University of Trento | [*Thinking Past the Answer*](https://arxiv.org/abs/2606.02835) distinguishes harmless verbosity from harmful correct-to-wrong drift. | `simone.caldarella@unitn.it`, [current CV page](https://simonecaldarella.github.io/cv/) | Review the proposed trace taxonomy and what would justify “genuine overthinking” | 5/5/5/5/4/4 |
| 5 | **Ryan Steed** — statistical evaluation | Research Scientist, NIST Center for AI Standards and Innovation | Coauthor of [NIST AI 800-3](https://doi.org/10.6028/NIST.AI.800-3), which distinguishes fixed-benchmark and generalized accuracy and models repeated trials. | `ryan.steed@nist.gov`, [official NIST profile](https://www.nist.gov/people/ryan-steed) | One bounded question about repeats, fixed-item inference, and item-clustered uncertainty | 4/4/5/3/3/5 |
| 6 | **Aryo Pradipta Gema** — genuine inverse scaling | Research postgraduate and PhD student, University of Edinburgh | [*Inverse Scaling in Test-Time Compute*](https://arxiv.org/abs/2507.14417) is the strongest challenge to any claim that all negative scaling is truncation. | `s2412861@sms.ed.ac.uk`, [official Edinburgh profile](https://people.inf.ed.ac.uk/Aryo_Gema.html) | Adversarial review of whether the design truly distinguishes censoring from inverse scaling | 5/5/5/5/4/4 |
| 7 | **Gaurav Srivastava** — token-constrained math evaluation | Virginia Tech alumnus; official page says he graduated in spring 2026, but a current employer was not confirmed | [LLMThinkBench](https://aclanthology.org/2026.findings-acl.1285/) evaluates 53 models and reports large collapse under constrained tokens, with robust parsing as a stated concern. | `gks@vt.edu`, [official Virginia Tech profile](https://sanghani.cs.vt.edu/people/students/gaurav-srivastava.html) | Parser and truncation-reporting audit; compare harness assumptions | 5/5/5/5/5/3 |
| 8 | **Shu Zhou** — test-time overthinking | Nanjing University affiliation in the July 2026 paper; exact role not confirmed | [*When More Thinking Hurts*](https://aclanthology.org/2026.findings-acl.1199/) tracks marginal utility and correct-to-wrong flips on AIME and other tasks. | `shuzhou@smail.nju.edu.cn`, printed in the [paper PDF](https://aclanthology.org/2026.findings-acl.1199.pdf) | Ask how cap-hit/no-answer rows were handled and whether the factorial decomposition complements their forced-stop design | 5/5/4/5/4/4 |
| 9 | **Sangjun Song** — stop interventions | Graduate School of Data Science, Seoul National University, per July 2026 paper; exact role not stated | [*ThinkBrake*](https://aclanthology.org/2026.findings-acl.1095/) uses forced stops to identify answer abandonment. | `ssangjun706@snu.ac.kr`, printed in the [paper PDF](https://aclanthology.org/2026.findings-acl.1095.pdf) | Review five to ten rescued/failed trace pairs against their operational definition | 5/5/4/5/4/4 |
| 10 | **Pranjal Aggarwal** — length control/benchmarking | PhD student, Carnegie Mellon LTI | [*L1*](https://arxiv.org/abs/2503.04697) and [OptimalThinkingBench](https://arxiv.org/abs/2508.13141) study controlled length and joint over/underthinking metrics. | `pranjala@andrew.cmu.edu`, [official CMU profile](https://www.lti.cs.cmu.edu/people/students/aggarwal-pranjal.html); the paper also lists `pranjal2041@gmail.com` | Review the estimand and whether a censoring-aware efficiency summary is defensible | 5/5/5/5/4/4 |
| 11 | **Yuanchun Li** — strict output constraints | Assistant Professor, Institute for AI Industry Research, Tsinghua University | Senior author of [the strict output-length study](https://aclanthology.org/2025.emnlp-main.389/) that contrasts abrupt cutoff with reserved answer space. | `liyuanchun@air.tsinghua.edu.cn`, [current research page](https://yuanchun-li.github.io/) | Ask whether hard cutoff should be a separate outcome rather than an ordinary wrong answer | 5/5/5/4/3/4 |
| 12 | **Saurabh Srivastava** — token exhaustion in API models | Final-term PhD student, George Mason University | [*Reasoning Under Constraint*](https://openreview.net/forum?id=SNQbmwO2rb) directly reports reasoning loops exhausting budgets without an answer. | `ssrivas6@gmu.edu`, [current personal page](https://saurabhsriv.com/) | Compare their timeout/no-answer handling with the proposed cap-hit taxonomy | 5/5/4/5/5/3 |
| 13 | **Hailey Schoelkopf** — reproducible evaluation infrastructure | Evaluation researcher and LM Evaluation Harness maintainer; her current personal page says EleutherAI, but a conflicting non-authoritative directory was not used | [*Lessons from the Trenches*](https://arxiv.org/abs/2405.14782) and LM Evaluation Harness focus on reproducible sample-level evaluation. | `hailey.ruth.schoelkopf@gmail.com`, [self-hosted CV](https://haileyschoelkopf.github.io/assets/pdf/Hailey-Schoelkopf-Resume-Updated-9-2-24.pdf); her [site](https://haileyschoelkopf.github.io/) says Discord is preferred | Audit retries, cache/deduplication, censoring fields, and provenance | 4/4/5/4/4/5 |
| 14 | **Guanjie Lin** — gateway auditing | UMass Boston affiliation in the 2026 paper; exact current title not independently confirmed | Lead author of [GateScope](https://arxiv.org/abs/2604.21083), the closest provider/gateway truncation and billing audit. | `guanjie.lin001@umb.edu`, printed in the [paper PDF](https://arxiv.org/pdf/2604.21083) | Ask for route-attribution and receipt-schema review or independent replication | 5/5/5/5/4/4 |
| 15 | **Xinliang “Frederick” Zhang** — structural trace analysis | Research Engineer, Google DeepMind Gemini team; recent Michigan PhD | [TRACE](https://aclanthology.org/2026.acl-long.773/) defines overthinking structurally rather than by length alone. | `xlfzhang@google.com` or `xlfzhang@umich.edu`, [current research page](https://web.eecs.umich.edu/~xlfzhang/) | Review whether trace cases resemble over-exploration, late landing, or simple incompletion | 5/5/4/4/4/5 |
| 16 | **Michael Saxon** — evaluation validity | Research Scientist, Google DeepMind, Internationalization team | Co-first author of [ThoughtTerminator](https://arxiv.org/abs/2504.13367) and works on benchmark metrology. | `michael@saxon.me`, [public CV](https://saxon.me/doc/cv_saxon.pdf); role on [current site](https://saxon.me/) | Critique whether finish reasons and receipts are adequate measurement controls | 5/4/5/4/4/4 |
| 17 | **Niklas Muennighoff** — budget forcing | Building Composer at Cursor and Stanford CS PhD student | [*s1*](https://arxiv.org/abs/2501.19393) intentionally forces reasoning to end or continue, clarifying why hard truncation is a different intervention. | A focused issue on the [s1 repository](https://github.com/simplescaling/s1) is his stated preference; [current page](https://muennighoff.com/) also lists `n.muennighoff@gmail.com` | Ask one precise implementation question about forced conclusion versus hard cutoff | 5/4/5/4/3/5 |
| 18 | **Charlie Snell** — test-time compute allocation | 2026 UC Berkeley PhD graduate; next employer is not confirmed on the cited source | First author of [the foundational adaptive test-time-compute study](https://arxiv.org/abs/2408.03314). | `csnell22@berkeley.edu`, [official 2026 BAIR graduate showcase](https://bair.berkeley.edu/blog/2026/07/01/grads-2026/) | Ask whether “compute budget” should separate requested cap, generated tokens, and complete-answer availability | 4/4/5/4/3/5 |

### Strong additional contacts, not in the first 18

- **Jinyan Su**, Cornell CS PhD student: [*Between Underthinking and
  Overthinking*](https://arxiv.org/abs/2505.00127); `js3673@cornell.edu` on the
  [official Cornell profile](https://www.cs.cornell.edu/people/jinyan-su). Strong
  accessible second-wave reviewer for length/correctness confounding.
- **Sophia Xiao Pu**, UC Santa Barbara CS PhD student: [ThoughtTerminator](https://arxiv.org/abs/2504.13367).
  Use her [public research page](https://sophiapx.github.io/). The email rendered in
  the paper is ambiguous, so it is deliberately not normalized or guessed.
- **Yueqing Hu**, Chinese Academy of Sciences affiliation in the May 2026 paper:
  [*Effort as Ceiling, Not Dial*](https://arxiv.org/abs/2605.16938);
  `scnu.psy.hyq@gmail.com` printed in the paper. Good second-wave native-effort contact.
- **Nathanaël Carraz Rakotonirina**, Universitat Pompeu Fabra PhD student:
  [*Correct, Concise and Complete*](https://aclanthology.org/2026.findings-acl.622/);
  `nathanael.rakotonirina@upf.edu` printed in the paper. Strong for completeness
  terminology.

## Provider, infrastructure, replication, and funding contacts

These contacts serve a different purpose from scientific reviewers. Providers should
be asked to verify route facts, not to approve the paper's conclusions.

| Contact | Why it matters | Verified channel | Timing and request |
|---|---|---|---|
| **OpenRouter technical support** | OpenRouter maps reasoning controls, selects a provider, reports normalized/native usage, and computes charges. Accurate gateway attribution is essential. | `support@openrouter.ai`, support ticket, or documented Discord `#help`, [official support page](https://openrouter.ai/support) | Before smoke: ask how the pinned route handles effort, cap, native usage, and fallbacks. After data: provide generation IDs and request factual correction of the route description. |
| **Together AI inference team / Yineng Zhang** | Together is the proposed pinned host. Its team page lists Yineng Zhang in inference, but no personal address was verified. | [Official support portal](https://docs.together.ai/docs/support); role on [Together research page](https://www.together.ai/research) | Before main block: ask for served model revision, precision/quantization, total-cap semantics, and reasoning/answer accounting. Do not guess a personal email. |
| **Thinking Machines Tinker / Inkling team** | The model developer can clarify effort semantics and the historical direct-Tinker 4,096-cap and HTTP 402 record. | `tinker@thinkingmachines.ai`, [official support page](https://tinker-docs.thinkingmachines.ai/support/) | Before calls if possible; after data for a route-scoped factual review. The experiment need not wait indefinitely for a reply. |
| **J.J. Allaire / Meridian Labs, Inspect AI** | Inspect offers a path from a one-off finding to standard sample fields and evaluation tooling. | `info@meridianlabs.ai`, [official team page](https://meridianlabs.ai/team) | After a stable result: ask whether requested cap, observed native usage, finish reason, and censoring status belong in standard logs. |
| **Nathan Habib / Hugging Face LightEval** | LightEval is a practical independent implementation and distribution route. | Hugging Face direct message or GitHub `NathanHB`; [profile](https://huggingface.co/SaylorTwift), [LightEval docs](https://huggingface.co/docs/lighteval/) | After data: request schema review or an independent recipe. Do not rely on a historical commit email. |
| **Vector Institute AI Engineering, Toronto** | A geographically practical independent evaluation group with benchmark and Inspect experience. | `info@vectorinstitute.ai`, [official contact page](https://vectorinstitute.ai/about/contact/) | After initial confirmatory data: ask about artifact review or a small independent replication. |
| **Artificial Analysis** | Measures models, providers, latency, and pricing at the model-host pair level. | `hello@artificialanalysis.ai`, [official services page](https://artificialanalysis.ai/services/) | Post-data: ask whether they have seen requested-output versus billed-token discrepancies and propose a public independent route replication. |
| **DeepInfra inference engineering** | Relevant only if the GPT-OSS native-completion/reasoning meter anomaly remains in the manuscript. | `info@deepinfra.com`, [official model documentation](https://docs.deepinfra.com/models) | Post-data appendix courtesy note with the generation ID; ask whether tokenizer layers can explain the mismatch. |
| **xAI developer support** | The earlier 54,969-token observation was OpenRouter-to-xAI, not a direct xAI call. | [Official contact page](https://x.ai/contact) or developer Discord from the [official FAQ](https://docs.x.ai/developers/faq/general) | Post-data only if Grok remains in the paper; explicitly ask about the direct API's semantics without attributing the gateway result to xAI. |

### Funding and compute routes

- [OpenAI Researcher Access](https://openai.com/form/researcher-access-program/)
  currently offers eligible early-stage/resource-constrained researchers up to
  $1,000 in API credits, reviewed quarterly. This is the best documented route for
  a later direct closed-model replication. It is not a source of OpenRouter credits.
- [Tinker research grants](https://thinkingmachines.ai/news/tinker-research-and-teaching-grants/)
  start at $5,000 and are assessed on a rolling basis, but the stated program is for
  research involving training open-weight models. The present inference-only study
  is not an obvious fit and should not be distorted to qualify.
- [Together's research credits program](https://www.together.ai/research-credits-program-request)
  is described as invite-only and student-oriented. Connor's eligibility is not
  confirmed.
- [Hugging Face GPU Spaces](https://huggingface.co/docs/hub/main/spaces-gpus) can
  support a public interactive artifact and accepts free-upgrade requests, but it
  does not fund third-party API inference.

## Contact these five first

This portfolio answers five different questions before spending. It is not merely a
list of the five most famous people.

### 1. Daniel Kaiser

**Why him:** His three-part decomposition is closest to the proposed reporting
framework. A response can prevent an accidental novelty overclaim and improve the
outcome taxonomy.

**Show:** The one-page 2×2 design, the three outcomes, censoring bounds, and the
exploratory 30-item table.

**Avoid:** Claiming the decomposition is new or that cap-hit rows reveal latent
correctness.

**Low-friction request:** “Do these three outcomes and the interaction answer a
different question from your framework, or am I missing an existing analysis?”

### 2. Marthe Ballon

**Why her:** Her native-effort study is the closest factual precedent. Crossing both
efforts with both ceilings directly addresses a limitation relevant to her setup
without implying her study was defective.

**Show:** A single 2×2 diagram and the exact route-specific estimand.

**Avoid:** Saying different ceilings invalidate her findings. They answer a different
question.

**Low-friction request:** Ask whether she considers the effort-by-allowance
interaction scientifically useful and whether any o-series behavior suggests an
additional control.

### 3. Chirag Nagpal

**Why him:** He uniquely combines current LLM post-training work with formal
right-censoring expertise.

**Show:** The planned length survival summary, operational accuracy, counterfactual
accuracy bounds, and explicit statement that Kaplan-Meier will not be used for
correctness without assumptions.

**Avoid:** Treating correctness as a survival endpoint or claiming a larger-cap rerun
is a deterministic continuation.

**Low-friction request:** A terminology and partial-identification sanity check, not
a broad collaboration request.

### 4. Simone Caldarella

**Why him:** His prefix method directly addresses the second half of the title:
genuinely harmful overthinking.

**Show:** A few de-identified exploratory trace pairs, the automated final grades,
and the preregistered candidate taxonomy.

**Avoid:** Calling every completed high-effort error overthinking or claiming visible
reasoning is a faithful internal mechanism.

**Low-friction request:** Ask what minimum trace or intervention evidence he would
accept for the phrase “genuine overthinking.”

### 5. Ryan Steed

**Why him:** The highest-risk design choice is the tradeoff between two model panels
and repeated trials. His NIST work is directly about defining the estimand before
choosing an uncertainty procedure.

**Show:** The 30-item blocked factorial, the one-trial budget, the item-clustered
bootstrap plan, and the alternative two-trial budget.

**Avoid:** Asking NIST to endorse the project or expecting an extensive unpaid
analysis.

**Low-friction request:** One question: which claim is supportable with one trial per
cell, and which claim requires repeats?

**Fast-response alternates:** Gaurav Srivastava, Aryo Gema, Saurabh Srivastava,
Sangjun Song, and Pranjal Aggarwal are unusually close technically and appear more
accessible based on career stage and public contact preferences. This is an inference,
not a guarantee.

## Personalized email drafts

Each draft uses a placeholder for a repository or protocol URL because no public URL
has been verified. Replace the placeholder only with a real, accessible link. Attach
at most a one-page protocol and one figure. Do not send all five at once.

### Draft 1: Daniel Kaiser

**Subject:** Native effort × output cap question following *Beyond Accuracy*

Hello Daniel,

I'm Connor Klann, an independent researcher studying an evaluation artifact in
hosted reasoning models. In an exploratory 30-item AIME run on one pinned
OpenRouter-to-Together Inkling route, medium effort scored 25/30 with four
length-stopped responses, while max effort scored 21/30 with nine length stops.
One separately labeled pilot rerun changed a 20,000-token length stop with no answer
into a correct normal stop after 38,603 completion tokens. That is n=1 evidence, not
a confirmed effect.

Your clean-completion / conditional-correctness / token-consumption decomposition in
*Beyond Accuracy* is the closest framework I found. I have preregistered a 2×2 test
that crosses native effort with output allowance on the same items and reports three
outcomes separately: correct completion, completed wrong, and cap-hit/no answer. The
primary quantity is the effort-by-allowance interaction.

Would you be willing to give one narrow methods reaction: does this interaction
answer a meaningfully different question from your decomposition, or is there an
existing analysis I have missed? The one-page protocol is here: [VERIFIED PROTOCOL
LINK]. No confirmatory calls have been made yet, so this is the point at which a
correction would be most useful.

The limitations are substantial: one model route in the pilot, 30 fixed items,
stochastic independent reruns rather than continuations, and no proof that a completed
wrong answer is overthinking.

Thank you,

Connor Klann  
Independent Researcher  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)

**One follow-up after seven days:** I wanted to follow up once on the narrow outcome-taxonomy question below. Even a pointer to the closest analysis would be useful; no detailed review is expected.

### Draft 2: Marthe Ballon

**Subject:** Crossed effort and token ceilings as a follow-up to your o3-mini study

Hello Marthe,

I'm Connor Klann, an independent researcher preparing a small preregistered study of
native reasoning effort and output limits. Your Scientific Reports paper on o3-mini
is the closest native-effort study I found. In particular, it made me ask whether
effort and output allowance should be crossed rather than changed together.

The motivating pilot is route-specific and exploratory: on 30 AIME items using
Inkling through a pinned OpenRouter-to-Together route, medium effort scored 25/30
with four length stops, while max effort scored 21/30 with nine. One length-stopped
max-effort case later completed correctly with more room, but that is only one case
and the rerun was an independent stochastic generation.

The proposed confirmatory design runs both effort levels under both a 20,000-token
and a larger allowance on the same items. It tests whether the effort slope changes
when output room changes; it does not assume all completed errors are overthinking.

Could I ask one bounded question: do you consider the effort-by-allowance interaction
a useful complement to your analysis, and is there a control from your o3-mini work
that you would regard as essential? A one-page protocol is here: [VERIFIED PROTOCOL
LINK]. No confirmatory response has been generated.

Best,

Connor Klann  
Independent Researcher  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)

**One follow-up after seven days:** Following up once on the crossed effort/allowance question. A yes/no reaction or a citation I should read would be more than enough.

### Draft 3: Chirag Nagpal

**Subject:** Censored generation length versus correctness in a reasoning-model audit

Hello Chirag,

I'm Connor Klann, an independent researcher preregistering a route-specific audit of
reasoning effort and output caps. Your note on estimating generation length under a
fixed context window is directly relevant to a terminology and analysis problem I
want to get right before collecting confirmatory data.

The design crosses two native effort settings with two output allowances on the same
30 AIME items. A cap-hit response with no answer remains wrong for the utility of
that capped endpoint. I plan to call its generation length right-censored, treat its
counterfactual correctness with more room as unobserved, and report simple
correctness bounds. I do not plan to apply Kaplan-Meier to correctness.

The exploratory motivation is 25/30 at medium effort with four length stops versus
21/30 at max effort with nine on one OpenRouter-to-Together Inkling route. One
20,000-token cap hit later stopped normally and answered correctly after 38,603
tokens, but that n=1 rerun was independent and proves very little.

Would you be willing to sanity-check one point: is “right-censored generation
length with partially unidentified high-cap correctness” statistically accurate, or
would you recommend different language or bounds? The one-page protocol is here:
[VERIFIED PROTOCOL LINK]. No confirmatory call has been made.

Thank you,

Connor Klann  
Independent Researcher  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)

**One follow-up after seven days:** I am following up once on the censoring terminology below. A one-line correction or a pointer to the right method would be genuinely helpful; no broader commitment is being requested.

### Draft 4: Simone Caldarella

**Subject:** Token starvation versus harmful overthinking after *Thinking Past the Answer*

Hello Simone,

I'm Connor Klann, an independent researcher working on a small preregistered study
called *Thinking Cut Short*. Your distinction between verbose and harmful
overthinking is central to the line I am trying not to blur.

My exploratory result came from one pinned Inkling route on 30 AIME items. Medium
effort scored 25/30 with four length stops; max effort scored 21/30 with nine. One
max-effort row that had been stopped at 20,000 tokens with no answer later completed
correctly after 38,603 tokens when given more room. This suggests token starvation
can imitate a negative effort slope, but it does not show that every remaining
completed error is genuine overthinking.

The confirmatory plan crosses effort with allowance, keeps cap-hit/no-answer rows
separate from completed wrong rows, and labels the latter only as candidate
negative-scaling cases. Trace review cannot override the automated final grade.

Could I ask one precise question: in a black-box API setting without prefix logit
access, what minimum evidence would you accept before describing a completed error
as harmful or genuine overthinking? The one-page protocol is here: [VERIFIED
PROTOCOL LINK]. No confirmatory data have been collected.

Best,

Connor Klann  
Independent Researcher  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)

**One follow-up after seven days:** Following up once on the minimum-evidence question below. If the answer is simply “do not use that term without a prefix intervention,” that would be a valuable correction.

### Draft 5: Ryan Steed

**Subject:** Fixed-benchmark versus repeated-trial inference in a 30-item LLM factorial

Hello Dr. Steed,

I'm Connor Klann, an independent researcher preparing a preregistered evaluation of
reasoning-model output censoring. NIST AI 800-3 made me reconsider the estimand
before spending the study budget.

The proposed design uses 30 fixed AIME items in a blocked 2×2 factorial: native
reasoning effort (medium/max) by output allowance (20,000/49,152), with an
item-clustered bootstrap for the interaction. The current budget supports one
stochastic generation per item and cell on two model routes. Doubling trials would
require either dropping the second model, reducing items, or roughly doubling the
budget.

The intended narrow claim is operational and route-specific: whether the observed
effort slope on this fixed benchmark changes when the requested output allowance
changes. It is not a population-wide capability estimate, and cap-hit outputs remain
reported separately.

Could I ask one bounded question: is one trial per cell defensible for that narrow
fixed-benchmark estimand, provided the stochastic limitation is explicit, or would
you consider repeated trials necessary before interpreting the interaction at all?
The one-page protocol is here: [VERIFIED PROTOCOL LINK]. No confirmatory call has
been made.

Thank you,

Connor Klann  
Independent Researcher  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)

**One follow-up after seven days:** I wanted to follow up once on the fixed-benchmark/repeated-trial question. A brief methodological pointer is all I am seeking; I am not asking NIST to review or endorse the project.

## Recommended outreach sequence

### Before any paid call

1. Prepare the materials below and replace every placeholder with a verified public
   or read-only link.
2. Send **two** methods messages first: Daniel Kaiser and Chirag Nagpal. They cover
   outcome decomposition and censoring language. Wait four business days.
3. Send the Marthe Ballon and Ryan Steed messages. Ryan's request must explicitly
   say no NIST endorsement is sought.
4. Send Simone Caldarella's message after the trace rubric is a one-page appendix.
5. Send one technical ticket each to OpenRouter, Together, and the Inkling/Tinker
   team. Ask factual interface questions only. Record any answer and any resulting
   protocol amendment publicly before the first response.
6. Follow up once, seven calendar days later, only if the message remains unanswered.
   Stop after that.
7. After ten to fourteen days, either incorporate non-outcome-informed feedback in a
   dated committed amendment or document that the design is unchanged. Connor then
   makes the explicit run/no-run and budget choice.

### After confirmatory data but before submission

1. Send provider courtesy notes with exact generation IDs, request JSON, response
   fields, and the route-scoped factual sentence intended for the paper.
2. Ask Gaurav Srivastava, Aryo Gema, Shu Zhou, Sangjun Song, and Pranjal Aggarwal for
   a short technical reaction or independent replication.
3. Ask Hailey Schoelkopf or Michael Saxon for an artifact/provenance audit.
4. Ask one statistician to review the final estimand, transition counts, and
   uncertainty, without sharing only the most favorable result.

### After the repository and report are public

1. Approach Inspect/Meridian, LightEval, Vector Institute, and Artificial Analysis
   about integration or independent replication.
2. Apply to the OpenAI Researcher Access Program for a separately preregistered
   direct closed-model replication if that comparison remains useful.
3. Contact broader senior researchers or responsible amplifiers only when the raw
   data, request receipts, analysis code, limitations, and correction history are
   inspectable.

No one should be offered authorship for visibility. Authorship is appropriate only
for a substantive intellectual or experimental contribution under normal authorship
standards. Otherwise acknowledge useful feedback with permission.

## Materials required before outreach

1. **One-page methods summary:** research question, 2×2 diagram, estimand, three
   outcomes, hypotheses, and stop rules.
2. **Immutable preregistration link:** a public commit permalink, not only a mutable
   branch page.
3. **One exploratory table:** medium 25/30 with four length stops; max 21/30 with
   nine; one n=1 rescue. Label every number exploratory and route-specific.
4. **One route diagram:** caller → OpenRouter → pinned provider → model, including
   where effort, cap, usage, finish reason, and billing receipt are observed.
5. **Statistical appendix:** fixed-benchmark versus generalized estimand, repeated
   trial decision, paired interaction, transition counts, uncertainty procedure,
   multiplicity, missingness, and bounds.
6. **Trace rubric:** cap-hit/no answer, completed wrong, candidate harmful
   overthinking, parser failure, transport failure, and route mismatch.
7. **Data dictionary:** every JSONL field, units, null semantics, deduplication key,
   receipt linkage, and which row wins on rerun.
8. **Reproducibility bundle:** environment lock, exact request bodies with secrets
   removed, prompt and dataset hashes, schedule and seed, model ID, provider ID,
   date, precision/quantization or `unknown`, and analysis command.
9. **Budget ledger:** advertised rates, worst-case exposure, actual cost by call,
   hard stop, and untouched margin.
10. **Legal/redistribution check:** AIME question rights, provider terms for visible
    reasoning traces, and whether raw completions may be redistributed.
11. **Short limitations page:** make it readable before the results page. Include all
    risks below.
12. **Public identity:** Connor Klann, Independent Researcher, ORCID link, and a
    stable professional contact address. Do not imply an institutional affiliation.

## Credibility risks that could cause dismissal

1. **Novelty overclaim.** Output starvation and truncation are already established.
   The contribution is the native-effort × allowance interaction and route audit.
2. **Misusing “censoring.”** Generation length is right-censored; latent high-cap
   correctness is unobserved. Correctness is not automatically a survival outcome.
3. **Calling completed wrong “genuine overthinking.”** A normal stop plus a wrong
   answer does not establish answer abandonment.
4. **Independent reruns presented as continuations.** Without a shared seed and
   prefix continuation, a larger-cap rerun is a new stochastic sample.
5. **One generation per cell.** This omits within-item stochasticity. The claim and
   confidence procedure must reflect that or the design must add repeats.
6. **Small benchmark.** AIME-25 has 30 items. Percentage changes are lumpy, and a
   two-item change is 6.7 percentage points.
7. **Contamination and representativeness.** Public competition problems may have
   appeared in training, and AIME does not represent reasoning generally.
8. **Selection bias.** Completed-only accuracy will generally favor cases that finish;
   it must not replace conventional capped utility.
9. **Non-independent requested factors.** A gateway or provider may use
   `max_tokens` when mapping an effort label. A cap change may alter internal
   allocation, not merely remove a censor.
10. **Route-to-model overgeneralization.** The measured system includes OpenRouter,
    the pinned host, checkpoint/revision, precision, and date.
11. **Provider/model drift.** Aliases and serving revisions can change during a run.
    Pin what can be pinned and retain provider metadata for every row.
12. **Finish-reason trust.** A provider can impose a hidden limit or misreport usage.
    Reconcile request, normalized usage, native receipt, billed amount, and output.
13. **Visible reasoning is not privileged ground truth.** It can be incomplete,
    normalized, hidden, or unfaithful to internal computation.
14. **Outcome-informed pilot.** The pilot motivated the confirmatory hypotheses and
    must never be pooled with them.
15. **Multiple comparisons.** Two panels, mechanism outcomes, transitions, traces,
    and cost summaries create many opportunities for selective emphasis.
16. **Missing calls and retries.** Transport failures, billed failures, manual reruns,
    cache replays, and deduplication must remain visible.
17. **Provider feedback changing the protocol.** Technical clarification obtained
    before calls may justify an amendment; it must be dated and committed. Private
    advice after results cannot silently change the primary analysis.
18. **Reproducibility decay.** A proprietary route may disappear. Sanitized raw rows,
    receipts, and hashes are therefore part of the result, not optional supplements.
19. **Trace or dataset redistribution.** A public repo must respect model-provider and
    benchmark rights even if that means sharing hashes or derived annotations instead
    of full text.
20. **Paper title outrunning the evidence.** If the experiment only identifies cap
    rescue and completed negative scaling, the subtitle should avoid claiming that
    genuine overthinking itself was causally established.

## Final recommendation

Proceed with the paper, but do not start the paid experiment yet. The literature
supports a real, explainable gap: existing work typically changes reasoning effort,
changes token budget, forces a conclusion, or analyzes completed traces. The proposed
factorial asks whether a native effort curve changes when the output allowance is
independently manipulated and cap-hit responses are kept visible.

Before spending, resolve two questions:

1. Is the target claim a one-run fixed-benchmark route audit, or a stable stochastic
   model effect requiring repeat generations?
2. Will “genuine overthinking” be reserved for intervention/trajectory evidence, with
   all other normal-stop errors called completed negative-scaling cases?

If those are resolved and the route metadata can be pinned, the project has a
credible path to a rigorous and visible paper. The people most likely to improve it
scientifically are Kaiser, Ballon, Nagpal, Caldarella, Steed, Gema, Gaurav Srivastava,
Zhou, Song, and Aggarwal. Provider contacts can improve factual accuracy and
reproducibility, but they should not be treated as scientific validators.
