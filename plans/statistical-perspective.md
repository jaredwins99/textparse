# Statistical Perspective

A living document capturing the project owner's statistical intuition and philosophy. Claude should internalize these framings when building educational content. This is not a textbook summary — it's how to *think about* the statistics.

**Updated as the user provides new insights. Always append, then consolidate.**

---

## Core Philosophy

- Statistics is about **what you gain and what you lose** — every method is a tradeoff
- Intuition comes from **seeing the geometry**, not from reading the formula
- The formula is a compact encoding of the idea — it's the *last* thing you show, not the first
- When a classical assumption breaks, the method doesn't just "fail" — it degrades in specific, characterizable ways. Understanding the degradation is more useful than memorizing the assumption.

## OLS / Linear Regression

- OLS always estimates the **Best Linear Projection (BLP)** — even when the true CEF is nonlinear
- The BLP is a weighted average of local slopes, weighted by the covariate distribution
- As nonlinearity grows, the BLP becomes sensitive to the **support range** of X — shift where you observe data and β̂ estimates a different quantity
- "Biased" is the wrong framing. "Estimating a different target" is correct.
- Key refs: White (1980), Angrist & Pischke (2009) Thm 3.1.4-3.1.5, Buja et al. (2019)

## Ridge Regression

- The right entry point is **"what does ridge buy you?"** — it trades bias for substantially lower variance by shrinking coefficients
- The 3D loss landscape is the most intuitive visualization: you can *see* the penalty reshaping the surface
- The Bayesian interpretation (Gaussian prior → posterior mode) is the same geometric story told differently — prior + likelihood = reshaped landscape
- ESL's constraint geometry (diamond vs circle) is a more abstract way to see the same thing
- Effective degrees of freedom is the most abstract — only meaningful after you understand what λ does
- Direct ESL quotes are better than paraphrasing for benefits/tradeoffs

## Assumption Degradation (General Pattern)

- Don't present assumptions as binary (holds/fails). Model them as a **spectrum of degradation**.
- At each level, characterize: what still works, what breaks, what's the fix
- Cross-effects matter: heavy tails + small n is worse than either alone
- Every claim about degradation must be citable

---

*Sections below will be filled as the user reviews Chapter 3 concepts:*

## Lasso / Sparsity

*(awaiting user review)*

## Subset Selection

*(awaiting user review)*

## PCR / PLS

*(awaiting user review)*

## Bias-Variance Tradeoff

*(awaiting user review)*

## Orthogonal Projections / Hat Matrix

*(awaiting user review)*
