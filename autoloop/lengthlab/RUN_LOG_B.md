# lengthlab loop B run log

## 20260829-0319/1 HYPOTHESIS: For a fixed total-response budget (n_items x n_reps), the paired DiD test's variance decomposes into a between-item heterogeneity term that only shrinks with n_items and a within-item replicate-noise term that shrinks with n_items x n_reps together, so replicate depth beyond n_reps=1 does not reduce the dominant (between-item) variance component while it does consume budget that could instead buy more items - reallocate the baseline's 130 items x 2 reps (cost $35.05 of $40) to n_reps=1 and a proportionally larger n_items (280) to spend the same budget more effectively against the binding between-item variance term.
RESULT 20260829-0319/1: 0.080000  reverted (best 0.075000)

## 20260829-0319/2 HYPOTHESIS: The scorer's power scenarios always widen the allowance at high effort (a_big > a_sm) so the true diff-in-diff sign is known a priori to be positive (high effort is censored more at the small allowance), while the null scenarios keep the DiD symmetric around 0 by construction, so switching analyze() from a two-sided to a one-sided (DiD > 0) test should roughly double detection power on every power scenario without inflating type-I on the null scenarios.

RESULT 20260829-0319/2: 0.122500  KEPT (new best)

## 20260829-0319/3 HYPOTHESIS: Each item's true per-cell accuracy is P_answer(effort,allowance) * sigmoid(BASE - d_i + b_effort), so both the true DiD and the item's overall mean accuracy across the four cells are smooth decreasing functions of the same latent d_i (while their pure measurement-noise covariance is exactly zero by construction, since did=a-b-c+d and x=(a+b+c+d)/4 give zero cross-term for independent-noise cells), so an ANCOVA-style regression adjustment of the per-item DiD on that within-item mean-accuracy covariate (CUPED-like, with the correct n-2 residual degrees of freedom preserving the one-sided test's validity) should remove genuine between-item heterogeneity and increase power without inflating type-I.

RESULT 20260829-0319/3: 0.122500  reverted (best 0.122500)

