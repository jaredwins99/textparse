"""Apply taxonomy batch results to the database."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "textbooks.db"
TAXONOMY_DIR = Path(__file__).parent.parent / "data" / "extraction" / "taxonomy"

VALID_CATEGORIES = {"model", "estimation", "validation", "guarantees", "multi_model", "improvements"}
VALID_SUBCATEGORIES = {
    "model": {"dgp", "pseudo_model"},
    "estimation": {"criteria", "optimization"},
    "validation": {"diagnostics", "validation"},
    "guarantees": {"assumptions", "guarantees"},
    "multi_model": {"selection", "aggregating"},
    "improvements": {"preprocessing", "efficiencies"},
}


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    total = 0
    invalid = 0
    applied = 0

    for batch_num in range(1, 8):
        batch_path = TAXONOMY_DIR / f"batch-{batch_num}.json"
        if not batch_path.exists():
            print(f"  Batch {batch_num}: NOT FOUND")
            continue

        with open(batch_path) as f:
            data = json.load(f)

        print(f"  Batch {batch_num}: {len(data)} concepts")
        total += len(data)

        for item in data:
            cid = item["id"]
            new_cat = item["new_category"]
            subcat = item["subcategory"]

            if new_cat not in VALID_CATEGORIES:
                print(f"    INVALID category '{new_cat}' for concept {cid}")
                invalid += 1
                continue
            if subcat not in VALID_SUBCATEGORIES.get(new_cat, set()):
                print(f"    INVALID subcategory '{subcat}' for category '{new_cat}', concept {cid}")
                invalid += 1
                continue

            cur.execute(
                "UPDATE concepts SET new_category = ?, subcategory = ? WHERE id = ?",
                (new_cat, subcat, cid)
            )
            applied += 1

    conn.commit()
    conn.close()

    print(f"\nTotal: {total}, Applied: {applied}, Invalid: {invalid}")

    # Verify
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    assigned = cur.execute("SELECT COUNT(*) FROM concepts WHERE new_category IS NOT NULL").fetchone()[0]
    total_concepts = cur.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    print(f"DB state: {assigned}/{total_concepts} concepts have new_category")

    print("\nDistribution:")
    for row in cur.execute(
        "SELECT new_category, subcategory, COUNT(*) FROM concepts "
        "WHERE new_category IS NOT NULL GROUP BY new_category, subcategory ORDER BY new_category, subcategory"
    ):
        print(f"  {row[0]}/{row[1]}: {row[2]}")

    conn.close()


if __name__ == "__main__":
    main()
