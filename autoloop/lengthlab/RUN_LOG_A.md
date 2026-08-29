# lengthlab loop A run log

## 20260828-2107/1 HYPOTHESIS: Replace the single censored-lognormal fallback with a BIC-selected two-component censored lognormal mixture (EM with right-censoring), plus clamping extrapolated tail probabilities at the observed censored fraction, because the mixture/contaminated/pareto regimes dominate the misspecification error in q90 and P(length>=c) beyond the cap.

RESULT 20260828-2107/1: 0.035857  reverted (best 0.024558)

## 20260828-2107/2 HYPOTHESIS: Keep the single censored-lognormal Tobit fit but anchor all beyond-cap extrapolation (p_ge for c > cap, and the parametric median/q90 branches) to the exactly-identified empirical censored fraction, using the fit only for the conditional tail shape S(c)/S(cap), which removes the tail-level bias on misspecified mixture/pareto regimes without the instability of a mixture fit.

RESULT 20260828-2107/2: 0.026344  reverted (best 0.024558)

## 20260828-2119/1 HYPOTHESIS: Replace the Tobit-MLE lognormal fit used as the parametric fallback (unidentified median/q90, and p_ge extrapolation beyond cap) with a robust quantile-matching lognormal fit built from two empirically-identified clamped-data quantiles (falling back to the existing Tobit MLE when too little of the distribution is identified), since likelihood-based EM fitting is pulled off-shape by the bimodal/heavy-tail regimes (as seen in the two prior mixture/anchoring attempts) while quantile matching on identified order statistics should be less sensitive to that misspecification at n=500.

RESULT 20260828-2119/1: 0.041739  reverted (best 0.024558)

## 20260828-2119/2 HYPOTHESIS: Leave the Tobit-lognormal fit and the beyond-cap p_ge extrapolation untouched (three straight attempts to change the parametric tail model or its anchoring all made things worse), and instead replace the hard cen_frac threshold switches for median (0.5) and q90 (0.10) with a smoothstep blend between the empirical cap-substituted estimate and the parametric estimate over a narrow band around each threshold, since Monte Carlo noise in cen_frac at n=500 likely pushes borderline samples back and forth across the hard cutoff, adding avoidable variance right at the identifiability boundary that a smooth handoff should reduce without touching the parts of the estimator three prior attempts already showed are fragile.

RESULT 20260828-2119/2: 0.024703  reverted (best 0.024558)

## STRATEGY 20260828-2119/2 (reviewer):

(a) Diagnosis: All four attempts attacked the parametric fallback itself — replacing the fit (mixture EM 0.0359, quantile matching 0.0417), re-anchoring its tail level (0.0263), or smoothing its switch thresholds (0.0247, a near-tie) — and every one lost to the untouched baseline, so that family is exhausted. The fit-replacement failures teach that the Tobit lognormal is load-bearing on the three well-specified lognormal regimes, and any global change to it costs more there than it gains on mix_bimodal/mix_heavy/tail_pareto; the smoothstep near-tie says threshold-crossing variance is not where the error lives. The remaining error is systematic tail misspecification in the mixture/pareto regimes, so the next moves must be one-sided or diagnostic — interventions that fire only when the lognormal is provably off and are exact no-ops when it is fine.

(b) Ranked next directions (each a single edit to estimators.py):

1. Bound-respecting clamps from exact stochastic-dominance facts. Clamped data (cap substituted for censored rows) is pointwise <= truth, so its empirical quantiles are valid lower bounds always: take median = max(parametric_median, empirical_clamped_median) when cen_frac >= 0.5, q90 = max(parametric_q90, empirical_clamped_q90) when cen_frac >= 0.10 (note the clamped q90 equals cap there), and for c > cap take p_ge = min(lognormal_sf, cen_frac) plus enforcing p_ge nonincreasing in c. Unlike 2107/2's full anchoring (which rescaled the tail everywhere and hurt the well-specified regimes), these clamps activate only on bound violations — zero cost when the fit is already sane, pure gain when the misspecified fit undershoots the tail.

2. Peaks-over-threshold tail for c > cap only. Leave median/q90 and the fit alone; replace _lognormal_sf beyond the cap with a Hill/Pareto extrapolation: pick a threshold u at, say, the 75th percentile of uncensored observations below cap, estimate the tail index from log-exceedances of uncensored points in (u, cap), and set p_ge(c) = p_ge_empirical(u) * (c/u)^(-alpha_hat), falling back to the lognormal sf when too few exceedances exist. Directly targets tail_pareto and mix_heavy, where a lognormal tail decays with the wrong shape, without touching any identified quantity.

3. Use the identified region as a validation set for the tail branch. Before trusting any parametric output, compare the fitted lognormal's p_ge at the identified caps (c <= cap, where truth-level empirical values are exact) against those empirical values; if the mean absolute gap exceeds a small tolerance (say 0.03), declare the fit misspecified for this sample and swap only the unidentified outputs to bound-based defaults (q90 = cap when 0.10 <= cen_frac, p_ge(c>cap) = cen_frac scaled by the empirical exceedance decay between the two largest identified caps). This is per-sample model checking, which no prior attempt tried — the fit itself is never altered.

(c) Do NOT retry: any further modification of the lognormal fitting procedure or its global tail level (mixture EM, quantile-matched fits, cen_frac re-anchoring, threshold smoothing) - four straight reverts closed that family.

## 20260828-2119/3 HYPOTHESIS: Apply the reviewer's ranked-option-1 bound-respecting clamps unchanged - when the parametric branch is used for median (cen_frac >= 0.5) or q90 (cen_frac >= 0.10), take the max with the corresponding empirical clamped-data quantile (a valid lower bound), and for c > cap clamp p_ge to be no larger than cen_frac and enforce it is nonincreasing in c - since these are one-sided corrections that only fire on provable bound violations and are exact no-ops otherwise, unlike the four prior attempts that all globally altered the fit or its tail level.

RESULT 20260828-2119/3: 0.024492  reverted (best 0.024558)

