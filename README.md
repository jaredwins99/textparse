# textparse

Tear technical textbooks apart into a relational knowledge graph, then build
interactive visualizations and assumption explorers on top of it.
*The Elements of Statistical Learning* is the test case; the system is meant
to generalize to any technical book.

### Knowledge graph — chapter view

Each chapter forms a cluster; edges are typed (prerequisite, generalizes,
proves, illustrates).

![Chapter 3 cluster](assets/gifs/kg-chapter3.png)

### Knowledge graph — concept focus

Click any node to see its definition, formula, key facts, and connections —
plus a button straight into its visualization page.

![Ridge Regression and its neighborhood](assets/gifs/kg-ridge-focus.png)

### Concept visualization

One interactive page per concept. Here, ridge regression as a Bayesian MAP:
sharpen the likelihood with the data-signal slider, then deepen the prior
bowl with λ and watch the posterior get pulled to zero.

![Ridge regression — prior reshapes landscape](assets/gifs/ridge.gif)

### Assumption explorer

For each model, every assumption is a column with tiers from textbook-perfect
to broken. Tighten or break an assumption and the guarantee health bars react
in real time.

![Linear regression assumption explorer](assets/gifs/assumptions.gif)

## Architecture

| Module | Path | What it does |
|---|---|---|
| PDF parser | `src/pdf_parser/` | Pulls text, fonts, and spatial layout from PDFs (PyMuPDF + pdfplumber for tables). |
| Database | `src/database/` | SQLAlchemy/SQLite models for textbooks, pages, paragraphs, concepts, and typed edges. |
| Visualization | `src/visualization/` | Static images, manim animations, interactive HTML/JS pages. |
| Output | `output/` | Generated knowledge graph, concept-viz pages, assumption explorers. |

Concept extraction is hybrid: font + regex heuristics first, LLM for the
ambiguous paragraphs and relationship inference.

Stack: Python · SQLAlchemy/SQLite · PyMuPDF · pdfplumber · manim · matplotlib
· Plotly.js · Cytoscape.js

## Running it

```bash
pip install -r requirements.txt
python main.py                # parse + populate DB
python extract_concepts.py    # heuristics + LLM concept pass
```

Generated pages live under `output/`. Open any `.html` directly in a
browser — no server needed.

Issues are tracked in Linear via `scripts/linear.sh`. See `CLAUDE.md` for the
agent system, pedagogy rules, and project philosophy.
