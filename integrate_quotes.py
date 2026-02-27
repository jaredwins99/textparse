"""Integrate curated quotes and formulas into the database."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "textbooks.db"
QUOTES_DIR = Path(__file__).parent / "data" / "extraction"


def add_columns_if_needed(conn):
    """Add quote and formula columns to concepts table if they don't exist."""
    c = conn.cursor()

    # Check if columns exist
    c.execute("PRAGMA table_info(concepts)")
    columns = [row[1] for row in c.fetchall()]

    if "quote" not in columns:
        print("Adding 'quote' column to concepts table...")
        c.execute("ALTER TABLE concepts ADD COLUMN quote TEXT")
    else:
        print("Column 'quote' already exists")

    if "formula" not in columns:
        print("Adding 'formula' column to concepts table...")
        c.execute("ALTER TABLE concepts ADD COLUMN formula TEXT")
    else:
        print("Column 'formula' already exists")

    conn.commit()


def load_all_quotes():
    """Load and merge all 6 quote files."""
    all_quotes = []
    for i in range(1, 7):
        file_path = QUOTES_DIR / f"quotes_{i}.json"
        if file_path.exists():
            with open(file_path) as f:
                data = json.load(f)
                all_quotes.extend(data)
                print(f"Loaded {len(data)} entries from {file_path.name}")
        else:
            print(f"Warning: {file_path} not found")

    return all_quotes


def update_concepts(conn, quotes_data):
    """Update concepts with quotes and formulas."""
    c = conn.cursor()

    # Get all concepts for name matching
    c.execute("SELECT id, name FROM concepts")
    concepts = {row[0]: row[1] for row in c.fetchall()}
    name_to_id = {name.lower(): id for id, name in concepts.items()}

    stats = {
        "total": len(quotes_data),
        "matched_by_id": 0,
        "matched_by_name": 0,
        "no_match": 0,
        "quotes_added": 0,
        "formulas_added": 0,
    }

    for entry in quotes_data:
        concept_id = entry.get("concept_id")
        name = entry.get("name")
        quote = entry.get("best_quote")
        formula = entry.get("formula")

        # Try to match by ID first
        matched_id = None
        if concept_id and concept_id in concepts:
            matched_id = concept_id
            stats["matched_by_id"] += 1
        elif name:
            # Fallback to case-insensitive name matching
            matched_id = name_to_id.get(name.lower())
            if matched_id:
                stats["matched_by_name"] += 1

        if matched_id:
            # Update the concept
            c.execute("""
                UPDATE concepts
                SET quote = ?, formula = ?
                WHERE id = ?
            """, (quote, formula, matched_id))

            if quote:
                stats["quotes_added"] += 1
            if formula:
                stats["formulas_added"] += 1
        else:
            stats["no_match"] += 1
            if concept_id or name:
                print(f"No match for concept_id={concept_id}, name={name}")

    conn.commit()
    return stats


def main():
    print("Starting quote integration...")
    print()

    # Connect to database
    conn = sqlite3.connect(str(DB_PATH))

    # Step 1: Add columns
    add_columns_if_needed(conn)
    print()

    # Step 2: Load quotes
    quotes_data = load_all_quotes()
    print(f"\nTotal entries loaded: {len(quotes_data)}")
    print()

    # Step 3: Update concepts
    print("Updating concepts...")
    stats = update_concepts(conn, quotes_data)

    conn.close()

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total entries processed:     {stats['total']}")
    print(f"Matched by concept_id:       {stats['matched_by_id']}")
    print(f"Matched by name (fallback):  {stats['matched_by_name']}")
    print(f"No match found:              {stats['no_match']}")
    print()
    print(f"Quotes added:                {stats['quotes_added']}")
    print(f"Formulas added:              {stats['formulas_added']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
