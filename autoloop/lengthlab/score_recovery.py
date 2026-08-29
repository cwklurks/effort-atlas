"""Loop A scorer — FROZEN SURFACE. Estimator recovery under censoring.

Prints ONE number (lower is better): mean absolute relative error of the
editable estimator's median / q90 / P(length >= c) against generator truth,
across visible regimes x observation caps x Monte Carlo seeds.

Usage:
    python score_recovery.py                # loop metric (visible regimes)
    python score_recovery.py --repeat 5     # spread, for setting min_delta
    python score_recovery.py --json         # per-regime breakdown to stdout

The loop must never edit this file or generator.py. Editable: estimators.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib

import numpy as np

import generator as G
import estimators as E

N_PER_SAMPLE = 500          # rows per simulated dataset (pilot-sized: 200-1000)
OBS_CAPS = (8000, 14096, 32000)   # caps at which data is *collected*
REPORT_CAPS = G.CAPS
SEEDS_PER_CELL = 6


def score_regimes(regimes: dict, base_seed: int) -> tuple[float, dict]:
    errs = []
    detail = {}
    for name, reg in regimes.items():
        t = G.truth(reg)
        reg_errs = []
        for cap in OBS_CAPS:
            for s in range(SEEDS_PER_CELL):
                rng = np.random.default_rng(base_seed * 100_003 + zlib.crc32(name.encode()) % 65_521 + cap + s)
                x = G.sample(reg, N_PER_SAMPLE, rng)
                obs, cen = G.censor(x, cap)
                est = E.estimate(obs, cen, cap, caps=REPORT_CAPS)
                e = [
                    abs(est["median"] - t["median"]) / t["median"],
                    abs(est["q90"] - t["q90"]) / t["q90"],
                ]
                for c in REPORT_CAPS:
                    e.append(abs(est["p_ge"][c] - t["p_ge"][c]))
                reg_errs.append(float(np.mean(e)))
        errs.extend(reg_errs)
        detail[name] = float(np.mean(reg_errs))
    return float(np.mean(errs)), detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--base-seed", type=int, default=20260830)
    args = ap.parse_args()

    scores = []
    for r in range(args.repeat):
        s, detail = score_regimes(G.VISIBLE_REGIMES, args.base_seed + r)
        scores.append(s)
    if args.json:
        print(json.dumps({"scores": scores, "per_regime": detail}, indent=1))
    elif args.repeat > 1:
        print(f"mean {np.mean(scores):.6f} sd {np.std(scores):.6f} "
              f"runs {[round(x, 6) for x in scores]}")
    else:
        print(f"{scores[0]:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
