# lengthlab loop A run log

## 20260828-2107/1 HYPOTHESIS: Replace the single censored-lognormal fallback with a BIC-selected two-component censored lognormal mixture (EM with right-censoring), plus clamping extrapolated tail probabilities at the observed censored fraction, because the mixture/contaminated/pareto regimes dominate the misspecification error in q90 and P(length>=c) beyond the cap.

RESULT 20260828-2107/1: 0.035857  reverted (best 0.024558)

## 20260828-2107/2 HYPOTHESIS: Keep the single censored-lognormal Tobit fit but anchor all beyond-cap extrapolation (p_ge for c > cap, and the parametric median/q90 branches) to the exactly-identified empirical censored fraction, using the fit only for the conditional tail shape S(c)/S(cap), which removes the tail-level bias on misspecified mixture/pareto regimes without the instability of a mixture fit.

RESULT 20260828-2107/2: 0.026344  reverted (best 0.024558)

## 20260828-2119/1 HYPOTHESIS: Replace the Tobit-MLE lognormal fit used as the parametric fallback (unidentified median/q90, and p_ge extrapolation beyond cap) with a robust quantile-matching lognormal fit built from two empirically-identified clamped-data quantiles (falling back to the existing Tobit MLE when too little of the distribution is identified), since likelihood-based EM fitting is pulled off-shape by the bimodal/heavy-tail regimes (as seen in the two prior mixture/anchoring attempts) while quantile matching on identified order statistics should be less sensitive to that misspecification at n=500.

RESULT 20260828-2119/1: 0.041739  reverted (best 0.024558)

