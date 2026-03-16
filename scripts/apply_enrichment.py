"""Apply enrichment results to the concept_facts table."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "textbooks.db"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "extraction" / "enrichment"

VALID_FACT_TYPES = {"definition", "formula", "property", "comparison", "intuition", "example"}


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Get existing concept IDs for validation
    valid_concept_ids = set()
    for row in cur.execute("SELECT id FROM concepts"):
        valid_concept_ids.add(row[0])

    # Get already-enriched concepts to avoid duplicates
    already_enriched = set()
    for row in cur.execute("SELECT DISTINCT concept_id FROM concept_facts"):
        already_enriched.add(row[0])

    total_facts = 0
    total_concepts = 0
    skipped = 0
    invalid = 0

    for results_path in sorted(RESULTS_DIR.glob("results_*.json")):
        with open(results_path) as f:
            data = json.load(f)

        batch_num = results_path.stem.split("_")[1]
        batch_facts = 0

        for concept_entry in data:
            cid = concept_entry["concept_id"]

            if cid in already_enriched:
                skipped += 1
                continue

            if cid not in valid_concept_ids:
                print(f"  WARNING: concept_id {cid} not in DB, skipping")
                invalid += 1
                continue

            for fact in concept_entry.get("facts", []):
                fact_text = fact.get("fact_text", "").strip()
                if not fact_text or len(fact_text) < 10:
                    continue

                fact_type = fact.get("fact_type", "property")
                if fact_type not in VALID_FACT_TYPES:
                    fact_type = "property"

                cur.execute(
                    "INSERT INTO concept_facts (concept_id, fact_text, fact_type, importance_rank, page_number, paragraph_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        cid,
                        fact_text,
                        fact_type,
                        fact.get("importance_rank", 99),
                        fact.get("page_number"),
                        fact.get("paragraph_id"),
                    )
                )
                batch_facts += 1

            total_concepts += 1

        total_facts += batch_facts
        print(f"  Results {batch_num}: {batch_facts} facts from {len(data)} concepts")

    conn.commit()

    # Final stats
    total_in_db = cur.execute("SELECT COUNT(*) FROM concept_facts").fetchone()[0]
    concepts_with_facts = cur.execute("SELECT COUNT(DISTINCT concept_id) FROM concept_facts").fetchone()[0]
    total_concepts_db = cur.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]

    print(f"\nInserted: {total_facts} facts for {total_concepts} concepts (skipped {skipped} already enriched, {invalid} invalid)")
    print(f"DB state: {total_in_db} facts total, {concepts_with_facts}/{total_concepts_db} concepts have facts")

    # Distribution by fact_type
    print("\nFact type distribution:")
    for row in cur.execute("SELECT fact_type, COUNT(*) FROM concept_facts GROUP BY fact_type ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    main()
