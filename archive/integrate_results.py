"""Integrate agent-extracted concepts and relationships into the database."""

import json
import sys
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager, Concept, ConceptRelationship

# --- Config ---
RESULTS_DIR = Path(__file__).parent / "extraction"
DB_PATH = Path("data/textbooks.db")
NUM_FILES = 14

VALID_REL_TYPES = {
    "prerequisite", "generalizes", "special_case_of",
    "proved_by", "example_of", "contrasts_with", "uses"
}
REL_TYPE_MAP = {
    "equivalent_to": "uses",
}

GENERIC_SINGLES = {
    "error", "model", "data", "variable", "parameter", "estimate",
    "function", "method", "matrix", "vector", "coefficient", "prediction",
    "distribution", "sample", "population", "hypothesis", "statistic",
    "probability", "variance", "mean", "regression", "classification",
    "feature", "response", "predictor", "observation", "training",
    "testing", "loss", "risk", "penalty", "constraint", "optimization",
    "convergence", "iteration",
}


def is_garbage(name: str) -> bool:
    """Return True if concept name should be filtered out."""
    n = name.strip().lower()

    if len(n) < 3:
        return True
    if n.startswith("a ") or n.startswith("an "):
        return True
    if "=" in name:
        return True
    if name.count("(") != name.count(")"):
        return True
    if n in GENERIC_SINGLES:
        return True
    if len(n) > 0 and n[0].isdigit() and len(n) > 1 and not n[1].isalnum():
        return True
    if "/" in name:
        return True
    if n.startswith("the ") or n.startswith("this "):
        return True

    return False


def load_and_merge() -> tuple[dict, list]:
    """Load all result files, deduplicate concepts, return (concepts_dict, relationships)."""
    # key: normalized name -> {"name": best_name, "type": ..., "description": ...}
    concepts = {}
    relationships = []

    for i in range(1, NUM_FILES + 1):
        fpath = RESULTS_DIR / f"results_{i}.json"
        if not fpath.exists():
            print(f"WARNING: {fpath} not found, skipping")
            continue
        with open(fpath) as f:
            data = json.load(f)

        for c in data.get("concepts", []):
            norm = c["name"].strip().lower()
            desc = c.get("description", "") or ""
            if norm not in concepts or len(desc) > len(concepts[norm].get("description", "") or ""):
                concepts[norm] = {
                    "name": c["name"].strip(),
                    "type": c.get("type", ""),
                    "description": desc,
                }

        for r in data.get("relationships", []):
            relationships.append(r)

    return concepts, relationships


def main():
    concepts_raw, relationships_raw = load_and_merge()
    print(f"Loaded {len(concepts_raw)} unique concepts (pre-filter) from {NUM_FILES} files")
    print(f"Loaded {len(relationships_raw)} raw relationships")

    # Filter garbage
    garbage_count = 0
    concepts_clean = {}
    for norm, c in concepts_raw.items():
        if is_garbage(c["name"]):
            garbage_count += 1
        else:
            concepts_clean[norm] = c

    print(f"Filtered {garbage_count} garbage concepts, {len(concepts_clean)} remain")

    # Check if Concept model has extraction_method column
    has_extraction_method = hasattr(Concept, "extraction_method")

    # Write to DB
    db = DatabaseManager(db_path=DB_PATH)
    new_count = 0
    existing_count = 0
    concept_id_map = {}  # norm_name -> concept.id

    with db:
        # Get existing concepts first to know what's new
        existing_concepts = {c.name.strip().lower(): c for c in db.get_all_concepts()}

        for norm, c in concepts_clean.items():
            was_existing = norm in existing_concepts
            concept = db.get_or_create_concept(
                name=c["name"],
                description=c["description"],
                category=c["type"] if c["type"] else None,
            )
            concept_id_map[norm] = concept.id

            if was_existing:
                existing_count += 1
            else:
                new_count += 1
                if has_extraction_method:
                    concept.extraction_method = "llm"

        print(f"\nConcepts: {new_count} new, {existing_count} already existed")

        # Deduplicate relationships and write
        rel_added = 0
        rel_skipped_missing = 0
        rel_skipped_type = 0
        seen_rels = set()

        for r in relationships_raw:
            src_norm = r["source"].strip().lower()
            tgt_norm = r["target"].strip().lower()
            rtype = r.get("type", "").strip().lower()

            # Map relationship type
            rtype = REL_TYPE_MAP.get(rtype, rtype)
            if rtype not in VALID_REL_TYPES:
                rel_skipped_type += 1
                continue

            src_id = concept_id_map.get(src_norm)
            tgt_id = concept_id_map.get(tgt_norm)

            if not src_id or not tgt_id:
                rel_skipped_missing += 1
                continue

            if src_id == tgt_id:
                continue

            rel_key = (src_id, tgt_id, rtype)
            if rel_key in seen_rels:
                continue
            seen_rels.add(rel_key)

            db.add_concept_relationship(src_id, tgt_id, rtype)
            rel_added += 1

        print(f"Relationships: {rel_added} added, {rel_skipped_missing} skipped (concept not found), {rel_skipped_type} skipped (invalid type)")

    print(f"\nDone. Total concepts in DB now: {new_count + existing_count + (len(existing_concepts) - existing_count)}")


if __name__ == "__main__":
    main()
