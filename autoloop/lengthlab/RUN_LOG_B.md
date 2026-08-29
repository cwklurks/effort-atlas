# lengthlab loop B run log

## 20260829-0319/1 HYPOTHESIS: For a fixed total-response budget (n_items x n_reps), the paired DiD test's variance decomposes into a between-item heterogeneity term that only shrinks with n_items and a within-item replicate-noise term that shrinks with n_items x n_reps together, so replicate depth beyond n_reps=1 does not reduce the dominant (between-item) variance component while it does consume budget that could instead buy more items - reallocate the baseline's 130 items x 2 reps (cost $35.05 of $40) to n_reps=1 and a proportionally larger n_items (280) to spend the same budget more effectively against the binding between-item variance term.
RESULT 20260829-0319/1: 0.080000  reverted (best 0.075000)

## 20260829-0319/2 HYPOTHESIS: The scorer's power scenarios always widen the allowance at high effort (a_big > a_sm) so the true diff-in-diff sign is known a priori to be positive (high effort is censored more at the small allowance), while the null scenarios keep the DiD symmetric around 0 by construction, so switching analyze() from a two-sided to a one-sided (DiD > 0) test should roughly double detection power on every power scenario without inflating type-I on the null scenarios.

RESULT 20260829-0319/2: 0.122500  KEPT (new best)

## 20260829-0319/3 HYPOTHESIS: Each item's true per-cell accuracy is P_answer(effort,allowance) * sigmoid(BASE - d_i + b_effort), so both the true DiD and the item's overall mean accuracy across the four cells are smooth decreasing functions of the same latent d_i (while their pure measurement-noise covariance is exactly zero by construction, since did=a-b-c+d and x=(a+b+c+d)/4 give zero cross-term for independent-noise cells), so an ANCOVA-style regression adjustment of the per-item DiD on that within-item mean-accuracy covariate (CUPED-like, with the correct n-2 residual degrees of freedom preserving the one-sided test's validity) should remove genuine between-item heterogeneity and increase power without inflating type-I.

RESULT 20260829-0319/3: 0.122500  reverted (best 0.122500)

## 20260829-0319/4 HYPOTHESIS: The baseline design (130 items x 2 reps) only spends about $35.05 of the $40.00 budget, leaving roughly 12% of spend unused, so raising n_items to 145 (keeping n_reps=2, the ratio that already pairs well with the one-sided test) spends the idle budget headroom (projected mean cost ~$39.07, safely under $40) to shrink the paired t-test's standard error by ~1/sqrt(145/130) and increase worst-case power with no downside, since it changes total N rather than the items:reps ratio already probed by hypothesis 1.

RESULT 20260829-0319/4: 0.137500  KEPT (new best)

## 20260829-0319/5 HYPOTHESIS: Because each per-cell accuracy is a mean of only n_reps=2 Bernoulli draws, its sampling variance p(1-p)/n_reps is strongly heteroscedastic in p (largest near p=0.5, smallest near the extremes), which inflates and unevenly weights the per-item DiD's estimated variance across items and cells; applying the classical arcsine square-root variance-stabilizing transform y=2*arcsin(sqrt(acc)) to each of the four cells before forming the DiD preserves E[DiD]=0 exactly under every null scenario (matched cells remain iid draws from the same distribution under a_sm==a_big regardless of the monotone transform applied to each), so it should homogenize per-item variance and increase the one-sided paired t-test's power without inflating type-I.

RESULT 20260829-0319/5: 0.137500  reverted (best 0.137500)


## 20260829-0319/6 HYPOTHESIS: Because the scorer's expected spend is exactly proportional to the product n_items*n_reps (each of the 4 cells' per-draw token cost is independent of how many reps/items it is split across), reallocating the current best's 145 items x 2 reps (290 item-reps, ~$39.07) to 290 items x 1 rep holds expected cost essentially fixed while, under the standard between-item-heterogeneity/within-item-noise variance decomposition Var(DiD-mean) = between/n_items + within/(n_items*n_reps), substituting items=Budget/(u*reps) shows total variance is strictly increasing in n_reps for any positive between-item variance - so cutting reps to the minimum (1) and doubling items is variance-optimal at fixed budget; the previous n_reps=1 test (hypothesis 1) only showed a marginal gain because it was measured under the since-replaced two-sided test, so retesting the same item/rep ratio now that the one-sided test (hypothesis 2) and larger item budget (hypothesis 4) are both in place should reveal the full benefit.
RESULT 20260829-0319/6: 0.125000  reverted (best 0.137500)

