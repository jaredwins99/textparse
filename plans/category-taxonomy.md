# Plan: 6-Category Taxonomy Implementation

**Status**: Ready to implement
**Date**: 2026-02-17
**Scope**: DB schema, batch reclassification of 670 concepts, visualization updates, export script

---

## 1. Context and Current State

### Current category field

The `Concept` model has a single `category` column (`String(100)`, nullable). Current distribution across 670 concepts:

| Category    | Count |
|-------------|-------|
| method      | 178   |
| technique   | 150   |
| metric      | 113   |
| property    | 106   |
| definition  | 56    |
| algorithm   | 54    |
| theorem     | 5     |
| parameter   | 4     |
| principle   | 1     |
| model       | 1     |
| example     | 1     |
| estimator   | 1     |

These categories are descriptive nouns about the *form* of a concept (is it a method? an algorithm?), not its *function* in the ML epistemology. The new taxonomy replaces this with a functional classification.

### Where `category` is consumed

1. **`src/visualization/export_graph.py`**: Selects `c.category` and emits it as `"category"` in every node's data dict.
2. **`output/knowledge-graph/index.html`**:
   - `CATEGORY_COLORS` maps category strings to hex colors for node rendering.
   - Category filter checkboxes are built dynamically from node data.
   - The detail panel badge shows `data.category` with its background color.
   - The legend is built from `CATEGORY_COLORS` keys.
3. **`src/database/models.py`**: `Concept.category` is a plain `String(100)` column with no constraint.
4. **`src/database/manager.py`**: `get_or_create_concept()` accepts `category` as a parameter; `get_all_concepts()` returns all fields including category. No other methods touch it directly.

---

## 2. New Taxonomy

Six top-level categories, each with two subcategories:

| Category       | Subcategory A               | Subcategory B                  |
|----------------|-----------------------------|--------------------------------|
| **Model**      | DGP                         | Pseudo Model                   |
| **Estimation** | Criteria                    | Optimization                   |
| **Validation** | Diagnostics                 | Validation                     |
| **Guarantees** | Assumptions                 | Guarantees                     |
| **Multi-Model**| Selection                   | Aggregating                    |
| **Improvements**| Preprocessing              | Efficiencies                   |

**Subcategory semantics:**

- **Model/DGP**: Data generating processes — probabilistic models, generative models, likelihood functions, joint distributions (e.g., Gaussian mixture model, linear regression DGP, Markov random field)
- **Model/Pseudo Model**: Discriminative/predictive models — classifiers, regressors, decision boundaries (e.g., SVM, neural network, CART, k-NN)
- **Estimation/Criteria**: Objective functions, loss functions, estimating equations, RSS, log-likelihood, OLS criterion (e.g., cross-entropy loss, RSS, Gini index)
- **Estimation/Optimization**: Algorithms that minimize criteria — SGD, coordinate descent, Newton methods, backprop (e.g., gradient boosting, IRLS, conjugate gradients)
- **Validation/Diagnostics**: In-sample fit metrics, residual analysis, training error, AIC/BIC as training-set summaries (e.g., R², residual sum of squares, deviance)
- **Validation/Validation**: Out-of-sample assessment — cross-validation, test error, generalization (e.g., CV error, .632 estimator, test set performance)
- **Guarantees/Assumptions**: Conditions required for results to hold (e.g., identifiability, iid assumption, regularity conditions, stationarity)
- **Guarantees/Guarantees**: Theoretical results — consistency, unbiasedness, convergence rates, bias-variance decomposition (e.g., Cover and Hart result, Bayes rate, VC dimension)
- **Multi-Model/Selection**: Model selection, regularization, information criteria, priors that choose among models (e.g., lasso, ridge, BIC, AIC, Bayesian model selection)
- **Multi-Model/Aggregating**: Ensembles, boosting, bagging, model averaging (e.g., AdaBoost, random forests, stacking, committee methods)
- **Improvements/Preprocessing**: Dimension reduction, feature engineering, basis expansions, SVD/PCA (e.g., PCA, wavelet basis, B-splines, kernel trick)
- **Improvements/Efficiencies**: Computational tricks, factorizations, parametrizations that make existing computations cheaper (e.g., QR decomposition, Cholesky, log-sum-exp trick, Reinsch form)

