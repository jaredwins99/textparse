# Statistical Perspective

A living document capturing the project owner's statistical intuition and philosophy. Claude should internalize these framings when building educational content. This is not a textbook summary — it's how to *think about* the statistics.

**Updated as the user provides new insights. Always append, then consolidate.**

---

## Core Philosophy

- Statistics is about **what you gain and what you lose** — every method is a tradeoff
- Intuition comes from **seeing the geometry**, not from reading the formula
- The formula is a compact encoding of the idea — it's the *last* thing you show, not the first
- When a classical assumption breaks, the method doesn't just "fail" — it degrades in specific, characterizable ways. Understanding the degradation is more useful than memorizing the assumption.
- **Show synonyms.** Many concepts have multiple names across fields — always surface these connections (e.g., collinearity / perfect correlation / singular moment matrix / rank deficiency)

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
- **Two parameterizations** — size constraint AND penalty. Both should be shown.
- Size constraint helps with large positive and large negative coefficients cancelling each other (unstable scenarios)
- **Not equivariant under scaling** — but ESL doesn't explain this for OLS either! Need to address both.
- Ridge can be framed both as a **different model** and as a **different objective function** — it is NOT an optimization procedure. This distinction matters.
- Add point about centering / intercept treatment
- Main practical motivation: making XᵀX non-singular — ridge as a solution to singularity
- The reference to equality of prior distributions (ESL) is abstruse — needs to be made concrete
- Explain effective df, explain d (eigenvalues) and how it affects which dimensions are shrunk most
- Can visualize the eigenvalue/shrinkage connection and match it to the "suction" intuition
- Page 67 of ESL is confusing — needs better explanation

## Assumption Degradation (General Pattern)

- Don't present assumptions as binary (holds/fails). Model them as a **spectrum of degradation**.
- At each level, characterize: what still works, what breaks, what's the fix
- Cross-effects matter: heavy tails + small n is worse than either alone
- Every claim about degradation must be citable

---

## Chapter 3 Walkthrough — User's Detailed Review

### General Critiques (patterns across the chapter)

- **Cart before horse**: ESL repeatedly introduces the "why" before the "what" — e.g., prediction accuracy before explaining what we're predicting, CV before explaining what we're selecting
- **Formulas before intuition**: The book starts with formulas. Our pages must not.
- **Missing plain English**: Many concepts are shown mathematically but never stated in plain English
- **Synonyms not surfaced**: Full rank / collinearity / perfectly correlated / singular moment matrix are the same idea from different angles — students need to see these connections
- **Missing applied examples**: Collinearity should have a concrete example of redundant information, not just math

### 3.1–3.2: Linear Models, Least Squares, Design Matrix

**Covariate transformations**
- "Linear in the parameters" — the key insight is that X can include nonlinear transformations of raw features

**Least squares**
- Independent draws → conditionally independent Y
- The viz is "missing the squared essence" — need to show what squaring does
- "Average lack of fit" as the plain-English framing
- Validity section doesn't say enough

**Design matrix**
- Needs an actual table visualization, not just math
- **Linear algebra equivalence** should be explicit: the regression problem IS a projection problem

**Projection matrix / orthogonality condition**
- Current viz doesn't give intuition for what the projection matrix actually does
- Perfect for an animation (manim), not an interactive

**Full rank / collinearity**
- Surface all synonyms: full rank, collinearity, perfectly correlated, singular moment matrix
- Give an applied example of redundant information (not just abstract)
- The book brings up images as an example — worth keeping

### 3.2.1–3.2.3: Inference, Hypothesis Tests

**Standard errors**
- Assumptions: uncorrelated errors, constant variance, fixed X
- The current page gives the formula — wrong instinct, explain what SE means first

**Unbiasedness**
- Needs a counterexample — what does bias look like?

**Sampling distribution / population assumptions**
- Mean is linear, additive noise, normally distributed
- Gives MVN distribution, distribution of sample variance (chi-squared)
- Chi-squared is independent from coefficient estimates — this is not obvious and needs emphasis

**Hypothesis tests: z-scores, t-tests, F-tests**
- Z-score page should just be folded into hypothesis testing, not standalone
- t-distribution: **no mention of blend over Cauchy and Normal** — this is the key intuition for the t-distribution
- As sample increases, t → normal (they become the same)
- F-distribution under normal assumption — **lacks intuition for what the distribution represents**
- F generalizes the t-statistic (F = t² for single coefficient)
- As sample increases, F → chi-squared
- Confidence interval formula is way more complicated than needed — the ±2 SE approximation is good and already included
- "Gaussian error does not hold" is ambiguous — all other assumptions need to hold, and it's by CLT not magic
- Confidence set seemed like a useful property but probably no intuition for most students — needs viz

**Log scaling**
- Doesn't explain *why* in terms of measurement, heteroskedasticity, Poisson-flavored data etc.
- Overall jumps ahead with concepts in the example

