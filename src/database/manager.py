"""Database manager - Handle storage and retrieval of parsed content."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Textbook, Page, Paragraph, Concept


class DatabaseManager:
    """Manage the textbook database."""

    def __init__(self, db_path: str | Path = "data/textbooks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def add_textbook(self, title: str, file_path: str, total_pages: int) -> Textbook:
        """Add a new textbook to the database."""
        with self.get_session() as session:
            textbook = Textbook(
                title=title,
                file_path=file_path,
                total_pages=total_pages
            )
            session.add(textbook)
            session.commit()
            session.refresh(textbook)
            return textbook

    def add_page(self, textbook_id: int, page_number: int, raw_text: str) -> Page:
        """Add a page to a textbook."""
        with self.get_session() as session:
            page = Page(
                textbook_id=textbook_id,
                page_number=page_number,
                raw_text=raw_text
            )
            session.add(page)
            session.commit()
            session.refresh(page)
            return page

    def add_paragraph(
        self,
        page_id: int,
        sequence_index: int,
        text: str,
        bbox: tuple[float, float, float, float] | None = None
    ) -> Paragraph:
        """Add a paragraph to a page."""
        with self.get_session() as session:
            paragraph = Paragraph(
                page_id=page_id,
                sequence_index=sequence_index,
                text=text,
                bbox_x0=bbox[0] if bbox else None,
                bbox_y0=bbox[1] if bbox else None,
                bbox_x1=bbox[2] if bbox else None,
                bbox_y1=bbox[3] if bbox else None
            )
            session.add(paragraph)
            session.commit()
            session.refresh(paragraph)
            return paragraph

    def get_or_create_concept(self, name: str, description: str = None, category: str = None) -> Concept:
        """Get an existing concept or create a new one."""
        with self.get_session() as session:
            concept = session.query(Concept).filter_by(name=name).first()
            if not concept:
                concept = Concept(name=name, description=description, category=category)
                session.add(concept)
                session.commit()
                session.refresh(concept)
            return concept

    def link_paragraph_to_concept(self, paragraph_id: int, concept_id: int):
        """Link a paragraph to a concept."""
        with self.get_session() as session:
            paragraph = session.query(Paragraph).get(paragraph_id)
            concept = session.query(Concept).get(concept_id)
            if paragraph and concept:
                paragraph.concepts.append(concept)
                session.commit()

    def get_paragraphs_by_concept(self, concept_name: str) -> list[Paragraph]:
        """Get all paragraphs related to a concept."""
        with self.get_session() as session:
            concept = session.query(Concept).filter_by(name=concept_name).first()
            if concept:
                return concept.paragraphs
            return []

    def get_all_concepts(self) -> list[Concept]:
        """Get all concepts in the database."""
        with self.get_session() as session:
            return session.query(Concept).all()
