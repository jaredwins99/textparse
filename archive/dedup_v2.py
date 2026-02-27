"""
Conservative concept deduplication — v2.

SAFE merges only:
1. Exact case-insensitive match
2. Ligature normalization (ﬁ→fi, ﬂ→fl)
3. Algorithm prefix stripping (only if base concept exists)
4. Trailing punctuation
5. Whitespace normalization
"""

import sys
import re
from collections import defaultdict

sys.path.insert(0, '/home/godli/textparse')
from src.database.models import Concept, ConceptRelationship, paragraph_concepts
from sqlalchemy import create_engine, text, delete, update
from sqlalchemy.orm import Session

engine = create_engine('sqlite:////home/godli/textparse/data/textbooks.db')

LIGATURE_MAP = {
    'ﬁ': 'fi',
    'ﬂ': 'fl',
    'ﬀ': 'ff',
    'ﬃ': 'ffi',
    'ﬄ': 'ffl',
}


def normalize_name(name: str) -> str:
    """Normalize a concept name: fix ligatures, strip trailing periods, collapse whitespace."""
    for lig, repl in LIGATURE_MAP.items():
        name = name.replace(lig, repl)
    name = ' '.join(name.split())  # collapse whitespace
    name = name.rstrip('.')        # trailing periods
    return name


def strip_algorithm_prefix(name: str) -> str | None:
    """Strip 'Algorithm X.Y ' prefix. Returns stripped name or None if no prefix."""
    m = re.match(r'^Algorithm\s+\d+\.\d+\s+(.+)$', name)
    if not m:
        return None
    stripped = m.group(1).strip()
    # Also strip em-dash suffix like '—LVQ' or '—FSϵ'
    stripped_no_suffix = re.sub(r'\s*—.*$', '', stripped).strip()
    return stripped_no_suffix if stripped_no_suffix else stripped


def pick_keeper(c1, c2):
    """Pick which concept to keep. Prefer longer description, then lower id."""
    len1 = len(c1.description or '')
    len2 = len(c2.description or '')
    if len1 >= len2:
        return c1, c2  # keep c1, delete c2
    return c2, c1      # keep c2, delete c1


def merge_concept(session: Session, keep, delete_concept, merges_log: list):
    """Merge delete_concept into keep: re-point relationships and paragraph links."""
    kid = keep.id
    did = delete_concept.id

    merges_log.append((delete_concept.name, keep.name))

    # Re-point concept_relationships.source_id
    session.execute(
        update(ConceptRelationship)
        .where(ConceptRelationship.source_id == did)
        .values(source_id=kid)
    )
    # Re-point concept_relationships.target_id
    session.execute(
        update(ConceptRelationship)
        .where(ConceptRelationship.target_id == did)
        .values(target_id=kid)
    )

    # Re-point paragraph_concepts: insert missing links, skip existing
    existing_para_ids = set(
        r[0] for r in session.execute(
            text("SELECT paragraph_id FROM paragraph_concepts WHERE concept_id = :kid"),
            {"kid": kid}
        ).fetchall()
    )
    old_para_ids = set(
        r[0] for r in session.execute(
            text("SELECT paragraph_id FROM paragraph_concepts WHERE concept_id = :did"),
            {"did": did}
        ).fetchall()
    )
    new_links = old_para_ids - existing_para_ids
    for pid in new_links:
        session.execute(
            text("INSERT INTO paragraph_concepts (paragraph_id, concept_id) VALUES (:pid, :kid)"),
            {"pid": pid, "kid": kid}
        )

    # Delete old paragraph_concepts links
    session.execute(
        text("DELETE FROM paragraph_concepts WHERE concept_id = :did"),
        {"did": did}
    )

    # Delete the concept itself
    session.execute(text("DELETE FROM concepts WHERE id = :did"), {"did": did})


