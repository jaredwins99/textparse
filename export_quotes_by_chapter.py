#!/usr/bin/env python3
"""
Export concepts grouped by chapter for quote/formula curation pass.
Loads extraction results and maps quotes to concepts by name.
Splits into 6 batches of ~3 chapters each.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from sqlalchemy import create_engine, text

sys.path.insert(0, '/home/godli/textparse')

# Database setup
engine = create_engine('sqlite:////home/godli/textparse/data/textbooks.db')

# Paths
DATA_DIR = Path('/home/godli/textparse/data')
EXTRACTION_DIR = Path('/home/godli/textparse/archive/extraction')
OUTPUT_DIR = DATA_DIR / 'extraction'

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_extraction_quotes():
    """Load all extraction results and build a name -> quote map."""
    quotes_map = {}

    # Find all results_*.json files
    results_files = sorted(EXTRACTION_DIR.glob('results_*.json'))

    for results_file in results_files:
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)

            # data is a list of concepts with quotes
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'name' in item:
                        # Normalize name to lowercase for matching
                        name = item['name'].lower().strip()
                        if 'quote' in item and item['quote']:
                            quotes_map[name] = item['quote']
        except Exception as e:
            print(f"Warning: Failed to load {results_file}: {e}")

    return quotes_map


def get_chapter_from_section_id(conn, section_id):
    """Get the chapter number from a section_id by traversing up the hierarchy."""
    if not section_id:
        return None

    # Get the section's number
    result = conn.execute(
        text("SELECT number FROM sections WHERE id = :id"),
        {"id": section_id}
    )
    row = result.first()
    if not row or not row[0]:
        return None

    number = row[0]
    # Extract chapter number (first digit)
    chapter = number.split('.')[0]
    try:
        return int(chapter)
    except ValueError:
        return None


def load_concepts(conn, quotes_map):
    """Load all concepts from database, grouped by chapter."""
    concepts_by_chapter = defaultdict(list)

    result = conn.execute(
        text("""
            SELECT id, name, description, section_id
            FROM concepts
            ORDER BY id
        """)
    )

    for row in result:
        concept_id, name, description, section_id = row

        # Get chapter number
        chapter = get_chapter_from_section_id(conn, section_id)
        if chapter is None:
            chapter = 0  # Unassigned

        # Look up existing quote
        name_key = name.lower().strip()
        existing_quote = quotes_map.get(name_key)

        concept = {
            "id": concept_id,
            "name": name,
            "chapter": chapter,
            "description": description or "",
            "existing_quote": existing_quote
        }

        concepts_by_chapter[chapter].append(concept)

    return concepts_by_chapter


def create_batches(concepts_by_chapter, num_batches=6):
    """
    Split chapters into num_batches groups.
    Each batch contains ~3 chapters.
    """
    # Get sorted chapter numbers
    chapters = sorted(k for k in concepts_by_chapter.keys() if k > 0)

    # Calculate chapters per batch
    chapters_per_batch = max(1, len(chapters) // num_batches)

    batches = []
    for batch_id in range(1, num_batches + 1):
        start_idx = (batch_id - 1) * chapters_per_batch
        if batch_id == num_batches:
            # Last batch gets remaining chapters
            batch_chapters = chapters[start_idx:]
        else:
            batch_chapters = chapters[start_idx:start_idx + chapters_per_batch]

        # Collect all concepts for these chapters
        batch_concepts = []
        for chapter in batch_chapters:
            batch_concepts.extend(concepts_by_chapter[chapter])

        # Sort by chapter and id within batch
        batch_concepts.sort(key=lambda x: (x['chapter'], x['id']))

        batch = {
            "batch_id": batch_id,
            "chapters": batch_chapters,
            "concepts": batch_concepts
        }
        batches.append(batch)

    return batches


def main():
    print("Loading extraction results...")
    quotes_map = load_extraction_quotes()
    print(f"  Loaded quotes for {len(quotes_map)} concepts")

    with engine.connect() as conn:
        print("Loading concepts from database...")
        concepts_by_chapter = load_concepts(conn, quotes_map)

        # Count total concepts
        total_concepts = sum(len(v) for v in concepts_by_chapter.values())
        print(f"  Loaded {total_concepts} concepts across {len([k for k in concepts_by_chapter.keys() if k > 0])} chapters")

        # Check for unassigned concepts
        unassigned = concepts_by_chapter.get(0, [])
        if unassigned:
            print(f"  Warning: {len(unassigned)} concepts have no chapter assignment")

        # Create batches
        print("Creating batches...")
        batches = create_batches(concepts_by_chapter, num_batches=6)

        # Write batch files
        for batch in batches:
            output_file = OUTPUT_DIR / f"quote_batch_{batch['batch_id']}.json"
            with open(output_file, 'w') as f:
                json.dump(batch, f, indent=2)

            concept_count = len(batch['concepts'])
            chapter_list = ', '.join(map(str, batch['chapters']))
            print(f"  Batch {batch['batch_id']}: {concept_count} concepts (chapters {chapter_list})")
            print(f"    -> {output_file}")

    print("\nDone! Created 6 batch files ready for quote curation.")


if __name__ == '__main__':
    main()
