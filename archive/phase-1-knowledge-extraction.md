# Phase 1: Knowledge Extraction Engine

## Goal

Build the algorithmic core that transforms raw parsed paragraphs into structured **knowledge bytes** — atomic units of knowledge with typed relationships — stored in a relational backend. Target: ESL (Elements of Statistical Learning) as the test case.

## Resolved Decisions

- **Hybrid extraction**: Heuristics first (font metadata + regex), LLM for ambiguous content and relationship inference
- **Dual structure**: Full dependency graph (typed edges) + parent-child section tree (mirrors printed layout)
- **Typed paragraphs**: `paragraph_type` field on paragraphs, classified via font metadata + regex
- **Definitions pop**: Definitions are first-class citizens, prominently surfaced. Goal is to strip fluff.
- **DB fix**: Single session per parse run, batch commits. Kill the session-per-operation pattern.
- **Table extraction**: pdfplumber alongside PyMuPDF (PyMuPDF for text/fonts, pdfplumber for tables)
- **Anki**: Deferred to Phase 2. Schema can be added later.
- **Scope**: Applied stats/ML textbooks first

## Context

### What exists
- PDF parser extracts text blocks via PyMuPDF, stores as paragraphs with bounding boxes
- SQLite database: 764 pages, 99,372 paragraphs from ESL. **Zero concepts, zero links.**
- Textbook imported twice (duplicate data)
- Visualization renderer is 100% placeholder
- Font metadata (size, bold, italic) is **thrown away** by the parser — this is the primary signal for classification

### What's missing
1. No concept extraction (the entire point of the project)
2. No paragraph type classification
3. No concept-to-concept relationships
4. No section hierarchy
5. No table extraction
6. Duplicate data, no idempotency

## Steps

### Step 1: Fix DatabaseManager session lifecycle
**File:** `src/database/manager.py`

Refactor to use a single session per operation batch. Add context manager pattern so the parse loop in `main.py` uses one transaction. Add idempotency guard on textbook import (unique constraint on file_path).

### Step 2: Enrich PDF parser with font metadata
**File:** `src/pdf_parser/parser.py`

PyMuPDF's dict output includes per-span: `font`, `size`, `flags` (bold/italic/superscript), `color`. Currently discarded. Add:
- `SpanData` dataclass: text, font, size, flags, color, bbox
- `LineData` dataclass: spans list, bbox
- Add `lines: list[LineData]` to `ExtractedParagraph` (keep `text` as flattened version)

### Step 3: Add pdfplumber table extraction
**New file:** `src/pdf_parser/table_extractor.py`

Use pdfplumber to extract tables as structured data (rows/columns). Store separately from paragraph text. Tables in ESL contain critical model comparison data.

### Step 4: Extend database schema
**File:** `src/database/models.py`

Add:
- `paragraph_type` field on `Paragraph` (enum: section_header, definition, theorem, lemma, proof, example, exercise, figure_caption, table, equation, narrative, bibliography)
- `Section` model (hierarchical: parent_id self-referential, number, title, page range)
- `ConceptRelationship` model (source_id, target_id, relationship_type: prerequisite, generalizes, special_case_of, proved_by, example_of, contrasts_with, uses)
- Unique constraint on Textbook.file_path

### Step 5: Build structural classifier (heuristics)
**New file:** `src/knowledge/classifier.py`

Classify paragraphs using font metadata + regex patterns:
1. Section headers: large font / bold / matches `^\d+(\.\d+)*\s+\w`
2. Definitions: starts with "Definition" or italic term + explanation
3. Theorems/Lemmas: starts with "Theorem/Lemma/Corollary" + number
4. Proofs: starts with "Proof"
5. Examples: starts with "Example" + number
6. Exercises: starts with "Ex." or in exercise sections
7. Figure captions / Table captions: "FIGURE X.Y" / "TABLE X.Y"
8. Equations: short, mostly symbols
9. Narrative: default

Use configurable `ClassifierConfig` with factory `ClassifierConfig.for_esl()`.

### Step 6: Build concept extractor (heuristic + LLM hybrid)
**New file:** `src/knowledge/extractor.py`

**Heuristic pass:**
- Definitions → concept with type "definition"
- Theorems/lemmas → concept with type "theorem"/"lemma"
- Section headers → Section records (build hierarchy from numbering)
- Bold/italic first-mentions in narrative → candidate concepts (lower confidence)

**LLM pass (for ambiguous content):**
- Narrative paragraphs that mention statistical methods/algorithms but aren't formally structured
- Relationship inference between concepts that aren't explicitly cross-referenced
- Operates on batches, not individual paragraphs

### Step 7: Build relationship mapper
**New file:** `src/knowledge/relationships.py`

Infer relationships from:
1. Document ordering (A before B in same section → A prerequisite for B)
2. Explicit references ("as in Theorem 3.1", "using X", "a special case of Y")
3. Section hierarchy (parent section generalizes child concepts)
4. LLM inference for implicit relationships

### Step 8: Wire CLI and clean up
**File:** `main.py`

Subcommands:
- `python main.py parse <pdf_path>` — parse + classify
- `python main.py extract <textbook_id>` — concept extraction + relationship mapping
- `python main.py info <textbook_id>` — stats summary

Clean up:
- Delete duplicate textbook data
- Re-parse ESL with enriched parser
- Remove stale code/files as needed

## File Structure After Phase 1

```
src/
  pdf_parser/
    parser.py              # MODIFIED: font metadata
    table_extractor.py     # NEW: pdfplumber tables
  database/
    models.py              # MODIFIED: Section, ConceptRelationship, paragraph_type
    manager.py             # MODIFIED: session lifecycle, idempotency
  knowledge/               # NEW PACKAGE
    classifier.py          # Paragraph type classification
    extractor.py           # Concept extraction (heuristic + LLM)
    relationships.py       # Relationship inference
  visualization/
    renderer.py            # UNTOUCHED (Phase 2)
main.py                    # MODIFIED: CLI subcommands
```

## Open Questions

1. How good are PyMuPDF font flags for ESL specifically? Need a diagnostic script to inspect font metadata on sample pages before calibrating classifier thresholds.
2. LaTeX equation extraction — deferred. Classify equation blocks, store raw text, flag for Phase 2 enrichment.
3. Which LLM to use for the hybrid extraction pass? Could use Claude API directly, or keep it model-agnostic.
4. Re-parse vs backfill existing data? **Re-parse.** Font metadata is critical and wasn't captured. Delete and rebuild is cleaner.

## Definition of Done

- [ ] `python main.py parse data/ESL.pdf` produces classified paragraphs (every paragraph has a `paragraph_type`)
- [ ] `python main.py extract 1` populates `concepts`, `sections`, `concept_relationships`, `paragraph_concepts`
- [ ] ESL has: 50+ named concepts, section hierarchy matching table of contents, relationship edges
- [ ] `python main.py info 1` prints summary: N concepts, M relationships, section tree depth
- [ ] No duplicate textbook rows. Re-running parse updates rather than duplicates
- [ ] Single session per parse run, not session-per-operation
- [ ] Tables extracted via pdfplumber and stored with structure preserved
