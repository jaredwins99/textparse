"""Export knowledge graph from SQLite to JSON for Cytoscape.js visualization."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "textbooks.db"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "output" / "knowledge-graph" / "graph-data.js"


def export():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Concepts
    c.execute("""
        SELECT c.id, c.name, c.description, c.category, c.section_id,
               c.quote, c.formula, c.new_category, c.subcategory,
               s.number as section_number, s.title as section_title
        FROM concepts c
        LEFT JOIN sections s ON c.section_id = s.id
    """)
    concepts_rows = c.fetchall()

    # Fetch concept facts
    c.execute("SELECT concept_id, fact_text, fact_type, importance_rank, page_number FROM concept_facts ORDER BY concept_id, importance_rank")
    facts_by_concept = {}
    for row in c.fetchall():
        cid = str(row["concept_id"])
        if cid not in facts_by_concept:
            facts_by_concept[cid] = []
        facts_by_concept[cid].append({
            "text": row["fact_text"],
            "type": row["fact_type"],
            "rank": row["importance_rank"],
            "page": row["page_number"],
        })

    nodes = []
    chapters_seen = set()
    for row in concepts_rows:
        section_num = row["section_number"] or ""
        chapter = section_num.split(".")[0] if section_num else ""
        parent_id = f"ch-{chapter}" if chapter else "ch-0"
        chapters_seen.add((parent_id, chapter))
        nodes.append({
            "data": {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"] or "",
                "category": row["new_category"] or row["category"] or "other",
                "subcategory": row["subcategory"] or "",
                "old_category": row["category"] or "other",
                "chapter": chapter,
                "section": f"{section_num} {row['section_title']}" if section_num else "",
                "quote": row["quote"] or "",
                "formula": row["formula"] or "",
                "facts": facts_by_concept.get(str(row["id"]), []),
                "parent": parent_id,
            }
        })

    # Parent nodes for each chapter
    parent_nodes = []
    for parent_id, chapter in sorted(chapters_seen):
        label = f"Chapter {chapter}" if chapter else "Uncategorized"
        parent_nodes.append({
            "data": {
                "id": parent_id,
                "name": label,
                "isParent": True,
            }
        })
    nodes = parent_nodes + nodes

    # Relationships
    c.execute("SELECT id, source_id, target_id, relationship_type FROM concept_relationships")
    edges = []
    for row in c.fetchall():
        edges.append({
            "data": {
                "id": f"e{row['id']}",
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relationship_type": row["relationship_type"],
            }
        })

    conn.close()

    # Write as JS variable assignment (no CORS issues when opening file://)
    output = {
        "nodes": nodes,
        "edges": edges,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("const GRAPH_DATA = ")
        json.dump(output, f, indent=None)  # compact for faster loading
        f.write(";")

    concept_count = len(nodes) - len(parent_nodes)
    print(f"Exported {concept_count} concepts ({len(parent_nodes)} chapter groups) and {len(edges)} edges to {OUTPUT_PATH}")


if __name__ == "__main__":
    export()
