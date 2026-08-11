# Phase 3 Claude/Codex adversarial-loop objective

Review the current `codex/prereg-v2` Phase 3 artifacts claim by claim. The purpose
is to converge on an evidence-backed recommendation, not to manufacture agreement
between two models.

Read `AGENTS.md` and `reap/CODEX_BRIEFING.md` first, followed by:

- `reap/13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md`
- `reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md`
- `reap/review_artifacts/2026-08-10/README.md`
- `reap/review_artifacts/2026-08-10/reap_costs.py`
- `reap/review_artifacts/2026-08-10/reap_costs.out.txt`
- `reap/review_artifacts/2026-08-10/reap_sims.py`
- `reap/review_artifacts/2026-08-10/reap_sims.out.txt`
- the Phase 3 decision, status, grader, and analysis tests relevant to each claim

No provider, smoke, paid research-generation, probe, or confirmatory call is
allowed. Do not inspect or reproduce secrets. Work read-only. Existing frozen
artifacts remain frozen.

## Claims requiring adversarial resolution

- **C01, dataset scope:** Determine whether the review consistently chooses a
  30-row HMMT-2026 core or expects all 33 current rows. Identify every remaining
  contradiction and state exactly what provenance remains unresolved for rows
  31-33.
- **C02, Terra semantics:** Determine whether all passages now consistently use the
  documented GPT-5.6 family effort set `none/low/medium/high/xhigh/max`, exclude
  `minimal`, distinguish family documentation from route-specific smoke evidence,
  and describe benchmark exposure as possible rather than proven.
- **C03, cost provenance:** Distinguish independently recomputed arithmetic from
  constants copied into a scratchpad. Check whether the scripts actually encode
  current separate input/output and list/discount rates, derive every displayed
  total, and identify a dated primary-source rate snapshot.
- **C04, H6 simulation fidelity:** Determine which numerical results are exactly
  reproducible and which depend on a simplified generative model. Check whether
  the simulation shares item-level large-cap length structure across thresholds
  and matches the planned estimator. Leave Chirag's power rerun as the scientific
  authority where required.
- **C05, scorer boundary:** Determine whether the proposed pipeline, grader-v2
  extraction to a pinned MathArena `parse_answer`/`check_answers` path, exists only
  in prose or is implemented and mutation-tested. Preserve the ban on MathArena
  answer scavenging and LLM judging.
- **C06, durable state:** Check whether the briefing, Phase 3 status JSON, rendered
  dashboard, branch head, test count, and external-review disposition agree.
- **C07, scratchpad provenance:** Distinguish verified byte identity within the
  committed artifacts from the stronger historical claim that files were copied
  verbatim from an earlier external session. State what original hash or timestamp
  would be needed to prove that stronger claim.

For each claim use exactly one verdict: `CONFIRMED`, `PARTIALLY_CONFIRMED`,
`REFUTED`, or `UNVERIFIABLE`. Attach exact repository evidence and classify the
claim as a repository fact, mutable external fact, statistical judgment, or human
decision. Consensus without evidence does not close a claim.

The models may recommend decisions. They must not approve spending, a live or
smoke call, provider activation, preregistration freeze, or any decision owned by
Connor or Chirag. The final synthesis must list those human gates separately.
