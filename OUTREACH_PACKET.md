# Thinking Cut Short: pre-data outreach packet

**Prepared:** 2026-07-22
**Author:** Connor Klann, Independent Researcher
**ORCID:** https://orcid.org/0009-0002-5056-6670
**Status:** Drafts only. Nothing in this packet has been sent. No confirmatory API
call has been made.

## Purpose and boundary

The scientific messages ask for narrow methodological corrections before data
collection. They do not ask for endorsement, authorship, promotion, or a prediction
about the result. The provider messages ask for route and accounting facts. A vendor
reply is correspondence, not scientific validation or permission to publish.

Feedback may change terminology, validation checks, or analysis only through a dated
preregistration amendment committed before the first confirmatory response. It may
not change the fixed items, prompts, gold labels, grader, hypotheses, or design after
outcomes are observed.

## Send blockers

Do not send any message until all of these are true:

- Connor has explicitly approved the final text and the external send.
- Connor has explicitly approved pushing the current local commits to the public
  repository. A local commit is not a public link.
- Every link below returns without authentication in a private browser window.
- The sender address and signature are the ones Connor wants to use professionally.
- The public repository contains no secret, account identifier, balance, raw private
  trace, or environment file.

The local branch was 10 commits ahead of `origin/main` when this packet was prepared.
Consequently, the prospective GitHub URLs below are intentionally marked **inactive**.
They must not be placed into outgoing mail until the corresponding commits are
pushed and independently opened.

## Public link map after an approved push

| Material | Immutable prospective URL | Current state |
|---|---|---|
| Preregistered protocol | https://github.com/cwklurks/effort-atlas/blob/bc941bf118516cddafc671fcb9acc4607fd7ea33/PREREGISTRATION.md | Inactive until push |
| Methods brief | https://github.com/cwklurks/effort-atlas/blob/55d8bc500f298f02de2818294104a722ae058aa3/METHODS_BRIEF.md | Inactive until push |
| Frozen schedule manifest | https://github.com/cwklurks/effort-atlas/blob/55d8bc500f298f02de2818294104a722ae058aa3/confirmatory_artifacts/preflight-2026-07-22/schedule_manifest.json | Inactive until push |
| Exploratory cap audit | https://github.com/cwklurks/effort-atlas/blob/4ea36c7a819906c3ed77d37bc77b418aca2705de/CAP_SEMANTICS.md | Inactive until push |

The scientific emails need only the protocol and methods-brief links. Provider
tickets should include the protocol and schedule-manifest links. Do not attach raw
responses or reasoning traces. If a support form does not accept links, attach a PDF
rendering of the methods brief only after confirming it matches the committed text.

## First scientific message: Daniel Kaiser

**Verified recipient:** `daniel.kaiser@uit.no`
**Source:** https://en.uit.no/ansatte/person?p_document_id=856406
**Subject:** 10-minute methods question on effort x output allowance

Hello Daniel,

I'm Connor Klann, an independent researcher preparing a small route-specific
evaluation of reasoning effort and output limits.

Your *Beyond Accuracy* decomposition is the closest framework I found. I have
preregistered a 2x2 design crossing two native effort settings with two requested
output allowances on the same 30 fixed AIME items. Each response is classified as a
correct normal completion, completed wrong answer, or cap-hit/no-final-answer. The
primary quantity is whether the effort slope changes with allowance.

Could you spare 10 minutes for one narrow reaction: does this interaction answer a
meaningfully different question from your decomposition, or is there an existing
analysis I should use instead?

No confirmatory API calls or data exist. The exploratory motivation is separated
and will not be pooled with confirmatory estimates.

Protocol: [VERIFIED IMMUTABLE PROTOCOL LINK]
Methods brief: [VERIFIED METHODS BRIEF LINK]

Thank you,

Connor Klann
Independent Researcher
ORCID: https://orcid.org/0009-0002-5056-6670

## Second scientific message: Chirag Nagpal

**Verified recipient:** `chiragn@alumni.cmu.edu`
**Source:** https://chiragnagpal.github.io/
**Subject:** 10-minute terminology check: censored generation length

Hello Chirag,

I'm Connor Klann, an independent researcher preparing a small route-specific audit
of reasoning effort and output limits. Your note on estimating generation length
under a fixed context window is directly relevant.

The preregistered design crosses two native effort settings with two output
allowances on the same 30 fixed AIME items. A cap-hit response with no extractable
final answer remains wrong for capped-endpoint accuracy. I plan to describe its
generation length as right-censored, its correctness with more allowance as
unobserved, and to report simple bounds rather than apply Kaplan-Meier to
correctness.

Could you spare 10 minutes for one narrow check: is "right-censored generation
length with unobserved higher-cap correctness" accurate language, or would you
recommend different terminology or bounds?

No confirmatory API calls or data exist.

Protocol: [VERIFIED IMMUTABLE PROTOCOL LINK]
Methods brief: [VERIFIED METHODS BRIEF LINK]

Thank you,

Connor Klann
Independent Researcher
ORCID: https://orcid.org/0009-0002-5056-6670

## OpenRouter technical inquiry

**Verified channel:** support ticket at https://openrouter.ai/support
**Alternative address listed by OpenRouter for billing/account questions:**
`support@openrouter.ai`
**Subject:** Preregistered benchmark: route and accounting questions before paid calls

Hello OpenRouter Support,

