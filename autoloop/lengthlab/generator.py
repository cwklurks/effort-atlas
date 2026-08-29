"""lengthlab synthetic generator — FROZEN SURFACE.

EXPLORATORY TOOLING. Not part of any confirmatory path. No provider calls;
this module never imports effort_atlas.client and has no network code.

The optimization loop must NEVER edit this file (list it in `protected`).
It defines the data-generating processes (DGPs) both scorers use. If the loop
can edit the world it is scored on, its scores are fiction.

Regimes
-------
VISIBLE_REGIMES are what the loop trains against. Held-out regimes are drawn
by `holdout_regimes(seed)` from wider parameter ranges plus a contamination
family; the seed lives OUTSIDE the repo (env var LENGTHLAB_HOLDOUT_SEED,
supplied only when a human runs final_eval.py). The holdout *code* is visible
here by necessity; the holdout *parameters* are not reachable without the seed.

Anchoring: medians/sigmas bracket what the project has observed so far
(pilot config expects ~5k median output tokens at medium effort; observational
lognormal fits span roughly sigma 0.5-1.5). The Inkling pilot will re-anchor
these ranges; regenerate VISIBLE_REGIMES then, as a new dated decision, and
rerun the loop rather than editing results.
"""
from __future__ import annotations

import numpy as np

# Caps mirror config_pilot_inkling.yaml report_caps plus the pilot allowance.
CAPS = (4096, 8000, 14096, 16000, 20000, 32000)

# name -> dict(family, params)
VISIBLE_REGIMES = {
    # single lognormal, short / mid / long medians
    "ln_short": {"family": "lognormal", "median": 1200, "sigma": 0.6},
    "ln_mid": {"family": "lognormal", "median": 5000, "sigma": 0.9},
    "ln_long": {"family": "lognormal", "median": 9000, "sigma": 1.1},
    # two-mode mixture: quick answers + long reasoning chains
    "mix_bimodal": {
        "family": "mixture",
        "w": 0.55, "median1": 900, "sigma1": 0.5, "median2": 11000, "sigma2": 0.7,
    },
    "mix_heavy": {
        "family": "mixture",
        "w": 0.75, "median1": 3000, "sigma1": 0.8, "median2": 20000, "sigma2": 0.5,
    },
    # lognormal body with a Pareto tail (runaway reasoning)
    "tail_pareto": {
        "family": "pareto_tail",
        "median": 4000, "sigma": 0.8, "tail_frac": 0.08, "tail_alpha": 1.4,
        "tail_min": 12000,
    },
}


def _sample_lognormal(rng, n, median, sigma):
    return rng.lognormal(mean=np.log(median), sigma=sigma, size=n)


def sample(regime: dict, n: int, rng: np.random.Generator) -> np.ndarray:
    """True (uncensored) token lengths for one regime. Positive floats."""
    fam = regime["family"]
    if fam == "lognormal":
        x = _sample_lognormal(rng, n, regime["median"], regime["sigma"])
    elif fam == "mixture":
        pick = rng.random(n) < regime["w"]
        a = _sample_lognormal(rng, n, regime["median1"], regime["sigma1"])
        b = _sample_lognormal(rng, n, regime["median2"], regime["sigma2"])
        x = np.where(pick, a, b)
    elif fam == "pareto_tail":
        x = _sample_lognormal(rng, n, regime["median"], regime["sigma"])
        tail = rng.random(n) < regime["tail_frac"]
        ntail = int(tail.sum())
        if ntail:
            x[tail] = regime["tail_min"] * (1.0 + rng.pareto(regime["tail_alpha"], ntail))
    elif fam == "contaminated":  # holdout-only family
        x = _sample_lognormal(rng, n, regime["median"], regime["sigma"])
        c = rng.random(n) < regime["c_frac"]
        nc = int(c.sum())
        if nc:
            x[c] = _sample_lognormal(rng, nc, regime["c_median"], regime["c_sigma"])
    else:
        raise ValueError(f"unknown family {fam!r}")
    return np.maximum(x, 1.0)


def censor(lengths: np.ndarray, cap: int):
    """Right-censor at cap. Returns (observed, is_censored)."""
    is_c = lengths >= cap
    return np.minimum(lengths, cap), is_c


def truth(regime: dict, caps=CAPS, n: int = 400_000, seed: int = 7) -> dict:
    """Ground-truth quantities via a large uncensored draw (fixed seed)."""
    rng = np.random.default_rng(seed)
    x = sample(regime, n, rng)
    return {
        "median": float(np.median(x)),
        "q90": float(np.quantile(x, 0.90)),
        "p_ge": {c: float(np.mean(x >= c)) for c in caps},
    }


def holdout_regimes(seed: int) -> dict:
    """Held-out regimes from wider ranges + a contamination family.

    Deterministic in `seed`. The loop never receives the seed; a human sets
    LENGTHLAB_HOLDOUT_SEED only when running final_eval.py. Do not commit the
    seed anywhere in the repo.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for i in range(2):
        out[f"holdout_ln_{i}"] = {
            "family": "lognormal",
            "median": float(rng.uniform(600, 15000)),
            "sigma": float(rng.uniform(0.4, 1.6)),
        }
    out["holdout_mix"] = {
        "family": "mixture",
        "w": float(rng.uniform(0.3, 0.85)),
        "median1": float(rng.uniform(500, 4000)),
        "sigma1": float(rng.uniform(0.4, 1.0)),
        "median2": float(rng.uniform(8000, 26000)),
        "sigma2": float(rng.uniform(0.4, 1.0)),
    }
    out["holdout_contam"] = {
        "family": "contaminated",
        "median": float(rng.uniform(2000, 8000)),
        "sigma": float(rng.uniform(0.5, 1.2)),
        "c_frac": float(rng.uniform(0.03, 0.15)),
        "c_median": float(rng.uniform(18000, 30000)),
        "c_sigma": float(rng.uniform(0.3, 0.8)),
    }
    return out
