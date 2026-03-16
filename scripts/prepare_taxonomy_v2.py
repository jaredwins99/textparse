"""Prepare batch inputs for revised taxonomy reclassification."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "textbooks.db"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "extraction" / "taxonomy_v2"

BATCH_SIZE = 96


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT c.id, c.name, c.description, c.category, c.new_category, c.subcategory,
               s.number as section_number, s.title as section_title
        FROM concepts c
        LEFT JOIN sections s ON c.section_id = s.id
        ORDER BY c.id
    """)
    rows = cur.fetchall()
    conn.close()

    concepts = []
    for row in rows:
        section = f"{row['section_number']} {row['section_title']}" if row["section_number"] else ""
        concepts.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"] or "",
            "section": section,
            "old_category": row["new_category"] or row["category"] or "",
            "old_subcategory": row["subcategory"] or "",
        })

    # Write batches
    batch_num = 1
    for i in range(0, len(concepts), BATCH_SIZE):
        batch = concepts[i:i + BATCH_SIZE]
        path = OUTPUT_DIR / f"input-{batch_num}.json"
        with open(path, "w") as f:
            json.dump(batch, f, indent=2)
        print(f"  Batch {batch_num}: {len(batch)} concepts (ids {batch[0]['id']}-{batch[-1]['id']})")
        batch_num += 1

    print(f"\nTotal: {len(concepts)} concepts in {batch_num - 1} batches at {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
