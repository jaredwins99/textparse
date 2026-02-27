# Concept Enrichment Agent Pass

Goal: For each of the 670 concepts in the DB, extract multiple **verbatim quote snippets** from ESL paragraphs that capture the concept's key facts. Store these as structured rows in a new `concept_facts` table.

---

## Current State (verified against DB)

| Metric | Value |
|--------|-------|
| Total concepts | 670 |
| Concepts with `quote` | 661 |
| Concepts with `formula` | 302 |
| Concepts with `section_id` | 670 (all) |
| Total paragraphs | 49,651 |
| paragraph_concepts link rows | 69 (nearly empty — not usable as primary lookup) |
| Distinct concept_ids in paragraph_concepts | 68 |
| Paragraph types | narrative (31,856), equation (16,239), section_header (646), bibliography (341), figure_caption (323), exercise (207), table_caption (35) |

The `paragraph_concepts` many-to-many table is effectively empty. It cannot be used as the primary paragraph retrieval path. The working retrieval path is: **concept → section_id → section.page_start → paragraphs on those pages**.

Section `page_end` is NULL for all 324 sections. The effective page range for a section is:
- `page_start` = section.page_start
- `page_end` = MIN(page_start of next sibling in same parent) - 1, or if no next sibling, the parent's next sibling page_start - 1

---

## Design Decisions

### 1. Storage: New `concept_facts` Table

Reject the JSON-column approach. A dedicated table is the right choice because:
- Each fact is independently queryable (for Anki card generation, visualization, filtering by type)
- Facts can be ranked/ordered by importance
- The existing `quote` field on `Concept` stays as the single "primary" quote — `concept_facts` adds depth, not replacement

**Schema to add to `models.py`:**

```python
class ConceptFact(Base):
    """A verbatim key fact extracted from the textbook for a concept."""
    __tablename__ = 'concept_facts'

    id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    fact_text = Column(Text, nullable=False)      # verbatim quote from the book
    fact_type = Column(String(50), nullable=True) # 'definition', 'formula', 'property', 'example', 'comparison', 'intuition'
    page_number = Column(Integer, nullable=True)  # page the quote came from
    paragraph_id = Column(Integer, ForeignKey('paragraphs.id'), nullable=True)  # source paragraph if linkable
    importance_rank = Column(Integer, nullable=True)  # 1 = most important, ascending

    concept = relationship("Concept", back_populates="facts")
    paragraph = relationship("Paragraph")
```

Add to `Concept`:
```python
facts = relationship("ConceptFact", back_populates="concept", cascade="all, delete-orphan", order_by="ConceptFact.importance_rank")
```