---

## 3. DB Schema Changes

### 3.1 New columns

Add two new columns to `concepts` table:

```python
# In src/database/models.py, on the Concept class:
new_category = Column(String(100), nullable=True)   # e.g. "Model", "Estimation"
subcategory  = Column(String(100), nullable=True)   # e.g. "DGP", "Optimization"
```

Keep `category` as-is. Do not drop it. It serves as a fallback and audit trail during reclassification.

### 3.2 Migration script

Write a standalone migration (not managed by Alembic — the project uses raw SQLite). A simple Python script is sufficient:

```python
# scripts/migrate_add_new_category.py
import sqlite3
DB = "data/textbooks.db"
conn = sqlite3.connect(DB)
try:
    conn.execute("ALTER TABLE concepts ADD COLUMN new_category TEXT")
    print("Added new_category")
except sqlite3.OperationalError:
    print("new_category already exists")
try:
    conn.execute("ALTER TABLE concepts ADD COLUMN subcategory TEXT")
    print("Added subcategory")
except sqlite3.OperationalError:
    print("subcategory already exists")
conn.commit()
conn.close()
```

Run once before any reclassification work. Script is idempotent (catches OperationalError if columns exist).

### 3.3 Model update

In `src/database/models.py`, add to the `Concept` class:

```python
new_category = Column(String(100), nullable=True)
subcategory  = Column(String(100), nullable=True)
```

No ORM migration needed — SQLite's `ALTER TABLE ADD COLUMN` is sufficient since both columns are nullable.

### 3.4 Manager update

In `src/database/manager.py`, update `get_or_create_concept()` signature to accept optional `new_category` and `subcategory`. Add a new helper:

```python
def update_concept_taxonomy(self, concept_id: int, new_category: str, subcategory: str):
    """Set new_category and subcategory on a concept by ID."""
    session, standalone = self._get_session()
    try:
        concept = session.get(Concept, concept_id)
        if concept:
            concept.new_category = new_category
            concept.subcategory = subcategory
            if standalone:
                session.commit()
            else:
                session.flush()
    except Exception:
        if standalone:
            session.rollback()
        raise
    finally:
        if standalone:
            session.close()
```

---

## 4. Batch Reclassification of 670 Concepts

### 4.1 Strategy

LLM reclassification is the only realistic approach. The old categories (method, technique, algorithm, etc.) describe form, not function — heuristic rules cannot reliably distinguish e.g. "gradient boosting" (Estimation/Optimization) from "AdaBoost" (Multi-Model/Aggregating) without reading their descriptions.

Each concept will be classified using:
- `name` (always present)
- `description` (present for most; raw paragraph text for many)
- `category` (old category, as a weak signal)

### 4.2 Batch sizing

670 concepts total. Recommended: **7 batches of ~100 concepts each** (last batch ~70).

Rationale:
- 100 concepts with name + description fits comfortably in a single LLM context window
- Each batch takes 1-3 minutes; parallelizing 7 agents runs the full set in ~5 minutes
- Batch size is small enough that a failed batch can be rerun without losing much work
- Results are written directly to the DB per batch, so partial completion is safe

### 4.3 Concept ordering for batches

Order by `id` (insertion order). Do not randomize — predictable batches make reruns deterministic.

- Batch 1: id 1-100
- Batch 2: id 101-200
- Batch 3: id 201-300
- Batch 4: id 301-400
- Batch 5: id 401-500
- Batch 6: id 501-600
- Batch 7: id 601-670

### 4.4 Context each subagent needs

Each subagent receives:
1. The taxonomy definition (category/subcategory names and their semantics) — verbatim from Section 2 of this plan
2. A JSON array of `{id, name, description, category}` for its batch (100 rows)
3. Instructions to produce a JSON array of `{id, new_category, subcategory}` for every concept in its batch
4. A constraint: `new_category` must be one of `["Model", "Estimation", "Validation", "Guarantees", "Multi-Model", "Improvements"]`; `subcategory` must be the valid subcategory for that category

