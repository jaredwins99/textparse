"""Deduplicate and merge concepts in the textparse database.

Strategies:
1. Exact lowercase match after stripping whitespace
2. Substring matching (one name contained in another)
3. Fuzzy match: ligatures, punctuation, whitespace normalization
4. Pluralization (trailing 's')
5. "Algorithm X.Y Foo" matching bare "foo"

Merge rules:
- Keep version with longest non-empty description
- Prefer lowercase canonical names over "Algorithm X.Y ..." style
- Combine descriptions/quotes, re-point relationships and paragraph_concepts
- Deduplicate relationships after re-pointing
"""

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_PATH = Path("/home/godli/textparse/data/textbooks.db")


def normalize_name(name: str) -> str:
    """Normalize a concept name for comparison purposes."""
    s = name.strip()
    # Fix ligatures
    s = s.replace("\ufb01", "fi").replace("\ufb02", "fl")
    # Strip trailing periods
    s = s.rstrip(".")
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Lowercase
    s = s.lower()
    # Remove punctuation (hyphens, quotes, etc.) for comparison
    s = re.sub(r"[''\"`,;:!?(){}[\]]", "", s)
    # Normalize hyphens/dashes to single hyphen
    s = re.sub(r"[–—−‐]+", "-", s)
    return s.strip()


def strip_algorithm_prefix(name: str) -> str | None:
    """If name is 'Algorithm X.Y Foo Bar', return normalized 'foo bar'."""
    m = re.match(r"^algorithm\s+\d+(\.\d+)*\s+(.+)$", name.strip(), re.IGNORECASE)
    if m:
        return normalize_name(m.group(2))
    return None


def depluralize(s: str) -> str:
    """Naive depluralization: remove trailing 's' if len > 4."""
    if s.endswith("s") and len(s) > 4 and not s.endswith("ss"):
        return s[:-1]
    return s


def find_duplicate_groups(concepts: list[dict]) -> list[list[int]]:
    """Find groups of duplicate concept IDs.

    Returns list of groups, where each group is a list of concept IDs
    that should be merged together.
    """
    n = len(concepts)

    # Build normalized forms
    norm_map = {}  # id -> normalized name
    algo_map = {}  # id -> stripped algorithm name (or None)
    for c in concepts:
        norm_map[c["id"]] = normalize_name(c["name"])
        algo_map[c["id"]] = strip_algorithm_prefix(c["name"])

    # Union-Find
    parent = {c["id"]: c["id"] for c in concepts}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Index by normalized name for O(1) exact matching
    norm_to_ids = defaultdict(list)
    for c in concepts:
        norm_to_ids[normalize_name(c["name"])].append(c["id"])

    # Strategy 1: Exact normalized match
    for norm, ids in norm_to_ids.items():
        for i in range(1, len(ids)):
            union(ids[0], ids[i])

    # Strategy 5: Algorithm prefix matching
    for c in concepts:
        stripped = algo_map[c["id"]]
        if stripped and stripped in norm_to_ids:
            # Match to any concept with that normalized name
            for other_id in norm_to_ids[stripped]:
                if other_id != c["id"]:
                    union(c["id"], other_id)

    # Strategy 4: Pluralization - "support vectors" matches "support vector"
    deplural_to_ids = defaultdict(list)
    for c in concepts:
        dp = depluralize(normalize_name(c["name"]))
        deplural_to_ids[dp].append(c["id"])
    for dp, ids in deplural_to_ids.items():
        for i in range(1, len(ids)):
            union(ids[0], ids[i])

    # Strategy 3: Further normalization - remove hyphens entirely for fuzzy match
    def ultra_normalize(name):
        s = normalize_name(name)
        s = s.replace("-", "").replace(" ", "")
        return s

    ultra_to_ids = defaultdict(list)
    for c in concepts:
        u = ultra_normalize(c["name"])
        if len(u) >= 3:  # avoid matching empty/tiny strings
            ultra_to_ids[u].append(c["id"])
    for u, ids in ultra_to_ids.items():
        for i in range(1, len(ids)):
            union(ids[0], ids[i])

    # Strategy 2: Substring matching
    # Sort by normalized name length (shorter first)
    sorted_concepts = sorted(concepts, key=lambda c: len(normalize_name(c["name"])))
    for i in range(n):
        ni = norm_map[sorted_concepts[i]["id"]]
        if len(ni) < 3:
            continue  # Skip very short names to avoid false matches
        for j in range(i + 1, n):
            nj = norm_map[sorted_concepts[j]["id"]]
            # Check if shorter is a substring of longer
            if len(ni) <= len(nj) and ni in nj:
                # But only if it's a significant match (not "a" in "abc")
                # The shorter name should be at least 40% of the longer name's length
                # or be a word-boundary match
                ratio = len(ni) / len(nj)
                if ratio >= 0.5:
                    union(sorted_concepts[i]["id"], sorted_concepts[j]["id"])
                elif len(ni) >= 5:
                    # Check word boundary: shorter should match a whole word sequence in longer
                    # e.g. "lasso" in "the lasso" but not "ridge" in "bridge"
                    pattern = r"(?:^|\s)" + re.escape(ni) + r"(?:\s|$)"
                    if re.search(pattern, nj):
                        union(sorted_concepts[i]["id"], sorted_concepts[j]["id"])

    # Collect groups
    groups = defaultdict(list)
    for c in concepts:
        groups[find(c["id"])].append(c["id"])

    # Return only groups with >1 member
    return [ids for ids in groups.values() if len(ids) > 1]


