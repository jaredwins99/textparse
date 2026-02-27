"""Assign concepts to chapters using batch page ranges and section mappings."""

import json
import os
import sqlite3
from collections import Counter

DB_PATH = "/home/godli/textparse/data/textbooks.db"
EXTRACTION_DIR = "/home/godli/textparse/archive/extraction"
OUTPUT_DIR = "/home/godli/textparse/data/extraction"

def load_sections_from_db(conn):
    """Load all sections from the DB, return list of dicts sorted by page_start."""
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, number, title, page_start, page_end, parent_id FROM sections "
        "WHERE number IS NOT NULL ORDER BY page_start"
    ).fetchall()
    sections = []
    for r in rows:
        sections.append({
            "id": r[0], "number": r[1], "title": r[2],
            "page_start": r[3], "page_end": r[4], "parent_id": r[5]
        })
    return sections


def get_chapter_from_section_number(section_number):
    """Extract chapter number from section number like '3.2.1' -> '3'."""
    if not section_number:
        return None
    return section_number.split(".")[0]


def build_chapter_to_section_map(db_sections):
    """Map chapter number -> list of DB section IDs, and find the 'best' top-level section per chapter."""
    chapter_map = {}  # chapter_num -> first section ID for that chapter
    for s in db_sections:
        ch = get_chapter_from_section_number(s["number"])
        if ch and ch not in chapter_map:
            chapter_map[ch] = s["id"]
    return chapter_map


def find_section_for_page(page_num, db_sections):
    """Find the most specific section whose page_start <= page_num."""
    best = None
    for s in db_sections:
        if s["page_start"] is not None and s["page_start"] <= page_num:
            if best is None or s["page_start"] >= best["page_start"]:
                # Prefer more specific (deeper) sections at the same or later page
                best = s
    return best


def get_chapters_for_batch(batch_data, db_sections):
    """Determine which chapters a batch covers, return list of chapter numbers."""
    sections = batch_data.get("sections", [])
    chapters = set()
    for s in sections:
        ch = get_chapter_from_section_number(s.get("number"))
        if ch:
            chapters.add(ch)
    return sorted(chapters)


