# Text Parse
**Automatic textbook parser and interactive visualizer, with a proof-of-concept results from *Elements of Statistical Learning***

*STATUS: Post-LLM*

**Note**: This is a work in progress and I have only validated and added citations to most of Ch 3. 

### Knowledge graph, chapter view

Each chapter forms a cluster; edges are typed (prerequisite, generalizes,
proves, illustrates).

![Chapter 3 cluster](assets/gifs/kg-chapter3.png)

### Knowledge graph, concept focus

Click any node to see its definition, formula, key facts, and connections, as well as a button straight into its visualization page.

![Ridge Regression and its neighborhood](assets/gifs/kg-ridge-focus.png)

### Concept visualization

One interactive page per concept. 
Here, ridge regression is shown as a Bayesian MAP.
Sharpen the likelihood with the data-signal slider, then deepen the prior bowl with λ and watch the posterior get pulled to zero.

![Ridge regression — prior reshapes landscape](assets/gifs/ridge.gif)

### Assumption explorer

For OLS, every assumption is a column with tiers from fully upheld to mostly broken. 
Tighten or break assumptions to get a rough sense of how results change.

![Linear regression assumption explorer](assets/gifs/assumptions.gif)

## Architecture

| Module | Path | What it does |
|---|---|---|
| PDF parser | `src/pdf_parser/` | Pulls text, fonts, and spatial layout from PDFs (PyMuPDF + pdfplumber for tables). |
| Database | `src/database/` | SQLAlchemy/SQLite models for textbooks, pages, paragraphs, concepts, and typed edges. |
| Visualization | `src/visualization/` | Static images, manim animations, interactive HTML/JS pages. |
| Output | `output/` | Generated knowledge graph, concept-viz pages, assumption explorers. |

Concept extraction is hybrid: font + regex heuristics first, LLM for the ambiguous paragraphs and relationship inference.

## Checking it out

Generated pages live under `output/`. Open any `.html` directly in a browser — no server needed.

Issues are tracked in Linear via `scripts/linear.sh`. See `CLAUDE.md` for the
agent system, pedagogy rules, and project philosophy.