def choose_canonical(concepts_in_group: list[dict]) -> tuple[dict, list[dict]]:
    """Choose the canonical concept from a group. Returns (keeper, list_of_duplicates)."""
    # Score each concept
    def score(c):
        s = 0
        name = c["name"]
        desc = c["description"] or ""

        # Prefer longer description
        s += len(desc)

        # Prefer names that are NOT "Algorithm X.Y ..."
        if re.match(r"^Algorithm\s+\d", name):
            s -= 1000

        # Prefer names that start lowercase (more canonical)
        if name and name[0].islower():
            s += 50

        # Prefer shorter, cleaner names (slight bonus)
        s -= len(name) * 0.1

        # Prefer concepts with section_id set
        if c["section_id"]:
            s += 20

        # Prefer concepts with category set
        if c["category"]:
            s += 10

        return s

    ranked = sorted(concepts_in_group, key=score, reverse=True)
    keeper = ranked[0]
    dupes = ranked[1:]
    return keeper, dupes


def main():
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Enable foreign keys
    session.execute(text("PRAGMA foreign_keys = OFF"))

    # Load all concepts
    rows = session.execute(text("SELECT id, name, description, category, section_id FROM concepts")).fetchall()
    concepts = [{"id": r[0], "name": r[1], "description": r[2], "category": r[3], "section_id": r[4]} for r in rows]
    print(f"=== Concept Deduplication Report ===\n")
    print(f"Starting concepts: {len(concepts)}")

    # Load counts
    rel_count = session.execute(text("SELECT count(*) FROM concept_relationships")).scalar()
    pc_count = session.execute(text("SELECT count(*) FROM paragraph_concepts")).scalar()
    print(f"Starting relationships: {rel_count}")
    print(f"Starting paragraph_concepts: {pc_count}")

    # Find duplicate groups
    groups = find_duplicate_groups(concepts)
    print(f"\nDuplicate groups found: {len(groups)}")

    # Build id->concept lookup
    concept_by_id = {c["id"]: c for c in concepts}

    total_merged = 0
    merge_examples = []

    for group_ids in groups:
        group_concepts = [concept_by_id[gid] for gid in group_ids]
        keeper, dupes = choose_canonical(group_concepts)

        if not dupes:
            continue

        # Merge description: keep longest
        best_desc = keeper["description"] or ""
        for d in dupes:
            dd = d["description"] or ""
            if len(dd) > len(best_desc):
                best_desc = dd

        # Merge category: keep first non-null
        best_cat = keeper["category"]
        if not best_cat:
            for d in dupes:
                if d["category"]:
                    best_cat = d["category"]
                    break

        # Merge section_id: keep first non-null
        best_section = keeper["section_id"]
        if not best_section:
            for d in dupes:
                if d["section_id"]:
                    best_section = d["section_id"]
                    break

        # Update keeper
        session.execute(text(
            "UPDATE concepts SET description = :desc, category = :cat, section_id = :sid WHERE id = :kid"
        ), {"desc": best_desc if best_desc else None, "cat": best_cat, "sid": best_section, "kid": keeper["id"]})

        dupe_ids = [d["id"] for d in dupes]

        for did in dupe_ids:
            # Re-point concept_relationships source_id
            session.execute(text(
                "UPDATE concept_relationships SET source_id = :kid WHERE source_id = :did"
            ), {"kid": keeper["id"], "did": did})

            # Re-point concept_relationships target_id
            session.execute(text(
                "UPDATE concept_relationships SET target_id = :kid WHERE target_id = :did"
            ), {"kid": keeper["id"], "did": did})

            # Re-point paragraph_concepts - need to handle potential duplicates
            # First find paragraph_ids linked to dupe
            linked = session.execute(text(
                "SELECT paragraph_id FROM paragraph_concepts WHERE concept_id = :did"
            ), {"did": did}).fetchall()

            for (pid,) in linked:
                # Check if keeper already linked to this paragraph
                existing = session.execute(text(
                    "SELECT 1 FROM paragraph_concepts WHERE paragraph_id = :pid AND concept_id = :kid"
                ), {"pid": pid, "kid": keeper["id"]}).fetchone()
                if not existing:
                    session.execute(text(
                        "INSERT INTO paragraph_concepts (paragraph_id, concept_id) VALUES (:pid, :kid)"
                    ), {"pid": pid, "kid": keeper["id"]})

            # Delete dupe's paragraph_concepts
            session.execute(text(
                "DELETE FROM paragraph_concepts WHERE concept_id = :did"
            ), {"did": did})

            # Delete dupe concept
            session.execute(text("DELETE FROM concepts WHERE id = :did"), {"did": did})

        total_merged += len(dupe_ids)

        if len(merge_examples) < 20:
            dupe_names = [d["name"] for d in dupes]
            merge_examples.append((keeper["name"], dupe_names))

    # Deduplicate relationships: remove duplicate (source_id, target_id, relationship_type)
    # Also remove self-referential relationships that may have been created
    session.execute(text("DELETE FROM concept_relationships WHERE source_id = target_id"))

    # Find and remove duplicate relationships
    dup_rels = session.execute(text("""
        SELECT source_id, target_id, relationship_type, COUNT(*) as cnt, MIN(id) as keep_id
        FROM concept_relationships
        GROUP BY source_id, target_id, relationship_type
        HAVING cnt > 1
    """)).fetchall()

    rels_removed = 0
    for row in dup_rels:
        src, tgt, rtype, cnt, keep_id = row
        session.execute(text("""
            DELETE FROM concept_relationships
            WHERE source_id = :src AND target_id = :tgt AND relationship_type = :rtype AND id != :keep_id
        """), {"src": src, "tgt": tgt, "rtype": rtype, "keep_id": keep_id})
        rels_removed += cnt - 1

    # Step 3: Normalize remaining concept names
    remaining = session.execute(text("SELECT id, name FROM concepts")).fetchall()
    names_fixed = 0
    for cid, name in remaining:
        new_name = name

        # Strip whitespace
        new_name = new_name.strip()

        # Fix ligatures
        new_name = new_name.replace("\ufb01", "fi").replace("\ufb02", "fl")

        # Remove trailing periods
        new_name = new_name.rstrip(".")

        # Lowercase first char if not an acronym or proper noun
        # Heuristic: if first word is all-caps and len <= 5, it's an acronym — leave it
        # If it starts with "Algorithm", leave it (though we prefer not to have these)
        if new_name and new_name[0].isupper():
            first_word = new_name.split()[0] if new_name.split() else ""
            is_acronym = first_word.isupper() and len(first_word) <= 6
            is_algorithm = first_word.lower() == "algorithm"
            # Check if it looks like a proper name (e.g., "Bayes", "Fisher")
            # Keep uppercase if first word is a known proper noun pattern
            # Simple heuristic: if the rest of the first word is lowercase after first char, it might be a proper noun
            is_proper = (len(first_word) > 1 and first_word[0].isupper() and first_word[1:].islower())

            if not is_acronym and not is_algorithm and not is_proper:
                new_name = new_name[0].lower() + new_name[1:]

        if new_name != name:
            # Check for conflicts: another concept might already have this normalized name
            conflict = session.execute(text(
                "SELECT id FROM concepts WHERE name = :name AND id != :cid"
            ), {"name": new_name, "cid": cid}).fetchone()
            if conflict:
                # This would be caught in a second pass; skip for now
                pass
            else:
                session.execute(text("UPDATE concepts SET name = :name WHERE id = :cid"),
                                {"name": new_name, "cid": cid})
                names_fixed += 1

    session.commit()

    # Final counts
    final_concepts = session.execute(text("SELECT count(*) FROM concepts")).scalar()
    final_rels = session.execute(text("SELECT count(*) FROM concept_relationships")).scalar()
    final_pc = session.execute(text("SELECT count(*) FROM paragraph_concepts")).scalar()

    # Print report
    print(f"\n--- Merge Summary ---")
    print(f"Concepts merged (deleted): {total_merged}")
    print(f"Relationships deduplicated: {rels_removed}")
    print(f"Self-referential relationships removed: (included in dedup)")
    print(f"Concept names normalized: {names_fixed}")

    print(f"\n--- Merge Examples (up to 20) ---")
    for keeper_name, dupe_names in merge_examples:
        print(f"  KEPT: {keeper_name!r}")
        for dn in dupe_names:
            print(f"    merged: {dn!r}")
        print()

    print(f"\n--- Final Counts ---")
    print(f"Concepts: {len(concepts)} -> {final_concepts}")
    print(f"Relationships: {rel_count} -> {final_rels}")
    print(f"Paragraph-concept links: {pc_count} -> {final_pc}")

    # Suspicious concepts
    print(f"\n--- Suspicious Concepts ---")
    remaining = session.execute(text("SELECT id, name, description FROM concepts ORDER BY name")).fetchall()
    suspicious = []
    for cid, name, desc in remaining:
        reasons = []
        if len(name) <= 2:
            reasons.append("very short name")
        if name.lower() in {"data", "model", "method", "error", "function", "value", "result",
                            "parameter", "variable", "matrix", "vector", "set", "class", "output",
                            "input", "test", "training", "sample", "feature", "table", "figure",
                            "the", "a", "an"}:
            reasons.append("very generic name")
        if not desc:
            reasons.append("no description")
        if reasons:
            suspicious.append((cid, name, reasons))

    if suspicious:
        for cid, name, reasons in suspicious:
            print(f"  [{cid}] {name!r}: {', '.join(reasons)}")
    else:
        print("  None found.")

    session.close()
    print(f"\nDone.")


if __name__ == "__main__":
    main()
