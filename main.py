"""Textbook Parser - Main entry point."""

import sys
from pathlib import Path

from src.pdf_parser import PDFParser
from src.database import DatabaseManager
from src.knowledge import (
    ParagraphClassifier,
    ClassifierConfig,
    ConceptExtractor,
    RelationshipMapper,
)


def parse_textbook(pdf_path: str, title: str = None):
    """Parse a textbook PDF: extract, classify, identify concepts, map relationships.

    Single-pass pipeline while font metadata is live in memory.
    """
    pdf_path = Path(pdf_path)
    title = title or pdf_path.stem
    config = ClassifierConfig.for_esl()
    classifier = ParagraphClassifier(config)

    with DatabaseManager() as db, PDFParser(pdf_path) as parser:
        page_count = parser.page_count

        textbook = db.add_textbook(
            title=title,
            file_path=str(pdf_path),
            total_pages=page_count
        )

        # Phase 1: Parse and classify all pages, keeping ExtractedPages in memory
        all_pages = []
        all_classifications = {}
        paragraph_db_ids = {}  # (page_number, sequence_index) -> paragraph.id

        print(f"Parsing {page_count} pages...")
        for page_data in parser.extract_all():
            page = db.add_page(
                textbook_id=textbook.id,
                page_number=page_data.page_number,
                raw_text=page_data.raw_text
            )

            classifications = classifier.classify_batch(
                page_data.paragraphs, total_pages=page_count
            )

            for para in page_data.paragraphs:
                p = db.add_paragraph(
                    page_id=page.id,
                    sequence_index=para.sequence_index,
                    text=para.text,
                    bbox=para.bbox
                )
                ptype = classifications.get(para.sequence_index)
                if ptype:
                    db.update_paragraph_type(p.id, ptype)
                key = (page_data.page_number, para.sequence_index)
                all_classifications[key] = ptype or "narrative"
                paragraph_db_ids[key] = p.id

            all_pages.append(page_data)

        print(f"Parsed {page_count} pages. Extracting concepts...")

        # Phase 2: Extract concepts (font metadata still in memory via all_pages)
        extractor = ConceptExtractor()
        result = extractor.extract(all_pages, all_classifications, total_pages=page_count)

        # Store sections
        section_map = {}  # number -> db section id
        for sec in result.sections:
            parent_id = section_map.get(sec.parent_number)
            db_section = db.add_section(
                textbook_id=textbook.id,
                title=sec.title,
                number=sec.number,
                parent_id=parent_id,
                page_start=sec.page_number,
            )
            if sec.number:
                section_map[sec.number] = db_section.id

        # Store concepts
        concept_map = {}  # name -> db concept id
        for concept in result.concepts:
            section_id = section_map.get(concept.section_number)
            db_concept = db.get_or_create_concept(
                name=concept.name,
                description=concept.description,
                category=concept.concept_type,
            )
            if section_id:
                db_concept.section_id = section_id
            db._session.flush()
            concept_map[concept.name] = db_concept.id

            # Link source paragraphs
            for pg_num, seq_idx in concept.source_paragraph_indices:
                para_id = paragraph_db_ids.get((pg_num, seq_idx))
                if para_id:
                    db.link_paragraph_to_concept(para_id, db_concept.id)

        print(f"Found {len(result.sections)} sections, {len(result.concepts)} concepts. Mapping relationships...")

        # Phase 3: Infer relationships
        mapper = RelationshipMapper()
        relationships = mapper.infer(result.concepts, result.sections)

        rel_count = 0
        for rel in relationships:
            source_id = concept_map.get(rel.source_name)
            target_id = concept_map.get(rel.target_name)
            if source_id and target_id:
                db.add_concept_relationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=rel.relationship_type,
                )
                rel_count += 1

        print(f"\nDone: {page_count} pages, {len(result.sections)} sections, "
              f"{len(result.concepts)} concepts, {rel_count} relationships")

    return textbook


def show_info(textbook_id: int):
    """Print summary stats for a textbook."""
    from sqlalchemy import func
    from src.database.models import Textbook, Page, Paragraph, Concept, Section, ConceptRelationship

    with DatabaseManager() as db:
        session = db._session

        textbook = session.get(Textbook, textbook_id)
        if not textbook:
            print(f"Textbook {textbook_id} not found")
            return

        page_count = session.query(Page).filter_by(textbook_id=textbook_id).count()
        para_count = (
            session.query(Paragraph)
            .join(Page)
            .filter(Page.textbook_id == textbook_id)
            .count()
        )
        section_count = session.query(Section).filter_by(textbook_id=textbook_id).count()
        concept_count = session.query(Concept).count()
        rel_count = session.query(ConceptRelationship).count()

        # Paragraph type breakdown
        type_breakdown = (
            session.query(Paragraph.paragraph_type, func.count())
            .join(Page)
            .filter(Page.textbook_id == textbook_id)
            .group_by(Paragraph.paragraph_type)
            .all()
        )

        # Section tree depth
        max_depth = 0
        for sec in session.query(Section).filter_by(textbook_id=textbook_id).all():
            depth = 1
            current = sec
            while current.parent_id:
                depth += 1
                current = session.get(Section, current.parent_id)
            max_depth = max(max_depth, depth)

        print(f"\n=== {textbook.title} ===")
        print(f"Pages: {page_count}")
        print(f"Paragraphs: {para_count}")
        print(f"Sections: {section_count} (max depth: {max_depth})")
        print(f"Concepts: {concept_count}")
        print(f"Relationships: {rel_count}")
        print(f"\nParagraph types:")
        for ptype, count in sorted(type_breakdown, key=lambda x: -x[1]):
            label = ptype or "unclassified"
            print(f"  {label}: {count}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py parse <pdf_path> [title]  - Parse, classify, and extract concepts")
        print("  python main.py info <textbook_id>        - Show textbook stats")
        sys.exit(1)

    command = sys.argv[1]

    if command == "parse":
        if len(sys.argv) < 3:
            print("Usage: python main.py parse <pdf_path> [title]")
            sys.exit(1)
        pdf_path = sys.argv[2]
        title = sys.argv[3] if len(sys.argv) > 3 else None
        parse_textbook(pdf_path, title)

    elif command == "info":
        if len(sys.argv) < 3:
            print("Usage: python main.py info <textbook_id>")
            sys.exit(1)
        textbook_id = int(sys.argv[2])
        show_info(textbook_id)

    else:
        print(f"Unknown command: {command}")
        print("Available commands: parse, info")
        sys.exit(1)


if __name__ == "__main__":
    main()
