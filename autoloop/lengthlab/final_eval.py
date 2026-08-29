"""Held-out evaluation — FROZEN SURFACE. Humans only; never part of the loop.

Scores the current editable files (estimators.py, design.py) on regimes the
loop has never seen. The holdout parameters derive from LENGTHLAB_HOLDOUT_SEED,
which must live outside the repo (and ideally outside shell history: `read -s`).
Refuses to run without it. Report THESE numbers alongside the loop's visible
numbers; a large gap between them means the loop overfit the visible regimes.

    LENGTHLAB_HOLDOUT_SEED=<secret int> python final_eval.py
"""
from __future__ import annotations

import json
import os
import sys

import generator as G
import score_recovery as SR
import score_power as SP


def main() -> int:
    seed_s = os.environ.get("LENGTHLAB_HOLDOUT_SEED")
    if not seed_s:
        print("LENGTHLAB_HOLDOUT_SEED is unset. This script is for the human "
              "holdout evaluation only; it refuses to guess a seed.",
              file=sys.stderr)
        return 2
    hold = G.holdout_regimes(int(seed_s))

    # Loop A on holdout: same scorer, unseen regimes.
    rec_score, rec_detail = SR.score_regimes(hold, base_seed=20260830)

    # Loop B on holdout: same cap pairs as the visible scenarios, holdout DGPs.
    power_scenarios = [
        ("holdout_ln_0", 8000, 32000),
        ("holdout_ln_1", 8000, 32000),
        ("holdout_mix", 8000, 32000),
        ("holdout_contam", 14096, 32000),
    ]
    null_scenarios = [
        ("holdout_ln_0", 32000, 32000),
        ("holdout_mix", 32000, 32000),
    ]
    res = SP.run(20260830, regimes=hold,
                 power_scenarios=power_scenarios, null_scenarios=null_scenarios)
    worst_count = max(res["type1_counts"].values())
    feasible = worst_count <= SP.TYPE1_CRIT and res["mean_cost_usd"] <= SP.BUDGET_USD
    power_score = min(res["powers"].values()) if feasible else 0.0

    print(json.dumps({
        "holdout_recovery_score": rec_score,
        "holdout_recovery_per_regime": rec_detail,
        "holdout_power_score": power_score,
        "holdout_power_detail": res,
        "type1_crit": SP.TYPE1_CRIT,
        "note": "report these numbers, not the loop's visible-regime numbers",
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
