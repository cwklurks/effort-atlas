# First-five exploratory launch revision, September 15, 2026

Connor authorized setup of the first five questions from the existing 1,000-item
medium plan under explicit provider assumptions, followed by a mandatory pause.
The original question selection, prompts, 32,768 output cap and scientific grading
are unchanged. The existing actual tokenizer report remains valid.

## What changed

- A distinct first-five evidence schema records assumed account prices, research
  credit eligibility and reasoning-inclusive cap/usage semantics. These three
  checks must remain false. Other checks still require supporting evidence.
- The account journal records the dated first-five decision in the reservation.
  Both journal replay and attempt submission refuse a sixth attempt before review.
  Restart, optional invocation limits and replacement launch evidence cannot reset
  the cumulative gate. Initial medium collection requires the first-five schema.
- After five complete uncapped responses, the runner emits a blank review template
  with the exact saved response hashes. It pauses before creating a new client on
  relaunch. A cap stop or uncertain attempt prevents normal continuation.
- Continuing requires a separate human artifact with current execution/account/plan
  identity, exact ordered response hashes, review time after the responses, all
  explicit checks, review notes, available billing evidence and express acceptance
  of residual assumptions. No continuation is approved in this change.
- The reviewed release is durable and does not release the full-stage financial
  reservation. Stored response and review artifacts remain authenticated on restart.

## Cost and scientific limits

The $250 medium and $250 conditional max ceilings, full-stage reservation and
$3,000 reserve remain unchanged. Projections use assumed rates and are not a
provider-enforced dollar guarantee. Existing exact final reconciliation remains
required. Five ordinary completions do not prove cap-collision semantics or
account-specific billing. The max stage cannot use the new exception.

The previous first-five optional pause was per invocation; this revision supersedes
its restart instructions for the initial medium launch. Old launch execution hashes
are invalid. Frozen historical artifacts and confirmatory gates are untouched.

## Verification and handoff

Two new contract/journal regressions were run before implementation and failed on
the missing first-five schema and reservation argument. Focused offline tests now
pass, including real SDK mock-transport initial pause, restart, old-record refusal,
wrong/stale/unapproved reviews and authenticated continuation. Mac verification: canonical 256 tests run, 255 passed with one optional source-rebuild skip; 20 supplemental upstream/SDK tests passed. Both 1,000-item synthetic rehearsals passed. Independent Sol XHigh review identified stale-execution review reuse and legacy unrestricted reservation bypass; both were repaired with regressions. Re-review is clean after 44 independently rerun offline checks. A changed execution after continuation review now refuses; an existing unrestricted medium reservation requires reviewed migration and is never erased. The box is unreachable; installation and updated host verification are pending. No provider calls were made by Codex.