**Ambiguous cases**: If a concept legitimately belongs to two categories (e.g., PCA is both Improvements/Preprocessing and a technique used in model fitting), classify by primary function in the context of ESL. PCA's primary pedagogical role in ESL is dimensionality reduction before modeling → `Improvements/Preprocessing`.

**Fallback**: If a concept is truly unclassifiable (e.g., a definition of a math symbol), use `new_category = "Model"`, `subcategory = "DGP"` as the default and flag it in a comment for manual review.

### 4.5 Reclassification script

Write `scripts/reclassify_concepts.py` that:
1. Accepts `--batch-file <json>` argument pointing to the LLM output file
2. Reads `[{id, new_category, subcategory}, ...]`
3. Validates each `new_category` and `subcategory` against the allowed set
4. Updates the DB using `UPDATE concepts SET new_category=?, subcategory=? WHERE id=?`
5. Prints a summary: N updated, M skipped (invalid), K already set

This decouples LLM calls from DB writes — each batch is a separate JSON file, stored in `data/extraction/taxonomy/batch-{N}.json` for auditability.

### 4.6 Validation after reclassification

After all 7 batches are written:

```sql
-- Check coverage
SELECT COUNT(*) FROM concepts WHERE new_category IS NULL;

-- Distribution check
SELECT new_category, subcategory, COUNT(*)
FROM concepts
GROUP BY new_category, subcategory
ORDER BY new_category, subcategory;

-- Sanity: no invalid categories
SELECT DISTINCT new_category FROM concepts WHERE new_category NOT IN
  ('Model','Estimation','Validation','Guarantees','Multi-Model','Improvements');
```

Expected rough distribution (from ESL content, highly approximate):
- Model: ~80 (DGP ~40, Pseudo Model ~40)
- Estimation: ~180 (Criteria ~90, Optimization ~90)
- Validation: ~70 (Diagnostics ~35, Validation ~35)
- Guarantees: ~60 (Assumptions ~25, Guarantees ~35)
- Multi-Model: ~130 (Selection ~60, Aggregating ~70)
- Improvements: ~150 (Preprocessing ~80, Efficiencies ~70)

If a category has <20 or >250, spot-check those concepts — likely the prompt was misinterpreted for that category.

---

## 5. Visualization Updates

### 5.1 `export_graph.py`

Change the SQL query to export `new_category` and `subcategory` alongside the existing `category`:

```python
c.execute("""
    SELECT c.id, c.name, c.description, c.category,
           c.new_category, c.subcategory,
           c.section_id, c.quote, c.formula,
           s.number as section_number, s.title as section_title
    FROM concepts c
    LEFT JOIN sections s ON c.section_id = s.id
""")
```

In the node data dict:
```python
nodes.append({
    "data": {
        ...
        "category":     row["new_category"] or row["category"] or "other",
        "subcategory":  row["subcategory"] or "",
        "old_category": row["category"] or "",
        ...
    }
})
```

The `category` field in the node data becomes the new taxonomy category. `old_category` is kept for debugging but not used by the visualization. `subcategory` is a new field the detail panel will consume.

### 5.2 `index.html` — color scheme

Replace the current 8-color `CATEGORY_COLORS` map with 6 colors for the new categories. Use colors that are visually distinct, work on the dark `#1a1a2e` background, and suggest the semantic role of each category:

```javascript
var CATEGORY_COLORS = {
    "Model":        "#4C72B0",   // blue — foundational structures
    "Estimation":   "#DD8452",   // orange — active fitting/computing
    "Validation":   "#55A868",   // green — checking/measuring
    "Guarantees":   "#C44E52",   // red — theoretical stakes
    "Multi-Model":  "#8172B2",   // purple — combining multiple things
    "Improvements": "#64B5CD",   // teal — enhancements
    "other":        "#999999"    // fallback during transition
};
```

Keep `"other"` as a fallback for the transition period when `new_category` may still be null for some concepts.

### 5.3 `index.html` — detail panel subcategory display

In the node click handler, after the category badge, add a subcategory line:

```javascript
// After setting badge.textContent = data.category:
var subBadge = document.getElementById('detail-subcategory');
if (data.subcategory) {
    subBadge.textContent = data.subcategory;
    subBadge.style.display = 'inline-block';
} else {
    subBadge.style.display = 'none';
}
```

Add the element to the HTML sidebar:
```html
<span class="category-badge" id="detail-category"></span>
<span class="subcategory-badge" id="detail-subcategory" style="display:none;"></span>
```

Add CSS:
```css
#concept-detail .subcategory-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    margin-bottom: 12px;
    margin-left: 6px;
    background: rgba(255,255,255,0.1);
    color: #aaa;
    border: 1px solid #444;
}
```

### 5.4 `index.html` — filter panel

The category filter checkboxes are built dynamically from node data — no hardcoding needed. They will automatically reflect the new 6 categories once `graph-data.js` is regenerated.

Optionally, add a second filter group for subcategories (12 values). Build it the same way as the category filter:

```javascript
var subCatFilters = document.getElementById('subcategory-filters');
var subcategories = [];
var subCatSet = {};
GRAPH_DATA.nodes.forEach(function(n) {
    if (n.data.isParent || !n.data.subcategory) return;
    if (!subCatSet[n.data.subcategory]) {
        subCatSet[n.data.subcategory] = true;
        subcategories.push(n.data.subcategory);
    }
});
// build checkboxes same as category filter
```

Add the HTML div:
```html
<div class="filter-group" id="subcategory-filters">
    <h4>Subcategories</h4>
</div>
```

Update `applyFilters()` to also check the active subcategories, applying the subcategory filter only when subcategory is non-empty (concepts with no subcategory pass through).

### 5.5 Legend update

The legend is currently built from `Object.keys(CATEGORY_COLORS)`. With the new map, it will show 6 entries (plus "other"). No code change needed beyond the color map replacement.

Optionally, add a second legend block for subcategories below the category legend — a simple HTML list with the 12 subcategory names grouped under their parent category labels.

---

## 6. Implementation Order

1. **Schema migration** — run `migrate_add_new_category.py`, update `models.py` and `manager.py`
2. **Write reclassification tooling** — `scripts/reclassify_concepts.py` (the DB writer)
3. **Run 7 LLM batches** — generate `data/extraction/taxonomy/batch-{1..7}.json`, then apply
4. **Validate distribution** — SQL queries from Section 4.6
5. **Update `export_graph.py`** — emit `new_category`, `subcategory`, `old_category`
6. **Regenerate `graph-data.js`** — run export script
7. **Update `index.html`** — new colors, subcategory badge, subcategory filter panel
8. **Smoke test** — open visualization, confirm 6 color categories visible, subcategory shows in detail panel, filters work

---

## 7. Files Changed

| File | Change |
|------|--------|
| `src/database/models.py` | Add `new_category`, `subcategory` columns to Concept |
| `src/database/manager.py` | Add `update_concept_taxonomy()`, update `get_or_create_concept()` |
| `src/visualization/export_graph.py` | Export `new_category`, `subcategory`, `old_category` |
| `output/knowledge-graph/index.html` | New colors, subcategory badge, subcategory filter |
| `scripts/migrate_add_new_category.py` | New — one-shot DB migration |
| `scripts/reclassify_concepts.py` | New — apply LLM batch JSON to DB |
| `data/extraction/taxonomy/batch-{1..7}.json` | New — LLM classification outputs |

`output/chapter-prereqs/index.html` and `output/chapter-prereqs/graph-data.js` do not consume `category` for coloring — no change needed there.

---

## 8. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM hallucinates invalid category names | `reclassify_concepts.py` validates against allowed set; invalid rows are skipped and logged |
| Many concepts have truncated/raw descriptions | Pass both `name` and `description`; name alone is often sufficient for ESL concepts |
| ~60 concepts currently have ambiguous old categories (e.g., "definition" covers math defs, model defs, algorithm defs) | These are the hardest batch; consider doing these as a separate pass with extra context |
| `new_category` null during transition breaks visualization | Export script falls back to `old_category`; visualization has `"other"` fallback color |
| Batch files lost or corrupted | Store in `data/extraction/taxonomy/` which is already gitignored from DB; add these JSON files to `.gitignore` as well |
