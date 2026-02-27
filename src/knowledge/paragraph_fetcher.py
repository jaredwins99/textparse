"""Fetch relevant paragraphs for a concept from the textbook database."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "textbooks.db"


def get_section_page_range(conn, section_id):
    """Get (page_start, page_end) for a section, inferring page_end from next sibling."""
    cur = conn.cursor()
    row = cur.execute(
        "SELECT page_start, page_end, parent_id FROM sections WHERE id = ?",
        (section_id,)
    ).fetchone()
    if not row:
        return None, None

    page_start = row[0]
    page_end = row[1]

    if page_end is None and page_start is not None:
        # Find next sibling section by page_start
        parent_id = row[2]
        if parent_id is not None:
            next_row = cur.execute(
                "SELECT page_start FROM sections WHERE parent_id = ? AND page_start > ? ORDER BY page_start LIMIT 1",
                (parent_id, page_start)
            ).fetchone()
        else:
            next_row = cur.execute(
                "SELECT page_start FROM sections WHERE parent_id IS NULL AND page_start > ? ORDER BY page_start LIMIT 1",
                (page_start,)
            ).fetchone()

        if next_row:
            page_end = next_row[0] - 1
        else:
            # Last section in parent — use parent's end, or add a reasonable default
            page_end = page_start + 20  # fallback: 20 pages max

    return page_start, page_end


def fetch_paragraphs_for_section(conn, section_id, paragraph_types=('narrative', 'equation')):
    """Fetch all paragraphs in a section's page range."""
    page_start, page_end = get_section_page_range(conn, section_id)
    if page_start is None:
        return []

    placeholders = ','.join('?' * len(paragraph_types))
    cur = conn.cursor()
    rows = cur.execute(f"""
        SELECT par.id, par.text, par.paragraph_type, p.page_number
        FROM paragraphs par
        JOIN pages p ON par.page_id = p.id
        WHERE p.page_number >= ? AND p.page_number <= ?
        AND par.paragraph_type IN ({placeholders})
        ORDER BY p.page_number, par.sequence_index
    """, (page_start, page_end, *paragraph_types)).fetchall()

    return [{"id": r[0], "text": r[1], "type": r[2], "page": r[3]} for r in rows]


def fetch_paragraphs_by_name(conn, concept_name, limit=20):
    """Fallback: find paragraphs mentioning the concept name."""
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT par.id, par.text, par.paragraph_type, p.page_number
        FROM paragraphs par
        JOIN pages p ON par.page_id = p.id
        WHERE par.text LIKE ? AND par.paragraph_type IN ('narrative', 'equation')
        ORDER BY p.page_number
        LIMIT ?
    """, (f"%{concept_name}%", limit)).fetchall()

    return [{"id": r[0], "text": r[1], "type": r[2], "page": r[3]} for r in rows]


def fetch_context_for_concept(conn, concept_id):
    """Fetch all relevant paragraphs for a concept: section-based + name-based fallback."""
    cur = conn.cursor()
    concept = cur.execute(
        "SELECT id, name, section_id FROM concepts WHERE id = ?",
        (concept_id,)
    ).fetchone()
    if not concept:
        return [], ""

    name = concept[1]
    section_id = concept[2]

    paragraphs = []
    if section_id:
        paragraphs = fetch_paragraphs_for_section(conn, section_id)

    # If section gave us few results, supplement with name search
    if len(paragraphs) < 5:
        name_paras = fetch_paragraphs_by_name(conn, name)
        seen_ids = {p["id"] for p in paragraphs}
        for p in name_paras:
            if p["id"] not in seen_ids:
                paragraphs.append(p)

    return paragraphs, name