def main():
    with Session(engine) as session:
        concepts = session.query(Concept).all()
        print(f"Starting concepts: {len(concepts)}")
        print(f"Starting relationships: {session.query(ConceptRelationship).count()}")
        print(f"Starting paragraph_concepts: {session.execute(text('SELECT COUNT(*) FROM paragraph_concepts')).scalar()}")
        print()

        # === Phase 1: Normalize all concept names (ligatures, whitespace, trailing periods) ===
        normalize_count = 0
        for c in concepts:
            new_name = normalize_name(c.name)
            if new_name != c.name:
                print(f"  NORMALIZE: {repr(c.name)} -> {repr(new_name)}")
                c.name = new_name
                normalize_count += 1
        session.flush()
        print(f"Normalized {normalize_count} concept names.\n")

        # === Phase 2: Build merge groups ===
        # Reload after normalization
        concepts = session.query(Concept).all()
        by_lower = defaultdict(list)
        for c in concepts:
            by_lower[c.name.lower()].append(c)

        merges_log = []
        deleted_ids = set()

        # 2a. Exact case-insensitive duplicates (includes ligature matches after normalization)
        for key, group in by_lower.items():
            if len(group) < 2:
                continue
            # Pick one to keep, merge the rest
            keeper = group[0]
            for other in group[1:]:
                k, d = pick_keeper(keeper, other)
                keeper = k  # keep the winner for next round
                if d.id not in deleted_ids:
                    merge_concept(session, k, d, merges_log)
                    deleted_ids.add(d.id)

        print(f"Case-insensitive merges: {len(merges_log)}")
        for old, new in merges_log:
            print(f"  {repr(old)} -> {repr(new)}")
        print()

        # 2b. Algorithm prefix stripping
        session.flush()
        concepts = session.query(Concept).all()
        by_lower = {c.name.lower(): c for c in concepts}

        algo_merges = []
        for c in list(concepts):
            if c.id in deleted_ids:
                continue
            stripped = strip_algorithm_prefix(c.name)
            if stripped is None:
                continue
            target_key = stripped.lower()
            if target_key in by_lower and by_lower[target_key].id != c.id:
                target = by_lower[target_key]
                if target.id in deleted_ids:
                    continue
                # Always keep the non-Algorithm-prefixed concept (clean name).
                # Transfer the better description if the Algorithm one has it.
                keep = target
                discard = c
                if len(c.description or '') > len(target.description or ''):
                    keep.description = c.description
                merge_concept(session, keep, discard, algo_merges)
                deleted_ids.add(discard.id)

        print(f"Algorithm prefix merges: {len(algo_merges)}")
        for old, new in algo_merges:
            print(f"  {repr(old)} -> {repr(new)}")
        print()

        # === Phase 3: Deduplicate relationships by (source_id, target_id, type) ===
        session.flush()
        rels = session.query(ConceptRelationship).all()
        seen = set()
        dup_rels = 0
        self_rels = 0
        for r in rels:
            # Remove self-referential
            if r.source_id == r.target_id:
                session.delete(r)
                self_rels += 1
                continue
            key = (r.source_id, r.target_id, r.relationship_type)
            if key in seen:
                session.delete(r)
                dup_rels += 1
            else:
                seen.add(key)

        print(f"Removed {dup_rels} duplicate relationships")
        print(f"Removed {self_rels} self-referential relationships")
        print()

        # === Commit ===
        session.commit()

        # === Final counts ===
        final_concepts = session.query(Concept).count()
        final_rels = session.query(ConceptRelationship).count()
        final_pc = session.execute(text('SELECT COUNT(*) FROM paragraph_concepts')).scalar()
        print(f"Final concepts: {final_concepts}")
        print(f"Final relationships: {final_rels}")
        print(f"Final paragraph_concepts: {final_pc}")
        print(f"\nTotal merges: {len(merges_log) + len(algo_merges)}")
        print(f"Total deleted concepts: {len(deleted_ids)}")


if __name__ == '__main__':
    main()
