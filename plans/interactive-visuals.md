# Interactive Visuals Plan

**Status**: Draft
**Last updated**: 2026-02-16
**Covers**: 670 ESL concepts, each getting an interactive Plotly.js or Three.js visualization

---

## 1. Core Insight: Template-Based Generation

670 concepts cannot be hand-crafted. The strategy is:

1. Define ~35 parameterized visualization templates
2. Map every concept to a template + parameter set
3. Generate the mapping via LLM agents in batches (similar to concept extraction)
4. A thin runtime loads the template and injects parameters when a concept is selected

This gives us: **35 template files** + **1 mapping file** (670 entries) + **1 runtime loader**.

---

## 2. Template Catalog

### Group A: Function Plots (Plotly.js) — covers ~180 concepts

**Template A1: Single Function Plot (2D)**
- What: Plot y = f(x) with interactive sliders for parameters
- Concepts: loss functions, activation functions, basis functions, penalty functions, link functions, kernel functions
- Parameters: `{function: "1/(1+exp(-x))", xRange: [-5,5], sliders: [{name: "steepness", param: "a", range: [0.1,5], default: 1}], xlabel: "x", ylabel: "sigma(x)"}`
- Example concepts: sigmoid activation, logistic loss, hinge loss, huber loss, soft thresholding, hard thresholding, RBF kernel, polynomial kernel, gaussian density, probit link

**Template A2: Function Comparison (2D)**
- What: Multiple functions on the same axes, toggle-able
- Concepts: comparing loss functions, comparing kernels, comparing penalties
- Parameters: `{functions: [{name: "L1", expr: "abs(x)"}, {name: "L2", expr: "x*x"}], xRange: [-3,3]}`
- Example concepts: L1 vs L2 penalty, squared error vs absolute error, 0-1 loss vs surrogate losses

**Template A3: 3D Surface (Plotly.js)**
- What: z = f(x, y) surface with rotation, zoom, optional contour
- Concepts: error surfaces, bias-variance tradeoff, regularization landscapes, multivariate gaussians
- Parameters: `{function: "(x-1)^2 + (y+0.5)^2 + 0.5*x*y", xRange: [-3,3], yRange: [-3,3], xlabel: "beta_1", ylabel: "beta_2", zlabel: "RSS"}`
- Example concepts: RSS surface, regularization path, bias-variance tradeoff surface, multivariate normal density

**Template A4: Regularization Path (2D)**
- What: Coefficient paths as a function of lambda (or log-lambda)
- Concepts: ridge paths, lasso paths, elastic net paths
- Parameters: `{method: "lasso", nCoefficients: 8, lambdaRange: [0.01, 100]}`
- Example concepts: lasso, ridge regression, elastic net, grouped lasso, relaxed lasso, dantzig selector, basis pursuit

### Group B: Scatter + Fit (Plotly.js) — covers ~120 concepts

**Template B1: Scatter with Regression Fit**
- What: 2D scatter with overlaid fit line/curve, interactive noise/flexibility controls
- Concepts: linear regression, polynomial regression, local regression, splines, smoothing
- Parameters: `{trueFunction: "sin(x)", noise: 0.3, fitType: "polynomial", fitParam: 3, xRange: [0, 2*pi]}`
- Example concepts: least squares fitting, polynomial regression, natural cubic splines, smoothing splines, local linear regression, nadaraya-watson estimator, LOESS

**Template B2: Bias-Variance Decomposition (animated scatter)**
- What: Shows multiple fits from different samples, their average, and the true function
- Concepts: bias, variance, model complexity, overfitting, underfitting
- Parameters: `{trueFunction: "sin(x)", models: ["linear", "poly3", "poly10"], nSamples: 20}`
- Example concepts: bias-variance tradeoff, model complexity, expected prediction error, training error vs test error, overfitting

**Template B3: Residual Plot**
- What: Scatter of residuals with diagnostic overlays
- Concepts: residual analysis, heteroscedasticity, leverage
- Parameters: `{pattern: "heteroscedastic", nPoints: 100}`
- Example concepts: residual sum of squares, hat matrix, leverage points, influence, Cook's distance

### Group C: Decision Boundaries (Plotly.js/Three.js) — covers ~100 concepts

**Template C1: 2D Decision Boundary**
- What: Two-class scatter in 2D with shaded decision regions, adjustable parameters
- Concepts: all classifiers
- Parameters: `{method: "knn", methodParam: 5, dataPattern: "two-gaussians", nPoints: 200}`
- Example concepts: k-nearest neighbor classifier, Bayes classifier, linear discriminant analysis, quadratic discriminant analysis, logistic regression boundary, SVM boundary, decision tree boundary