def try_find_page_by_quote(conn, quote):
    """Try to find a paragraph matching the quote and return its page number."""
    if not quote or len(quote) < 20:
        return None
    cur = conn.cursor()
    # Search for substring match - use first 60 chars of quote to handle truncation
    search_text = quote[:60].replace("'", "''")
    rows = cur.execute(
        "SELECT p.page_number FROM paragraphs par "
        "JOIN pages p ON par.page_id = p.id "
        "WHERE par.text LIKE ? LIMIT 1",
        (f"%{search_text}%",)
    ).fetchall()
    if rows:
        return rows[0][0]
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    db_sections = load_sections_from_db(conn)
    chapter_to_first_section = build_chapter_to_section_map(db_sections)

    print(f"Loaded {len(db_sections)} sections from DB")
    print(f"Chapter -> first section ID mapping: {chapter_to_first_section}")
    print()

    # Load all concepts from DB
    cur = conn.cursor()
    db_concepts = {}
    for row in cur.execute("SELECT id, name, section_id FROM concepts"):
        db_concepts[row[1].lower().strip()] = {"id": row[0], "name": row[1], "section_id": row[2]}

    print(f"Loaded {len(db_concepts)} concepts from DB")
    already_assigned = sum(1 for c in db_concepts.values() if c["section_id"] is not None)
    print(f"Already assigned: {already_assigned}")
    print()

    # Process each batch/results pair
    assignments = {}  # concept_name_lower -> section_id
    unmatched_in_db = []  # concepts in results but not in DB
    no_chapter = []  # concepts where we can't determine chapter

    for batch_num in range(1, 15):
        batch_path = os.path.join(EXTRACTION_DIR, f"batch_{batch_num}.json")
        results_path = os.path.join(EXTRACTION_DIR, f"results_{batch_num}.json")

        if not os.path.exists(results_path):
            continue

        with open(batch_path) as f:
            batch_data = json.load(f)
        with open(results_path) as f:
            results_data = json.load(f)

        batch_chapters = get_chapters_for_batch(batch_data, db_sections)
        batch_sections = batch_data.get("sections", [])
        page_range = batch_data.get("page_range", "")
        page_start, page_end = [int(x) for x in page_range.split("-")]

        concepts = results_data.get("concepts", [])
        print(f"Batch {batch_num}: pages {page_range}, chapters {batch_chapters}, {len(concepts)} concepts")

        for concept in concepts:
            name_lower = concept["name"].lower().strip()

            if name_lower not in db_concepts:
                unmatched_in_db.append(concept["name"])
                continue

            db_concept = db_concepts[name_lower]

            # Skip if already assigned
            if db_concept["section_id"] is not None:
                continue

            # Strategy 1: If batch covers only one chapter, assign to that chapter
            if len(batch_chapters) == 1:
                ch = batch_chapters[0]
                if ch in chapter_to_first_section:
                    # Try to find a more specific section using quote
                    page = try_find_page_by_quote(conn, concept.get("quote"))
                    if page is not None:
                        section = find_section_for_page(page, db_sections)
                        if section and get_chapter_from_section_number(section["number"]) == ch:
                            assignments[name_lower] = section["id"]
                            continue
                    assignments[name_lower] = chapter_to_first_section[ch]
                continue

            # Strategy 2: Multiple chapters - try to find page via quote
            page = try_find_page_by_quote(conn, concept.get("quote"))
            if page is not None:
                section = find_section_for_page(page, db_sections)
                if section:
                    assignments[name_lower] = section["id"]
                    continue

            # Strategy 3: If we can't find the page, use batch sections to infer
            # For multi-chapter batches, check which sections' page ranges contain
            # this concept. Use the midpoint of the batch as a rough heuristic.
            # Actually, just assign to the chapter that has the most sections in this batch.
            ch_counts = Counter(batch_chapters)
            # Count sections per chapter in this batch
            ch_section_counts = Counter()
            for s in batch_sections:
                ch = get_chapter_from_section_number(s.get("number"))
                if ch:
                    ch_section_counts[ch] += 1

            if ch_section_counts:
                best_ch = ch_section_counts.most_common(1)[0][0]
                if best_ch in chapter_to_first_section:
                    assignments[name_lower] = chapter_to_first_section[best_ch]
                    continue

            no_chapter.append(concept["name"])

    # Apply assignments to DB
    print(f"\n--- Results ---")
    print(f"Assignments to make: {len(assignments)}")
    print(f"Concepts not found in DB: {len(unmatched_in_db)}")
    print(f"Concepts with no chapter resolved: {len(no_chapter)}")

    updated = 0
    for name_lower, section_id in assignments.items():
        db_id = db_concepts[name_lower]["id"]
        cur.execute("UPDATE concepts SET section_id = ? WHERE id = ?", (section_id, db_id))
        updated += 1

    conn.commit()
    print(f"Updated {updated} concepts in DB")

    # Check final state
    total = cur.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    assigned = cur.execute("SELECT COUNT(*) FROM concepts WHERE section_id IS NOT NULL").fetchone()[0]
    unassigned = total - assigned
    print(f"\nFinal state: {assigned}/{total} assigned, {unassigned} unassigned")

    # Collect all unassigned concept names
    unassigned_concepts = []
    for row in cur.execute("SELECT name FROM concepts WHERE section_id IS NULL ORDER BY name"):
        unassigned_concepts.append(row[0])

    # Save unassigned concepts
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "unassigned_concepts.json")
    with open(output_path, "w") as f:
        json.dump({"count": len(unassigned_concepts), "concepts": unassigned_concepts}, f, indent=2)
    print(f"Saved {len(unassigned_concepts)} unassigned concepts to {output_path}")

    # Print chapter distribution
    print("\n--- Chapter distribution of assigned concepts ---")
    rows = cur.execute(
        "SELECT s.number, COUNT(*) FROM concepts c "
        "JOIN sections s ON c.section_id = s.id "
        "GROUP BY s.number ORDER BY s.number"
    ).fetchall()
    for section_num, count in rows:
        print(f"  Section {section_num}: {count} concepts")

    conn.close()


if __name__ == "__main__":
    main()
