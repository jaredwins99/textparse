# Quote Curation Plan

**Status**: Draft
**Last updated**: 2026-02-17
**Context**: 661/670 concepts have LLM-assigned quotes from the ESL textbook. The user wants to review these, approve/reject them, provide "good" examples to train the selection process, and suggest alternatives.

---

## Current State

Quotes live in the `concepts.quote` column (TEXT, nullable). They were bulk-assigned by LLM agents working from batched JSON exports (`data/extraction/quotes_1-6.json`). Quality is uneven — the LLM picked a plausible sentence but had no feedback signal for what "good" means to the user.

The existing pipeline already demonstrates the JSON roundtrip pattern: `export_quotes_by_chapter.py` dumps to `data/extraction/quote_batch_N.json`, and `integrate_quotes.py` reads those back and writes to the DB. Any curation approach can plug into this same pattern.

---

## Options

---

### Option A: In-Browser Review UI (extend the knowledge graph)

Add a review mode to the existing knowledge graph at `output/knowledge-graph/index.html`. When a concept node is clicked, the sidebar shows the current quote with three controls: **Approve**, **Reject**, and **Edit**. Decisions are accumulated in `localStorage` or written to a `data/review.json` file via a small local server endpoint. A separate import step writes approved/edited quotes back to the DB.

**What it takes**: ~200 lines of JS added to `index.html`, plus a minimal Flask/FastAPI server (10-20 lines) to handle save-to-disk since browsers can't write files directly. Alternatively, a periodic "download current state" button avoids the server entirely.

**Pros**:
- Already in the graph context — you see the concept's relationships and category while reviewing, which helps judge quote relevance
- Fastest browsing speed; can skip concepts you don't care about
- No terminal required; feels natural

**Cons**:
- Needs a local server to write to disk, or relies on a clunky manual "download JSON" step
- Can't easily see candidate alternative quotes from the source text (you'd have to look them up in the PDF separately)
- More code to maintain — touches the UI layer

---

### Option B: JSON Review File (export, edit, reimport)

Export all 670 concepts + quotes to a flat JSON file, one entry per concept. The user opens it in VS Code, edits quote fields directly, flags bad ones, and runs an import script to sync back to the DB. The export script could also include a `status` field (`"approved"` / `"rejected"` / `"edited"`) to track review progress.

**Export format**:
```json
[
  {
    "id": 1,
    "name": "supervised learning",
    "quote": "For each there is a set of variables that might be denoted as inputs...",
    "status": "pending",
    "note": ""
  }
]
```

**What it takes**: ~40 lines of export script (trivial), ~30 lines of import script (already mostly written in `integrate_quotes.py`).

**Pros**:
- Zero new infrastructure — the roundtrip already exists
- Full editor power: search, batch-edit, copy-paste from the PDF
- Easy to share / version control the review file
- Status field gives a natural progress tracker

**Cons**:
- 670 entries is a lot to scroll through in a JSON file
- No visual context (can't see concept relationships or category while reviewing)
- Easy to accidentally corrupt JSON syntax
- Tedious for concepts you just want to approve — you still have to touch every entry

---

### Option C: CLI Reviewer (interactive terminal script)

A Python script (`review_quotes.py`) that iterates through concepts one-by-one, prints the concept name, description, and current quote, then prompts: `[a]pprove / [r]eject / [e]dit / [s]kip / [q]uit`. Saves state to `data/review_progress.json` so sessions can be interrupted and resumed. Skipped concepts can be revisited in a second pass.

**Example session**:
```
Concept 47/670: gradient descent
Category: Optimization  |  Chapter 8
Description: Iterative method for minimizing a differentiable function.

Quote:
  "For a quadratic criterion as in linear regression, gradient descent always converges..."

[a]pprove  [r]eject  [e]dit  [s]kip  [q]uit  > a
✓ Approved (48/670)
```

**What it takes**: ~150 lines of Python. Resume logic is ~20 lines (write index to progress file).

**Pros**:
- Forces a linear pass — you actually see every quote
- Resume-anywhere means no pressure to finish in one sitting
- Edit mode can open `$EDITOR` with the quote pre-filled, or prompt for inline replacement
- Easy to add a "show candidates" mode that queries the DB for nearby paragraphs
- No server, no browser, no JSON syntax hazard

**Cons**:
- Terminal-only; less visual than the graph UI
- No context about concept relationships while reviewing
- Linear iteration is slower than jumping to the concepts you care about most

---

### Option D: Annotated Examples File (few-shot training set)

Skip bulk review for now. Instead, the user creates a small file — `data/quote_examples.json` or `data/quote_examples.md` — containing 15-25 "ideal" quotes manually curated by hand. Each entry notes the concept, the chosen quote, and optionally a brief note explaining why it's good ("tight definition", "shows the formula in context", "contrasts with alternative approach"). LLM agents use this file as few-shot examples when re-running quote selection for the full 670.

**Example format**:
```json
[
  {
    "concept": "lasso",
    "quote": "The lasso estimate is defined by β̂_lasso = argmin_β { Σ(y_i - β_0 - Σx_ij β_j)² } subject to Σ|β_j| ≤ t.",
    "why": "Contains the actual constraint formulation — the mathematical heart of the concept."
  },
  {
    "concept": "bias-variance tradeoff",
    "quote": "As the model complexity increases, the variance tends to increase and the squared bias tends to decrease.",
    "why": "Clean directional statement of the tradeoff, no fluff."
  }
]
```

**What it takes**: User time only — no code. Agents read this file before selecting quotes.

**Pros**:
- Lowest effort for the user upfront
- Forces the user to articulate what "good" looks like, which sharpens the signal for agents
- Immediately usable — no build step, no UI, no script to run
- Examples naturally cluster around what the user cares about most

**Cons**:
- Doesn't address the 661 existing quotes — the user still can't review them without another mechanism
- 15-25 examples may not cover the variety of concept types (algorithm, theorem, heuristic, meta-concept)
- Requires re-running quote extraction, which costs LLM tokens for all 670

---

## Recommendation

These options are not mutually exclusive. A natural sequence:

1. **Start with Option D** — write ~15 example quotes to establish what "good" means. This is 30 minutes of work and immediately makes re-extraction better.
2. **Then Option C** — run the CLI reviewer to sweep the 661 existing quotes. Mark the clearly good ones approved, the bad ones rejected. This surfaces the full scope of the quality problem.
3. **Option A** as a later enhancement once the graph UI is more developed — the review controls belong in the same interaction where you're exploring concepts anyway.

Option B (raw JSON editing) is the worst path: it combines the verbosity of a full export with the friction of hand-editing JSON. Skip it unless the other options break down.

---

## DB Schema Note

The `concepts` table already has the `quote` column. To support curation, add one more column:

```sql
ALTER TABLE concepts ADD COLUMN quote_status TEXT DEFAULT 'pending';
-- Values: 'pending', 'approved', 'rejected', 'edited'
```

This avoids a separate review file and keeps curation state durable across runs.

---

## Open Questions

1. When rejecting a quote, should the system automatically search for an alternative from linked paragraphs in the DB, or flag the concept for manual re-extraction?
2. How many example quotes (Option D) are needed before re-extraction quality is meaningfully better? Likely 20-30, covering at least: algorithm definition, theorem statement, heuristic/intuition, and meta-concept categories.
3. Should approved quotes be frozen from future re-extraction runs, or always overwritable?