**Template C2: Separating Hyperplane (Three.js)**
- What: 3D points with a plane/surface separating two classes, rotatable
- Concepts: SVMs in higher dimensions, optimal separating hyperplane
- Parameters: `{nDims: 3, margin: true, supportVectors: true, kernel: "linear"}`
- Example concepts: optimal separating hyperplane, support vectors, maximal margin classifier, kernel trick

**Template C3: Multi-class Boundaries**
- What: Multiple class regions with boundaries
- Concepts: multi-class methods
- Parameters: `{nClasses: 3, method: "lda"}`
- Example concepts: multi-class LDA, multinomial logistic regression, one-vs-all classification

### Group D: Dimension Reduction (Plotly.js) — covers ~60 concepts

**Template D1: PCA Projection**
- What: 3D point cloud with principal component axes shown, project onto 2D plane
- Concepts: PCA, SVD, projections
- Parameters: `{dataShape: "ellipsoid", nPoints: 200, showAxes: true, projectTo: 2}`
- Example concepts: principal components, singular value decomposition, projection pursuit, reduced-rank regression

**Template D2: Embedding Visualization**
- What: 2D embedding of high-dimensional data with interactive perplexity/parameter controls
- Concepts: manifold learning methods
- Parameters: `{method: "tsne", dataShape: "swiss-roll", perplexity: 30}`
- Example concepts: multidimensional scaling, local MDS, isometric feature mapping (isomap), locally linear embedding, t-SNE, self-organizing map, kernel PCA

**Template D3: Scree Plot / Variance Explained**
- What: Bar chart of eigenvalues or cumulative variance explained
- Concepts: dimension selection criteria
- Parameters: `{nComponents: 10, eigenvalues: [4.2, 2.1, 1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.02]}`
- Example concepts: scree plot, proportion of variance explained, Kaiser criterion

### Group E: Tree/Graph Structures (Plotly.js treemap + D3.js) — covers ~50 concepts

**Template E1: Decision Tree**
- What: Interactive tree with split conditions, leaf values, highlight paths
- Concepts: CART, pruning, tree methods
- Parameters: `{depth: 4, splitType: "axis-aligned", task: "classification"}`
- Example concepts: classification trees, regression trees, CART, pruning, cost-complexity pruning, PRIM

**Template E2: Dendrogram**
- What: Hierarchical clustering dendrogram with cut-height slider
- Concepts: hierarchical clustering methods
- Parameters: `{linkage: "complete", nLeaves: 20, cutHeight: 3}`
- Example concepts: hierarchical clustering, complete linkage, single linkage, Ward's method, agglomerative clustering

**Template E3: Graphical Model**
- What: Node-edge graph with conditional independence visualization
- Concepts: graphical models, Markov random fields
- Parameters: `{structure: "chain", nNodes: 6, directed: false}`
- Example concepts: undirected graphical model, Markov random fields, clique, graph Laplacian, hammersley-clifford theorem

### Group F: Algorithm Animation (Plotly.js with animation frames) — covers ~60 concepts

**Template F1: Iterative Optimization**
- What: Animated contour plot with a point moving along the optimization path
- Concepts: gradient descent, Newton's method, coordinate descent
- Parameters: `{surface: "(x-1)^2 + 5*(y-x^2)^2", algorithm: "gradient-descent", startPoint: [-1, 2], learningRate: 0.1}`
- Example concepts: gradient descent, stochastic gradient descent, Newton's method, coordinate descent, IRLS

**Template F2: Boosting Steps**
- What: Animated residual fitting — each frame adds a weak learner
- Concepts: boosting methods
- Parameters: `{nSteps: 10, baseLearner: "stump", trueFunction: "sin(x)"}`
- Example concepts: AdaBoost, gradient boosting, L2Boost, forward stagewise regression, incremental forward stagewise regression

**Template F3: EM Algorithm Steps**
- What: Animated Gaussian mixture fitting — E-step colors points, M-step moves centers
- Concepts: EM algorithm, mixture models
- Parameters: `{nComponents: 3, nPoints: 200, nSteps: 15}`
- Example concepts: EM algorithm, Gaussian mixture models, mixture modeling clustering, Gibbs sampler

**Template F4: K-Means Animation**
- What: Animated centroid assignment and update steps
- Concepts: K-means variants
- Parameters: `{k: 3, nPoints: 150, initMethod: "random"}`
- Example concepts: K-means clustering, k-medoids, vector quantization, codebook