**Example section problems**
- Talks of removing non-significant terms but doesn't mention implications (base error rate, multiple testing)

### 3.2.2: Gauss-Markov Theorem

- Students should internalize: the projection matrix encodes everything about OLS
- In the proof, MSE is minimized
- Expected prediction error relates to true error by only the variance of the new observation
- ESL puts "cart before horse" — tries to motivate before stating the result
- Failed attempt at motivating examples

### 3.2.3: Multiple Regression, Successive Orthogonalization

**Successive orthogonalization (Gram-Schmidt)**
- Doesn't signpost what's coming
- **Perfect for an animation** — show the orthogonalization step by step
- Show that correlated features lead to unstable estimates
- Implication: **randomization means orthogonal** design
- Leads to reinterpreting standard errors through orthogonalization lens

**QR decomposition**
- Is directly related to Gram-Schmidt — this connection wasn't emphasized enough
- Should be presented as "the computational version of what Gram-Schmidt does conceptually"

### 3.2.4: Multiple Outputs

- Key insight: outputs **don't affect each other** — state this first, THEN explain why
- Only correlation between observations (not between Y columns) affects the decoupling
- Current framing explains the "why" before the "what" — flip it

### 3.3: Subset Selection and Shrinkage

**Best subset selection**
- The pictures are shown and we say "use prediction error" but it's never explained in plain English why you can't just minimize RSS
- Bringing up CV at this point is cart before horse
- ESL literally brings up dropping non-significant terms in the example section but ALSO does it here — inconsistent
- "Not accounting for the search process" is the general form of the multiple testing concern above

**Stepwise selection**
- Compare to best subset: lower variance, higher bias
- Backward needs N > p — important practical constraint
- Remember to deal with groups of variables appropriately

**Forward stagewise**
- Show comparison to stepwise — how does the path differ?

### 3.4: Shrinkage Methods

**Cross-validation / estimated prediction error**
- One standard error rule should be highlighted
- Regularization: showing how it makes selection continuous (vs. discrete subset) by comparing CV error curves is great

**Ridge regression** — see dedicated section above, plus:
- SVD: explaining SVD at the same time as applying it is not the best — separate the concept from the application
- Explain effective df plot properly
- "aka shrinkage" — surface this synonym
- Ridge df, explain d (eigenvalues) and how it affects which dimensions are affected most

**Lasso**
- Basis pursuit connection
- Soft thresholding (remove as standalone page — fold into lasso)
- **Animation**: expanding contours over and over for both lasso and ridge — this is the key comparative visualization
- Generalized ridge regression connection
- Mode of posteriors; ridge is also the mean (not just mode)

**Elastic net**
- Shrinks correlated variables — this is the key distinguishing property

**Least angle regression (LAR)**
- Entire solution path — needs an animation showing the path being traced
- LAR-Lasso connection

### 3.5: Derived Input Methods

**Principal components regression**
- Dimension reduction before regression

**Partial least squares**
- Supervised dimension reduction

**Parameter space paths** (page 83 of ESL)
- "Really just needs the two images and nothing else" — the solution path comparison images are great
- Should add little arrows showing the direction of parameterization (the lines are parametrizations)

### 3.8–3.9: More Shrinkage and Paths

**Canonical correlation analysis, Reduced rank regression**
- Keep but lower priority

**Incremental forward stepwise, Modified LAR**
- Keep

**Piecewise linear path algorithms**
- Important algorithmic insight

**Dantzig selector, Grouped lasso, Lasso guarantees**
- Keep, lower priority

**Pathwise coordinate descent**
- Computational workhorse — important

**Cholesky**
- Add as a concept (computational building block)

### Concepts to REMOVE or RENAME

| Action | Current | New |
|--------|---------|-----|
| REMOVE | Soft Thresholding (standalone) | Fold into Lasso |
| REMOVE | Soft Thresholding Operator | Fold into Lasso |
| REMOVE | Z-Score Regression | Fold into Hypothesis Testing |
| RENAME | F-Statistic-Nested | F Statistic |
| RENAME | Multicollinearity | Collinearity |
| MERGE | Infinitesimal Forward Stagewise (2 entries) | Single entry |

### Node Importance Tiers (for canvas sizing)

**Tier 1 (largest):** Ridge Regression, Lasso, Collinearity, Bias-Variance Tradeoff, Least Squares, Gauss-Markov Theorem, Cross-Validation/Model Selection
**Tier 2:** Best Subset Selection, Forward/Backward Stepwise, PCR, PLS, Elastic Net, SVD, Orthogonal Projection
**Tier 3:** QR Decomposition, Gram-Schmidt, LAR, Forward Stagewise, Degrees of Freedom, MSE Decomposition, AIC, Canonical Correlation
**Tier 4 (smallest):** SCAD Penalty, Curds and Whey, Dantzig Selector, Grouped Lasso, Relaxed Lasso, Adaptive Lasso, L2Boost, Homotopy Algorithm, Basis Pursuit, L1 Arc Length
