# lengthlab loop A run log

## 20260828-2107/1 HYPOTHESIS: Replace the single censored-lognormal fallback with a BIC-selected two-component censored lognormal mixture (EM with right-censoring), plus clamping extrapolated tail probabilities at the observed censored fraction, because the mixture/contaminated/pareto regimes dominate the misspecification error in q90 and P(length>=c) beyond the cap.

RESULT 20260828-2107/1: 0.035857  reverted (best 0.024558)

## 20260828-2107/2 HYPOTHESIS: Keep the single censored-lognormal Tobit fit but anchor all beyond-cap extrapolation (p_ge for c > cap, and the parametric median/q90 branches) to the exactly-identified empirical censored fraction, using the fit only for the conditional tail shape S(c)/S(cap), which removes the tail-level bias on misspecified mixture/pareto regimes without the instability of a mixture fit.

RESULT 20260828-2107/2: 0.026344  reverted (best 0.024558)