This requires a schema migration: `ALTER TABLE concepts ADD ... ` is not needed (it's a new table). Run `Base.metadata.create_all(engine)` to create it.

### 2. Paragraph Retrieval Strategy

Since `paragraph_concepts` is empty, retrieve paragraphs by **page range derived from section hierarchy**:

```sql
-- Step 1: Get the concept's section page_start
SELECT s.page_start, s.parent_id, s.id as section_id
FROM sections s
JOIN concepts c ON c.section_id = s.id
WHERE c.id = :concept_id;

-- Step 2: Get page_start of the next sibling section (defines end of range)
SELECT MIN(s2.page_start) as next_page
FROM sections s2
WHERE s2.parent_id = :parent_id
  AND s2.page_start > :this_page_start;

-- Step 3: Fetch paragraphs in that page range
SELECT p.id, p.text, p.paragraph_type, pg.page_number
FROM paragraphs p
JOIN pages pg ON p.page_id = pg.id
WHERE pg.page_number >= :page_start
  AND pg.page_number < :next_page
  AND p.paragraph_type IN ('narrative', 'equation', 'table_caption', 'figure_caption')
ORDER BY pg.page_number, p.sequence_index;
```

**Fallback when section has no siblings:** Walk up to parent section and use its range. If still no bound, use page_start to page_start + 15 as a soft cap.

**Context expansion:** Some concepts (especially those in "Introduction" sections with 40+ concepts) need cross-section search. For these, also fetch paragraphs where the concept name appears literally in the text:

```sql
SELECT p.id, p.text, pg.page_number
FROM paragraphs p
JOIN pages pg ON p.page_id = pg.id
WHERE p.text LIKE '%ridge regression%'
  AND p.paragraph_type IN ('narrative', 'equation')
ORDER BY pg.page_number
LIMIT 30;
```

Use both sources, deduplicate by paragraph_id.

### 3. LLM Prompt Design

The agent receives a batch of concepts. For each concept it runs one LLM call with this structure:

**System prompt:**
```
You are extracting key facts about statistical/ML concepts from a textbook.
You will receive: (1) a concept name and description, (2) a list of paragraphs from the textbook.
Your job: identify the 3-7 most important facts about this concept and extract them as VERBATIM QUOTES.

Rules:
- Quotes must be copied exactly from the provided paragraphs. Do not paraphrase.
- Prefer: definitions, formulas stated in prose, key properties, comparisons to other methods, intuitions given by the authors.
- Avoid: generic sentences, section headers, figure captions that reference images.
- For each fact, label its type: definition | formula | property | comparison | intuition | example
- Rank facts by importance: 1 = the single most essential thing to know about this concept.
```

**User message template:**
```
Concept: {name}
Description: {description}
Category: {new_category} / {subcategory}

Paragraphs from the textbook section covering this concept:
---
{paragraph_texts joined with '\n---\n'}
---

Return JSON:
{
  "facts": [
    {
      "fact_text": "<verbatim quote>",
      "fact_type": "definition|formula|property|comparison|intuition|example",
      "importance_rank": <1-7>,
      "source_paragraph_id": <int or null>
    }
  ]
}
```

**Model:** Claude claude-sonnet-4-5-20250929 (sufficient for extraction, faster/cheaper than Opus). Use `claude-opus-4-6` only for concepts in Introduction sections with 40+ sibling concepts where disambiguation is hard.

### 4. Batching Strategy

**Batch size: 20 concepts per agent call.**

Rationale:
- 670 concepts / 20 = 34 batches
- Each batch: ~20 LLM calls (one per concept), ~300 paragraphs fetched total
- Batches are independent — can run in parallel (up to system/API limits)
- Failure in one batch does not affect others

**Grouping:** Batch by section to keep DB queries efficient (concepts in the same section share the same paragraphs). Fetch section paragraphs once per section, then run the concept-level LLM calls against that cached paragraph set.

**Parallelism:** Run up to 5 batches concurrently. Total runtime estimate: 34 batches / 5 parallel = ~7 rounds. At ~30s per batch (20 LLM calls × 1.5s each), total wall time ≈ 3-4 minutes.

---

## Implementation Plan

### Phase 1: Schema Migration

File: `src/database/models.py`

Add `ConceptFact` class and update `Concept.facts` relationship. Run `Base.metadata.create_all(engine)` to create the table without touching existing data.

### Phase 2: Paragraph Fetcher Module

File: `src/knowledge/paragraph_fetcher.py`

```python
def get_paragraphs_for_concept(session, concept_id) -> list[dict]:
    """
    Returns list of {id, text, paragraph_type, page_number} for paragraphs
    in the concept's section range, plus name-search matches.
    Deduplicates by paragraph id.
    """
```

```python
def get_section_page_range(session, section_id) -> tuple[int, int]:
    """
    Returns (page_start, page_end_exclusive) for a section.
    page_end is inferred from next sibling's page_start.
    Falls back to page_start + 15 if no sibling found.
    """
```

### Phase 3: Enrichment Agent Script

File: `src/knowledge/enrich_concepts.py`

```
usage: python src/knowledge/enrich_concepts.py [--batch-size 20] [--parallel 5] [--concept-ids 1,2,3] [--dry-run]
```

Logic:
1. Load all concepts from DB grouped by section_id
2. For each section group: fetch paragraphs once
3. Build batches of 20 concepts
4. For each batch (parallelized): call LLM per concept, parse JSON response, write ConceptFact rows
5. Commit after each batch
6. Log progress: concepts enriched, facts written, errors

**Idempotency:** Before writing, check `SELECT COUNT(*) FROM concept_facts WHERE concept_id = :id`. If > 0, skip (unless `--force` flag passed). This allows re-running safely.

**Error handling:** If LLM returns invalid JSON or quotes that don't appear in the source paragraphs, log the failure and continue. Write a `failed_concepts.json` to `data/extraction/` for manual review.

**Quote validation:** After parsing LLM output, verify each `fact_text` is a substring of one of the provided paragraphs (or at most a light edit — no validation that's too strict). If not found in any paragraph, mark `paragraph_id = NULL` and flag with `fact_type = 'unverified'`.

### Phase 4: Verification Script

File: `src/knowledge/verify_enrichment.py`

Quick sanity check:
- How many concepts have >= 3 facts
- Distribution of fact_types
- Sample 5 concepts and print their facts for manual review
- Flag any concept with 0 facts

```
python src/knowledge/verify_enrichment.py
```

---

## File Checklist

| File | Action |
|------|--------|
| `src/database/models.py` | Add `ConceptFact` model, update `Concept.facts` relationship |
| `src/knowledge/paragraph_fetcher.py` | New: section page-range logic + paragraph retrieval |
| `src/knowledge/enrich_concepts.py` | New: main enrichment runner (batching, LLM calls, DB writes) |
| `src/knowledge/verify_enrichment.py` | New: post-run sanity check |
| `data/extraction/` | Output dir for failed_concepts.json and run logs |

No new tables beyond `concept_facts`. No changes to existing `quote` or `formula` columns.

---

## Special Cases

**Concepts in large Introduction sections (e.g., section 14.1 with 79 concepts):** The section text covers many topics. The name-match search (`LIKE '%concept_name%'`) is critical here to pull relevant paragraphs out of a noisy section. The LLM prompt should include only the name-matched paragraphs plus the first 5 section paragraphs for context.

**Concepts whose name is short/generic (e.g., "bias", "variance"):** The LIKE search will return too many paragraphs. Cap at 30 paragraphs, sorted by page_number, and include the section-local paragraphs first.

**Equation paragraphs:** These are often formula fragments (e.g., "β̂ridge = ..."). They matter but are hard to quote as standalone facts. The LLM should combine equation paragraphs with adjacent narrative paragraphs to form a complete fact statement — but quote only from the narrative that describes the formula, not the raw equation block.

**Concepts with 0 linked section paragraphs (should not happen — all 670 have section_id):** Log and skip. These are orphaned concepts and should be investigated separately.

---

## Success Criteria

- >= 90% of 670 concepts (603+) have at least 3 facts in `concept_facts`
- All fact_text values are verifiable substrings of DB paragraphs or near-verbatim
- `importance_rank = 1` fact for each concept is the definition or most central property
- Run completes in < 10 minutes end-to-end
- Re-running is safe (idempotent)