I'm Connor Klann, an independent researcher preparing a preregistered benchmark of
reasoning effort x output cap. Before any new paid calls, could you clarify Chat
Completions behavior for `thinkingmachines/inkling` and `z-ai/glm-5.2` when
`provider.only=["together"]`, `allow_fallbacks=false`, and
`require_parameters=true`?

1. Does this prevent provider, model, or checkpoint substitution? Which returned
   fields identify the served provider, model revision/permaslug, endpoint, and
   precision or quantization?
2. How are the requested reasoning efforts mapped upstream for these routes? Does
   `max_tokens` bound reasoning plus visible output, and can the cap alter reasoning
   allocation?
3. Are unsupported reasoning, cap, or routing parameters rejected rather than
   silently dropped or mapped?
4. Which streamed usage and finish-reason fields are normalized? Which generation
   receipt fields are authoritative for native prompt, completion, and reasoning
   tokens, native finish reason, cost, provider, and linkage IDs?

Protocol: [VERIFIED IMMUTABLE PROTOCOL LINK]
Frozen schedule: [VERIFIED SCHEDULE MANIFEST LINK]

Any response will be documented as provider correspondence, not endorsement. We
will not publish secrets or raw traces. Thank you.

## Together technical inquiry

**Verified channel:** Submit a Ticket at https://support.together.ai/
**Channel source:** https://docs.together.ai/docs/support
**Subject:** Preregistered benchmark: Together route semantics before paid calls

Hello Together Support,

I'm Connor Klann, an independent researcher preparing a preregistered benchmark
through OpenRouter with Together pinned as provider. Before any new paid calls,
could you clarify the current behavior for Together-hosted
`thinkingmachines/inkling` and `z-ai/glm-5.2`?

1. What checkpoint or revision is served for each model and, if disclosable, what
   precision or quantization is used?
2. Which native reasoning-effort values are accepted, and how do OpenRouter's
   requested labels map to Together's controls?
3. Does `max_tokens` bound reasoning plus visible output, visible output only, or
   another quantity? Can the cap change reasoning allocation?
4. Which native fields report prompt, completion, reasoning, and cached tokens;
   native finish reason; cost; and request or response IDs that reconcile with an
   OpenRouter generation receipt?
5. Is an unsupported parameter rejected or defaulted? With gateway fallbacks
   disabled, can any upstream substitution still occur?

Protocol: [VERIFIED IMMUTABLE PROTOCOL LINK]
Frozen schedule: [VERIFIED SCHEDULE MANIFEST LINK]

This requests factual interface clarification, not endorsement. We will not include
secrets or raw traces.

## What is blocking and what is metadata-only

| Question | Classification | Action if unanswered |
|---|---|---|
| Provider is pinned and no substitution occurs | Blocking | Route cannot pass the smoke gate without a matching receipt/provider identity. |
| Requested effort is accepted and meaningfully distinguished | Blocking | Stop that panel if the request is rejected or silently normalized in a way that destroys the contrast. |
| `max_tokens` includes all billed generation for the route | Blocking | Stop that panel if native completion exceeds the requested cap. |
| Native usage, finish reason, cost, and IDs reconcile | Blocking | An unaccounted call is missing and receives no automatic retry. |
| Exact checkpoint/revision | Metadata-only if undisclosed | Record `unknown` and keep the claim route- and date-specific. |
| Precision, quantization, and hardware | Metadata-only if undisclosed | Record `unknown`; do not infer it from a model release. |

Provider silence is not evidence that the assumptions are true. If no provider
answers, the preregistered smoke gates remain the operational test. A route that
cannot satisfy those gates is stopped and reported as missing; another provider is
not substituted after outcomes are seen.

## Timing and follow-up

1. After explicit approval, publish and verify the immutable links.
2. Send Daniel Kaiser and Chirag Nagpal on the same day as separate personal
   messages. Send the OpenRouter and Together technical inquiries that day as
   separate support tickets.
3. Wait four business days before deciding whether methodological feedback requires
   a pre-data amendment. A provider ticket may remain open for up to five business
   days; do not imply that silence is confirmation.
4. Send one follow-up only, seven calendar days after an unanswered initial message:
   "Following up once on the narrow question below. A one-line correction or pointer
   would be very helpful; no detailed review is expected."
5. Stop after that follow-up. Record replies or no reply. Connor then makes a
   separate, explicit run/no-run decision before any paid smoke call.

## Documentation checked on 2026-07-22

- OpenRouter support: https://openrouter.ai/support
- OpenRouter provider routing: https://openrouter.ai/docs/guides/routing/provider-selection
- OpenRouter reasoning controls: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
- OpenRouter usage accounting: https://openrouter.ai/docs/cookbook/administration/usage-accounting
- OpenRouter generation receipts: https://openrouter.ai/docs/api/api-reference/generations/get-generation
- Together support: https://docs.together.ai/docs/support
- Together reasoning: https://docs.together.ai/docs/inference/chat/reasoning
- Together chat-completion reference: https://docs.together.ai/reference/chat-completions
- Chirag Nagpal's generation-length note: https://chiragnagpal.github.io/papers/llm_length_kaplan_meier_25.pdf

OpenRouter currently documents that provider fallbacks default to enabled and
required-parameter enforcement defaults to disabled, so both must be set explicitly.
It also documents reasoning tokens as output tokens for billing. Together currently
describes `max_tokens` as a cap on total output and warns that complex reasoning may
be truncated. Those general statements do not establish the behavior of the two
specific pinned routes; that is why the provider questions and paid smoke gates are
still necessary.
