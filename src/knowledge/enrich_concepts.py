"""Prepare enrichment batches: concepts + their relevant paragraphs."""

import json
import sqlite3
import sys
from pathlib import Path

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "paragraph_fetcher", Path(__file__).parent / "paragraph_fetcher.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
fetch_context_for_concept = _mod.fetch_context_for_concept

DB_PATH = Path(__file__).parent.parent.parent / "data" / "textbooks.db"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "extraction" / "enrichment"
BATCH_SIZE = 20


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Get concepts that don't have facts yet
    existing_facts = set()
    for row in cur.execute("SELECT DISTINCT concept_id FROM concept_facts"):
        existing_facts.add(row[0])

    concepts = []
    for row in cur.execute(
        "SELECT id, name, description, new_category, subcategory, quote, formula, section_id "
        "FROM concepts ORDER BY section_id, id"
    ):
        if row[0] in existing_facts:
            continue
        concepts.append({
            "id": row[0], "name": row[1], "description": row[2],
            "category": row[3], "subcategory": row[4],
            "existing_quote": row[5], "existing_formula": row[6],
            "section_id": row[7]
        })

    print(f"Concepts to enrich: {len(concepts)} (skipping {len(existing_facts)} with existing facts)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Batch concepts, grouped by section where possible
    batches = []
    current_batch = []
    for concept in concepts:
        current_batch.append(concept)
        if len(current_batch) >= BATCH_SIZE:
            batches.append(current_batch)
            current_batch = []
    if current_batch:
        batches.append(current_batch)

    print(f"Created {len(batches)} batches")

    # For each batch, fetch paragraphs and write to JSON
    for i, batch in enumerate(batches):
        batch_data = {"batch_number": i + 1, "concepts": []}
        for concept in batch:
            paragraphs, name = fetch_context_for_concept(conn, concept["id"])
            # Truncate very long paragraph lists to save space
            if len(paragraphs) > 30:
                paragraphs = paragraphs[:30]
            batch_data["concepts"].append({
                "id": concept["id"],
                "name": concept["name"],
                "description": concept["description"] or "",
                "category": concept["category"] or "",
                "subcategory": concept["subcategory"] or "",
                "existing_quote": concept["existing_quote"] or "",
                "existing_formula": concept["existing_formula"] or "",
                "paragraphs": paragraphs,
            })

        output_path = OUTPUT_DIR / f"batch_{i + 1}.json"
        with open(output_path, "w") as f:
            json.dump(batch_data, f, indent=2)

        total_paras = sum(len(c["paragraphs"]) for c in batch_data["concepts"])
        print(f"  Batch {i + 1}: {len(batch_data['concepts'])} concepts, {total_paras} paragraphs")

    conn.close()
    print(f"\nBatches written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
