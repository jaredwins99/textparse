# Lessons, Standards, and Decisions

Consolidated from user critiques and session learnings. **This is a living reference** — update it as new patterns emerge. Future Claude sessions: read this before touching visualizations, games, or citations.

---

## 1. Citation Standards

### Never trust latent knowledge
Claude's training data contains citations that are plausible but wrong — wrong journal names, wrong years, papers that don't exist. **Every citation must be verified.**

**Workflow:**
1. Write the content with citations from memory
2. Web-search each citation to verify: author names, year, journal/publisher, volume/pages
3. Flag any that can't be confirmed online — ask the user to upload the PDF
4. If a PDF is available in Zotero (via MCP), use `zotero_search_items` / `zotero_item_fulltext` to verify claims against the actual text

**Common failure modes:**
- Correct author + wrong journal (e.g., Samorodnitsky in "J. Time Series Analysis" → actually "Probability and Mathematical Statistics")
- Plausible but nonexistent papers (e.g., "Wilcox & Rousselet (2021) Frontiers in Psychology" doesn't exist — real paper is "Rousselet, Pernet & Wilcox (2021) Adv. Methods Pract. Psych. Sci.")
- Overstating what a paper proves (e.g., attributing the CLT to "Lévy (1922)" when the relevant result is Lindeberg (1922))

### Citation display format
- **Superscript footnote numbers** in the content: `<sup class="cite-num">3</sup>`
- **Numbered reference list** at the bottom, organized by section/header
- Do NOT inline full citation text in tier boxes — it clutters the UI
- CSS: `.cite-num { display: inline; font-size: 0.58rem; font-weight: 700; color: var(--blue); vertical-align: super; margin-left: 2px; }`

---

## 2. Statistical Accuracy — Key Corrections

### OLS under misspecification (linearity broken)
**Wrong framing:** "OLS is biased when linearity fails."
**Correct framing:** OLS always estimates the **Best Linear Projection (BLP)** — the MSE-optimal linear approximation to E[Y|X]. Even under misspecification:
- β̂ converges to β* = argmin E[(Y - X'β)²]
- This is a **weighted average of local slopes**, weighted by the covariate distribution
- As nonlinearity grows, the BLP becomes increasingly **sensitive to the support range** of X
- The BLP is a **functional of the covariate distribution**, not a fixed parameter — shift where you observe X and β̂ estimates a different quantity

**Key citations:**
- White (1980) "A Heteroskedasticity-Consistent Covariance Matrix Estimator" — Econometrica 48(4)
- Angrist & Pischke (2009) *Mostly Harmless Econometrics* — Theorem 3.1.4 (linear CEF), Theorem 3.1.5 (BLP)
- Buja, Brown, Berk, George, Pitkin, Traskin, Zhang & Zhao (2019) "Models as Approximations" — Statistical Science 34(4) — the definitive treatment of BLP sensitivity to covariate support

### Infinite variance errors
**Wrong:** "OLS consistency is questionable under infinite variance."
**Correct:** OLS is still consistent but converges at a slower rate: n^(1/α − 1) instead of √n for α-stable errors with index α < 2.

### VIF thresholds
VIF > 5 or > 10 rules are **rules of thumb**, not theorems. Always mark with a disclaimer. Cite O'Brien (2007) "A Caution Regarding Rules of Thumb for VIF."

---

## 3. Plotly.js 3D Visualization — Hard-Won Rules

These were discovered through 5+ failed attempts. Do NOT deviate.

### Camera preservation (the #1 problem)
**Any write to `scene.*` resets the 3D camera.** This includes:
- `Plotly.react()` — rebuilds the entire plot, resets camera
- `Plotly.relayout()` with any scene property — resets camera
- `Plotly.update()` with layout containing scene — resets camera

**The ONLY working pattern:**
1. Call `Plotly.newPlot()` **once** at initialization
2. Set ALL axes with `autorange: false` and explicit `range` at init time
3. For slider/toggle updates, use **ONLY** `Plotly.restyle()` to swap data
4. **Never** call `Plotly.relayout()`, `Plotly.react()`, or `Plotly.update()` with layout changes after init

```javascript
// INIT (once)
Plotly.newPlot('div', [trace], {
  scene: {
    xaxis: { range: [xMin, xMax], autorange: false },
    yaxis: { range: [yMin, yMax], autorange: false },
    zaxis: { range: [zMin, zMax], autorange: false },
    aspectmode: 'cube',
    camera: { eye: { x: 1.5, y: 1.5, z: 1.1 } }
  }
});

// UPDATE (on slider change) — restyle ONLY
Plotly.restyle('div', { z: [newZData] }, [0]);
```

### Axis range precomputation
Since you can't change axis ranges after init without resetting the camera, you must **precompute the max range across all possible slider positions** and set it at init. The axes stay fixed; the data changes within them.

### Aspect ratio locking
Default `aspectmode: 'auto'` rescales the 3D bounding box based on data ranges. This makes the background "move and grow" when data changes. **Always use `aspectmode: 'cube'`** to lock the box shape.

### Multiple 3D plots
When showing related surfaces (e.g., likelihood + prior + posterior), each gets its own `Plotly.newPlot` and its own `Plotly.restyle`. They share the same axis range constants so they look consistent.

---

## 4. Assumption Explorer Game Format

### Structure
- **Health bars** at top: 5 properties that degrade as assumptions break (regression: Unbiased, BLUE, Valid t/F, Consistent, Prediction; CLT: Normal Limit, Convergence Rate, Variance Estimation, CI Coverage, Test Validity)
- **Individual paths**: One per assumption, each with 5 tiers (0=perfect → 4=catastrophic)
- **Themed paths**: Cross-cutting combinations (2-3 themed paths per game)
- **Diagnostic panel**: Shows Survives/Broken/Fixes based on current selections
- **Citation footer**: Numbered references organized by path header

### Path ordering (regression)
Linearity → Independence → Error Distribution → Homoscedasticity → Collinearity

### Tier design
Each tier has:
- `name`: Short label
- `desc`: 1-2 sentences explaining what happens at this severity level
- `effects`: Object mapping health bar IDs to percentage values (100 = no damage)
- `cite`: Integer footnote number
- Every claim must be citable — no hand-waving

### Cross-effects
Themed paths should model **interaction effects** — combinations that are worse than the sum of parts:
- Heavy tails + small n → convergence collapse
- Dependence + non-identical distributions → CLT fails entirely
- Strong dependence + infinite variance → fatal

### Dark theme CSS variables
```css
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #1c2129;
  --border: #30363d;
  --text: #e6edf3;
  --text-dim: #8b949e;
  --green: #3fb950;
  --yellow: #d29922;
  --orange: #db6d28;
  --red: #f85149;
  --blue: #58a6ff;
  --purple: #bc8cff;
}
```

---

## 5. How to Teach a Concept — Pedagogy Rules

These are the most important lessons. They govern how every concept visualization should be structured.

### Lead with intuition, not formulas
The default instinct is to start with the formula — `β̂ = (XᵀX + λI)⁻¹Xᵀy` — and then explain it. **This is backwards.** The user explicitly rejected this. Formulas are reference material, not teaching tools. They belong at the **end**, after the reader already understands what's happening and why.

**Correct ordering for any concept page:**
1. **Benefits & Tradeoffs** — what does this method buy you? What do you give up? Use the textbook's own language (direct quotes with citations). This is what a reader actually cares about first.
2. **Interactive visualizations** — ordered from most concrete/intuitive to most abstract. The reader should *see* the concept before formalizing it.
3. **Statistical guarantees** — formal properties, theorems, conditions
4. **Formulas** — dead last, as reference

### Visualization ordering: concrete → abstract
Don't order visualizations by what's easiest to code or what follows the textbook's section order. Order them by **what builds intuition fastest.**

Ridge regression example (final ordering after user critique):
1. **Coefficient Shrinkage (2D)** — most concrete. You see β̂ values move toward zero as λ increases. Immediate intuition: "λ shrinks things."
2. **3D Loss Landscape** — now you see *why* shrinkage happens: the penalty reshapes the loss surface, moving the minimum.
3. **Bayesian Prior Interpretation** — the prior is just another way to see the same surface reshaping. Likelihood + Prior side by side so you can compare, Posterior below.
4. **Constraint Geometry (ESL Fig 3.11)** — the classic diamond/circle diagram. More abstract but connects to the textbook's visual language.
5. **Effective Degrees of Freedom** — the most abstract: a single curve showing df(λ). Only meaningful after you already understand what λ does.

### Don't follow trends — build the thing that explains it
The instinct is to make trendy-looking dashboards with fancy 2D charts because that's what most educational content looks like. But if a 3D rotatable loss surface is what actually makes the concept click, build that. The user specifically pushed for the 3D loss landscape approach because it was genuinely more intuitive than the abstract alternatives. Don't shy away from interactive 3D if it earns its complexity.

### Animation vs Interactive vs Static — concept classification tree

**Don't default to "interactive" for everything.** The format should match the nature of the concept. Think about what the concept IS in plain English, not in math. Forget what precedent exists for how these things are usually visualized — most educational content defaults to interactives because they're trendy, not because they teach better.

**Decision tree:**

**1. Is the concept a PROCESS or TRANSFORMATION?** → **Animation (manim)**
- The concept is something *happening* — a verb, not a noun
- The insight comes from watching it unfold in sequence
- Examples:
  - **Orthogonal projection** — "projection" in English means casting a shadow. A shadow falls. You watch y drop onto the column space. Animation.
  - **Gram-Schmidt orthogonalization** — a step-by-step process of making vectors perpendicular. Each step is sequential. Animation.
  - **Forward stagewise regression** — coefficients creep incrementally. The path IS the concept. Animation.
  - **LAR tracing the solution path** — you watch the path being drawn. Animation.
  - **Successive orthogonalization** — peeling off projections one by one. Animation.

**2. Does the concept have a PARAMETER the student needs to explore?** → **Interactive (Plotly/sliders)**
- There's a knob (λ, k, threshold) and the insight is in the *relationship* between that knob and the result
- The student needs to ask "what if?" and see the answer immediately
- Examples:
  - **Ridge regression** — drag λ, see coefficients shrink, see the loss surface reshape. Interactive.
  - **Lasso vs Ridge contour comparison** — expand contours over and over for both. Interactive with slider or animation with both running simultaneously.
  - **Bias-variance tradeoff** — move model complexity, see bias go down and variance go up. Interactive.
  - **Effective degrees of freedom** — slide λ, see df change. Interactive.

**3. Is the concept a COMPARISON or STRUCTURAL RELATIONSHIP?** → **Side-by-side static or annotated diagram**
- The insight is in seeing two things next to each other
- Examples:
  - **Solution path comparison** (ESL page 83) — just the two images with arrows showing direction of parameterization. Static.
  - **Diamond vs circle constraint geometry** — ESL Fig 3.11. Could be static annotated diagram or very simple interactive.
  - **Forward vs backward stepwise** — comparison table or side-by-side path traces.

**4. Is the concept a DEFINITION or PROPERTY?** → **Annotated example or no viz at all**
- Some concepts are best explained with words, a concrete example, and maybe a table
- Don't force a visualization where a clear sentence does the job better
- Examples:
  - **Design matrix** — show an actual data table becoming the X matrix
  - **Collinearity** — show a concrete example of redundant features
  - **Gauss-Markov theorem** — the proof structure matters more than a picture

**The key principle:** Ask "what is this concept in ENGLISH, to a human?" not "what does the math notation look like?" Projection = shadow falling. Shrinkage = squeezing. Orthogonalization = straightening. Path = tracing a route. The English word tells you the format.

### Benefits/tradeoffs are NOT optional
Every concept page must lead with a Benefits & Tradeoffs card. This is the answer to "why should I care about this method?" Format:
- **Benefits** (green dots): What this method gives you, with ESL quotes
- **Tradeoffs** (red dots): What you sacrifice, with ESL quotes
- **Book quote** at the bottom: The textbook's own summary sentence

### Use the textbook's terminology
If ESL says "shrinkage," don't unilaterally rename it "regularization" without noting both. If ESL says "effective degrees of freedom," use that phrase. The visualizations are companions to the textbook, not replacements.

### Direct quotes > paraphrasing
When the textbook makes a claim clearly, quote it directly with `(ESL §3.4.1)` citation. Don't paraphrase into your own words when the original is better. The user values seeing the book's actual language alongside the visualization.

### Visualization-specific layout decisions (ridge)
- **Viz 2 (3D Loss Landscape)**: Always shows penalized loss (RSS + λ penalty). No RSS-only toggle — it was removed because it wasn't useful.
- **Viz 3 (Prior Reshapes Landscape)**: Likelihood and Prior are **side by side** (2-column grid). Posterior is **below, centered** (max-width 600px). Not a 3-column triptych — user needs to see likelihood and prior simultaneously for comparison.

### General viz tech
- Use Plotly for 3D interactive surfaces
- Use MathJax for LaTeX rendering
- Same dark theme as assumption games
- Sliders should update smoothly without camera/axis resets

---

## 6. Process Lessons

### Pressure-test everything
When generating educational content with claims about statistical properties:
1. Write the content
2. Search for papers supporting each claim
3. Verify citations exist and say what you think they say
4. Ask the user which PDFs to upload for deep verification
5. Don't ship claims without citations

### The user's standard
- Format and interactivity can be great, but **accuracy is non-negotiable**
- A beautiful game with wrong statistical claims is worse than nothing
- Citations aren't decoration — they're the user's way of auditing correctness
- When in doubt, be conservative about what a statistical result guarantees

### Iteration pattern
The user gives rapid feedback. Expect:
1. Initial implementation
2. Multiple rounds of "nope, still broken" / "that's not quite right"
3. Deep critique of statistical claims
4. Format/layout preferences stated concisely
5. Requests may arrive mid-implementation (e.g., "also flip the ordering") — handle both in parallel

### Don't re-litigate
Once a decision is made (path ordering, BLP framing, citation format), don't second-guess it in future sessions. Reference this document.
