# High-Level Goals (Checkpoint: 2026-02-16)

## Current State
- 670 concepts, 580 relationships, 324 sections
- Interactive Cytoscape.js knowledge graph at output/knowledge-graph/
- Heuristic + agent extraction pipeline complete for ESL

## Goal 1: Chapter-Organized Prerequisite Navigation
**Priority: P0 — foundational for the user's core use case**

Someone reading a later chapter should systematically identify prior concepts they need if they have holes, without reading the entire book.

Design: Rectangle per chapter, lined up linearly, each containing its concepts. Edges show relationships across chapters. Filterable by relationship type (default: prerequisites only).

Prereq: Every concept must be assigned to a chapter first.

## Goal 2: Assign All Concepts to Chapters
**Priority: P0 — blocks Goal 1**

615 of 670 concepts lack section_id. Approach:
1. Page-based heuristic: use paragraph_ids from extraction results → pages → chapters
2. Agents fill gaps (~400+ without paragraph links)
3. During agent pass: select best quote per concept + simple end-result formulas

## Goal 3: 3D Interactive Visual for Every Concept
**Priority: P1**

Every concept gets an interactive 3D visualization. Most stats/ML concepts are easy to comprehend visually.

Tech mix:
- Plotly.js for statistical concepts (bias-variance surfaces, loss landscapes, regularization paths)
- Three.js for geometric concepts (separating hyperplanes, decision boundaries, manifolds)

Scale: ~670 concepts. Need templates/generators, not hand-crafted.

## Goal 4: Curate Best Quotes and Key Formulas
**Priority: P1 — can combine with Goal 2 agent pass**

Each concept gets:
- The single most useful exact quote from ESL
- Simple end-result formula when relevant (cheat-sheet style, not derivations)

## Resolved Decisions
- 3D tech: Plotly for stats + Three.js for geometry
- Prereq view: filterable by relationship type, default prerequisites
- Chapter assignment: page heuristic first, agents fill gaps
- Agents also pick best quotes + formulas during chapter assignment pass