### Group G: Matrix/Heatmap Visualizations (Plotly.js) — covers ~40 concepts

**Template G1: Matrix Heatmap**
- What: Color-coded matrix with hover values
- Concepts: covariance matrices, confusion matrices, correlation
- Parameters: `{matrix: "covariance", size: 8, symmetric: true}`
- Example concepts: covariance matrix, correlation matrix, confusion matrix, kernel matrix, adjacency matrix, graph Laplacian

**Template G2: Cross-Validation Grid**
- What: Heatmap of CV error across two hyperparameters
- Concepts: model selection methods
- Parameters: `{xParam: "lambda", yParam: "alpha", xRange: [0.01, 10], yRange: [0, 1]}`
- Example concepts: cross-validation, generalized cross-validation, AIC, BIC, leave-one-out CV

### Group H: Distribution / Statistical Concepts (Plotly.js) — covers ~40 concepts

**Template H1: Distribution with Annotations**
- What: PDF/CDF plot with interactive parameters, shaded regions for p-values, confidence intervals
- Concepts: statistical distributions, hypothesis testing
- Parameters: `{distribution: "normal", params: {mean: 0, sd: 1}, shade: {from: 1.96, to: Infinity}}`
- Example concepts: Gaussian distribution, t-distribution, chi-squared distribution, bootstrap distribution, Bayesian posterior

**Template H2: Sampling Distribution**
- What: Animated histogram building up from repeated samples
- Concepts: bootstrap, sampling variability
- Parameters: `{statistic: "mean", populationDist: "exponential", sampleSize: 30, nResamples: 500}`
- Example concepts: bootstrap, bagging, sampling distribution, standard error, confidence intervals

### Group I: Conceptual / Structural Diagrams (Three.js) — covers ~20 concepts

**Template I1: Network Architecture**
- What: Neural network layers with connection weights visualized
- Concepts: neural network architecture
- Parameters: `{layers: [4, 8, 8, 1], activation: "relu", showWeights: true}`
- Example concepts: single hidden layer neural network, deep learning, back-propagation, weight decay, dropout

**Template I2: Feature Space Mapping**
- What: Shows low-dim input, kernel/basis mapping, high-dim feature space
- Concepts: kernel methods, basis expansions
- Parameters: `{inputDim: 2, featureDim: 6, mappingType: "polynomial"}`
- Example concepts: kernel trick, feature extraction, reproducing kernel Hilbert space, basis function expansion

**Template count: 25 templates above. Remaining ~10 will be identified during batch mapping.**

---

## 3. Concept-to-Template Mapping Strategy

### The Mapping File

`output/visuals/concept-visuals.json`:

```json
{
  "concepts": [
    {
      "id": 1,
      "name": "supervised learning",
      "template": "B1",
      "params": {
        "trueFunction": "2*x + 1",
        "noise": 0.5,
        "fitType": "linear",
        "fitParam": 1,
        "xRange": [0, 5],
        "title": "Supervised Learning: Predicting Y from X",
        "annotation": "Given training pairs (x_i, y_i), find f such that f(x) predicts y"
      }
    },
    {
      "id": 42,
      "name": "Lasso",
      "template": "A4",
      "params": {
        "method": "lasso",
        "nCoefficients": 8,
        "lambdaRange": [0.01, 100],
        "title": "Lasso: L1 Regularization Shrinks Coefficients to Zero",
        "annotation": "As lambda increases, coefficients hit zero — automatic variable selection"
      }
    }
  ]
}
```

### How to Generate the Mapping

Use LLM agents in batches of ~50 concepts. Each batch:

1. Agent receives: list of 50 concept names/descriptions/formulas + the template catalog (this file's Section 2)
2. Agent outputs: JSON array of `{id, name, template, params}` for each concept
3. Agent rules:
   - Every concept MUST get a template assignment
   - Choose the template that best helps someone UNDERSTAND the concept
   - Parameters should create a visualization specific to that concept (not generic)
   - The `title` should name the concept; `annotation` should give the key insight
   - For formulas: embed LaTeX in the annotation where relevant

Batch structure (by chapter, since concepts within a chapter share visual themes):
- Batch 1: Chapters 2-3 (~98 concepts) — regression foundations
- Batch 2: Chapters 4-5 (~84 concepts) — classification + basis expansions
- Batch 3: Chapters 6-7 (~54 concepts) — kernel methods + model assessment
- Batch 4: Chapters 8-9 (~74 concepts) — inference + additive models
- Batch 5: Chapters 10-11 (~57 concepts) — boosting + neural networks
- Batch 6: Chapters 12-13 (~61 concepts) — SVMs + prototypes
- Batch 7: Chapter 14 (~128 concepts) — unsupervised learning
- Batch 8: Chapters 15-18 (~109 concepts) — random forests, ensemble, undirected graphs, high-dimensional

After all batches: review pass to catch bad mappings, merge duplicates, add missing templates.

---

## 4. File Structure

```
output/visuals/
  index.html                    # Concept explorer page (standalone)
  concept-visuals.json          # The 670-entry mapping file
  templates/
    A1-function-plot.js         # Each template is a self-contained module
    A2-function-comparison.js
    A3-surface-3d.js
    A4-regularization-path.js
    B1-scatter-fit.js
    B2-bias-variance.js
    B3-residual-plot.js
    C1-decision-boundary-2d.js
    C2-separating-hyperplane.js
    C3-multiclass-boundary.js
    D1-pca-projection.js
    D2-embedding-viz.js
    D3-scree-plot.js
    E1-decision-tree.js
    E2-dendrogram.js
    E3-graphical-model.js
    F1-iterative-optimization.js
    F2-boosting-steps.js
    F3-em-algorithm.js
    F4-kmeans-animation.js
    G1-matrix-heatmap.js
    G2-cv-grid.js
    H1-distribution.js
    H2-sampling-distribution.js
    I1-network-architecture.js
    I2-feature-space-mapping.js
  lib/
    data-generators.js          # Synthetic data: gaussians, spirals, moons, swiss-roll, etc.
    math-utils.js               # Function evaluation, matrix ops, simple solvers
    style-constants.js          # Shared colors, fonts, dark theme config
```

### Template Module Contract

Every template exports a single function:

```javascript
// templates/A1-function-plot.js
export function render(containerId, params) {
  // params: {function, xRange, sliders, xlabel, ylabel, title, annotation}
  // Creates a Plotly chart inside document.getElementById(containerId)
  // Returns a cleanup function: () => { Plotly.purge(containerId); }
}
```

### Runtime Loader

```javascript
// In index.html or integrated into existing pages
async function showVisual(conceptId, containerId) {
  const mapping = await fetch('concept-visuals.json').then(r => r.json());
  const entry = mapping.concepts.find(c => c.id === conceptId);
  if (!entry) return;

  const templateModule = await import(`./templates/${entry.template}.js`);
  templateModule.render(containerId, entry.params);
}
```

---

## 5. Integration with Existing UI

### Option chosen: Embed in both existing pages + standalone explorer

**A. Knowledge Graph sidebar** (`output/knowledge-graph/index.html`)
- Add a `<div id="concept-visual">` below the existing detail panel
- When a node is clicked and details shown, also call `showVisual(conceptId, 'concept-visual')`
- Size: 320px wide (sidebar width) x 250px tall
- Cleanup previous visual on new selection

**B. Chapter Prereqs sidebar** (`output/chapter-prereqs/index.html`)
- Same pattern: add `<div id="concept-visual">` inside `#concept-detail`
- Triggered on concept click

**C. Standalone Concept Explorer** (`output/visuals/index.html`) — NEW page
- Full-page layout: concept list on left, large visual area center, details on right
- Search + filter by category/chapter
- Visual area: 800x600px — large enough for full interaction
- Navigation links to/from the knowledge graph and chapter prereqs pages

### CDN Dependencies

Add to all pages that host visuals:
```html
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
```

---

## 6. Implementation Steps

### Phase 1: Template Infrastructure (do first)

1. Create `output/visuals/` directory structure
2. Implement `lib/data-generators.js` — synthetic data for scatter plots, clusters, etc.
3. Implement `lib/math-utils.js` — function parser (math.js or a small evaluator), basic linear algebra
4. Implement `lib/style-constants.js` — dark theme colors matching existing UI
5. Build the runtime loader (`showVisual` function)

### Phase 2: Core Templates (8 templates that cover the most concepts)

Build in this order (highest coverage first):

| Order | Template | Est. concepts covered |
|-------|----------|----------------------|
| 1 | A1 — Single Function Plot | ~80 |
| 2 | C1 — 2D Decision Boundary | ~60 |
| 3 | B1 — Scatter with Fit | ~50 |
| 4 | A3 — 3D Surface | ~45 |
| 5 | F1 — Iterative Optimization | ~35 |
| 6 | D1 — PCA Projection | ~30 |
| 7 | G1 — Matrix Heatmap | ~30 |
| 8 | A4 — Regularization Path | ~25 |

These 8 templates alone cover ~355 concepts (53%). Build and test these before expanding.

### Phase 3: Concept Mapping (agent batches)

Run 8 agent batches (see Section 3) to produce `concept-visuals.json`. Each agent:
- Receives the template catalog + batch of concepts from the DB
- Outputs JSON mapping
- Gets reviewed for quality (spot-check 10% per batch)

### Phase 4: Remaining Templates

Build the remaining ~17 templates as the mapping reveals actual demand:
- Some templates from the catalog may not be needed
- Some concepts may need templates not yet designed
- Expect to iterate: add 2-3 templates, then re-map unmapped concepts

### Phase 5: Integration

1. Add visual container to knowledge graph sidebar
2. Add visual container to chapter prereqs sidebar
3. Build standalone explorer page
4. Cross-link all three pages

### Phase 6: Polish

- Test every concept visual loads without error (automated: load each, check for JS exceptions)
- Performance: lazy-load Plotly/Three.js only when needed
- Mobile: ensure Plotly touch interactions work
- Accessibility: add alt-text descriptions from concept descriptions

---

## 7. Scale Estimates

| Item | Count |
|------|-------|
| Total concepts | 670 |
| Unique templates | 25-35 |
| Concepts covered by top 8 templates | ~355 (53%) |
| Concepts covered by top 15 templates | ~550 (82%) |
| Concepts covered by all templates | ~640 (95%) |
| Concepts needing custom one-off visuals | ~30 (5%) |
| Agent batches for mapping | 8 |
| Estimated mapping JSON size | ~200KB |

The 5% that need custom visuals are likely abstract theorems (Gauss-Markov, KKT conditions, Hammersley-Clifford) or meta-concepts (supervised learning, structured regression model). These get a "concept card" fallback: styled display of quote + formula + description, no interactive plot. Not every concept benefits from a chart.

---

## 8. Data Generator Library (lib/data-generators.js)

Critical for templates B, C, D, F. Must generate:

| Generator | Used by templates |
|-----------|-------------------|
| `twoClassGaussian(n, sep, noise)` | C1, C2, C3 |
| `regression(n, trueF, noise)` | B1, B2, B3, F2 |
| `clusters(k, n, dim, spread)` | D1, D2, F4 |
| `swissRoll(n)` | D2 |
| `spirals(n, nClasses)` | C1, D2 |
| `moons(n, noise)` | C1 |
| `timeSeries(n, arCoeffs)` | A1 |
| `multivarNormal(n, mean, cov)` | A3, D1, G1 |

Each returns `{x: Float64Array, y: Float64Array, labels?: Int32Array}`.

---

## 9. Template Parameter Constraints

To keep agents from producing garbage parameters, enforce a schema per template. Example for A1:

```json
{
  "template": "A1",
  "requiredParams": ["function", "xRange"],
  "optionalParams": ["sliders", "xlabel", "ylabel", "title", "annotation"],
  "paramTypes": {
    "function": "string (math expression in x, parseable by math.js)",
    "xRange": "[number, number]",
    "sliders": "[{name: string, param: string, range: [number, number], default: number}]"
  }
}
```

Include this schema in the agent prompt so mapping output validates cleanly.

---

## 10. Open Questions (decide before implementation)

1. **Math expression evaluator**: Use `math.js` (150KB) or write a minimal evaluator for the ~20 operations we need? Recommendation: use math.js. The 150KB cost is negligible given we already load Plotly (3MB).

2. **Three.js scope**: The catalog has only 2 templates (C2, I1) using Three.js. Consider using Plotly's 3D scatter/surface for everything and dropping Three.js entirely. This simplifies the stack. Recommendation: start with Plotly-only, add Three.js only if Plotly's 3D proves insufficient for hyperplane/manifold visuals.

3. **Precomputed vs live data**: Templates C1 (decision boundaries) and F1-F4 (animations) need actual algorithm implementations (KNN, gradient descent, EM). Options: (a) implement in JS, (b) precompute in Python and embed results. Recommendation: implement in JS for true interactivity. The algorithms are simple enough (KNN is trivial, gradient descent is 10 lines, EM is ~50 lines).

4. **Offline-first**: The existing pages use CDN links. For offline use, bundle Plotly locally. Recommendation: defer this — CDN is fine for now, bundle later if needed.
