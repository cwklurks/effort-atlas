"""Loop B scorer — FROZEN SURFACE. Design power at fixed budget.

Prints ONE number (higher is better): the WORST-CASE detection power across
the effect scenarios, subject to two hard constraints checked first:

  * calibration: on every null scenario, the rejection count must be
    statistically consistent with a true type-I rate <= ALPHA_NOMINAL
    (one-sided binomial gate at GATE_CONF; Monte Carlo noise alone cannot
    zero an honest test, but a genuinely anticonservative one fails)
  * expected spend of the design <= BUDGET_USD  (else prints 0.0)

Worst-case + hard constraints is deliberate: a design cannot win by nailing
one friendly scenario or by an anticonservative test.

DGP (review with the statistical supervisor; assumptions, not truth):
  item difficulty d_i ~ N(0,1); latent P(correct) = sigmoid(BASE - d_i + b_e)
  with effort benefit b_hi > b_lo; lengths from a lengthlab regime, scaled by
  LEN_MULT at high effort; a response longer than its allowance is an
  unanswered length stop and scores 0 under the unchanged conventional grader.
  The estimand is slope(big) - slope(small) on conventional accuracy — the
  mechanical censoring effect the paper studies. Null scenarios set both
  allowances equal, making the estimand exactly 0 by symmetry.

Usage mirrors score_recovery.py (--repeat, --json). Editable: design.py only.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

import generator as G
import design as D

BUDGET_USD = 40.0
PRICE_OUT_PER_MTOK = 4.05     # July config figure; sim constant, not a claim
ALPHA_NOMINAL = 0.05
GATE_CONF = 0.95
N_SIMS = 400


def _binom_crit(n: int, p: float, conf: float) -> int:
    """Smallest k such that P(X > k) < 1-conf for X~Binom(n,p): reject counts
    above k are inconsistent with a true rate <= p."""
    from math import comb
    acc, k = 0.0, -1
    for i in range(n + 1):
        acc += comb(n, i) * p**i * (1 - p) ** (n - i)
        if acc >= conf:
            k = i
            break
    return k if k >= 0 else n


TYPE1_CRIT = _binom_crit(N_SIMS, ALPHA_NOMINAL, GATE_CONF)  # max allowed rejections
BASE, B_LO, B_HI = 0.4, 0.0, 0.35
LEN_MULT_HI = 2.0

POWER_SCENARIOS = [
    ("ln_mid", 8000, 32000),
    ("mix_bimodal", 8000, 32000),
    ("tail_pareto", 14096, 32000),
]
NULL_SCENARIOS = [
    ("ln_mid", 32000, 32000),
    ("mix_bimodal", 32000, 32000),
]

CELLS = (("lo", "sm"), ("hi", "sm"), ("lo", "big"), ("hi", "big"))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def simulate_once(regime, allow_sm, allow_big, n_items, n_reps, rng):
    d = rng.normal(0, 1, n_items)
    acc, spend_tokens = {}, 0.0
    for eff, allow_name in CELLS:
        allowance = allow_sm if allow_name == "sm" else allow_big
        b = B_HI if eff == "hi" else B_LO
        mult = LEN_MULT_HI if eff == "hi" else 1.0
        p = _sigmoid(BASE - d + b)
        cell = np.zeros(n_items)
        for _ in range(n_reps):
            length = G.sample(regime, n_items, rng) * mult
            answered = length < allowance
            correct = (rng.random(n_items) < p) & answered
            cell += correct.astype(float)
            spend_tokens += float(np.minimum(length, allowance).sum())
        acc[(eff, allow_name)] = cell / n_reps
    return acc, spend_tokens


def run(base_seed: int, regimes: dict | None = None,
        power_scenarios=POWER_SCENARIOS, null_scenarios=NULL_SCENARIOS) -> dict:
    """regimes defaults to the visible set; final_eval.py passes holdouts."""
    regimes = regimes if regimes is not None else G.VISIBLE_REGIMES
    n_items, n_reps, alpha = D.DESIGN["n_items"], D.DESIGN["n_reps"], D.DESIGN["alpha"]
    out = {"powers": {}, "type1": {}, "type1_counts": {}, "mean_cost_usd": 0.0}
    costs = []
    for kind, scenarios in (("powers", power_scenarios), ("type1", null_scenarios)):
        for si, (rname, a_sm, a_big) in enumerate(scenarios):
            reg = regimes[rname]
            rej = 0
            for s in range(N_SIMS):
                rng = np.random.default_rng(base_seed + 7919 * si + s + (0 if kind == "powers" else 10**6))
                acc, tokens = simulate_once(reg, a_sm, a_big, n_items, n_reps, rng)
                costs.append(tokens / 1e6 * PRICE_OUT_PER_MTOK)
                if D.analyze(acc) < alpha:
                    rej += 1
            out[kind][f"{rname}@{a_sm}v{a_big}"] = rej / N_SIMS
            if kind == "type1":
                out["type1_counts"][f"{rname}@{a_sm}v{a_big}"] = rej
    out["mean_cost_usd"] = float(np.mean(costs))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--base-seed", type=int, default=20260830)
    args = ap.parse_args()

    scores, last = [], None
    for r in range(args.repeat):
        res = run(args.base_seed + 31 * r)
        last = res
        worst_count = max(res["type1_counts"].values())
        score = 0.0
        if worst_count <= TYPE1_CRIT and res["mean_cost_usd"] <= BUDGET_USD:
            score = min(res["powers"].values())
        scores.append(score)
    if args.json:
        print(json.dumps({"scores": scores, "last_run": last}, indent=1))
    elif args.repeat > 1:
        print(f"mean {np.mean(scores):.6f} sd {np.std(scores):.6f} "
              f"runs {[round(x, 6) for x in scores]} "
              f"(type1 {last['type1']}, cost ${last['mean_cost_usd']:.2f})")
    else:
        print(f"{scores[0]:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
