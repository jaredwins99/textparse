"""Database manager - Handle storage and retrieval of parsed content."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload

from .models import Base, Textbook, Page, Paragraph, Concept, Section, ConceptRelationship


class DatabaseManager:
    """Manage the textbook database."""

    def __init__(self, db_path: str | Path = "data/textbooks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._session: Session | None = None

    def __enter__(self):
        self._session = self.SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._session.rollback()
        else:
            self._session.commit()
        self._session.close()
        self._session = None
        return False

    def _get_session(self) -> tuple[Session, bool]:
        """Return (session, is_standalone).

        If a context-managed session exists, return it with is_standalone=False.
        Otherwise create a new session with is_standalone=True.
        """
        if self._session is not None:
            return self._session, False
        return self.SessionLocal(), True

    def add_textbook(self, title: str, file_path: str, total_pages: int) -> Textbook:
        """Add a new textbook to the database, or return existing one if file_path matches."""
        session, standalone = self._get_session()
        try:
            existing = session.query(Textbook).filter_by(file_path=file_path).first()
            if existing:
                session.refresh(existing)
                return existing
            textbook = Textbook(
                title=title,
                file_path=file_path,
                total_pages=total_pages
            )
            session.add(textbook)
            if standalone:
                session.commit()
            else:
                session.flush()
            session.refresh(textbook)
            return textbook
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def add_page(self, textbook_id: int, page_number: int, raw_text: str) -> Page:
        """Add a page to a textbook."""
        session, standalone = self._get_session()
        try:
            page = Page(
                textbook_id=textbook_id,
                page_number=page_number,
                raw_text=raw_text
            )
            session.add(page)
            if standalone:
                session.commit()
            else:
                session.flush()
            session.refresh(page)
            return page
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def add_paragraph(
        self,
        page_id: int,
        sequence_index: int,
        text: str,
        bbox: tuple[float, float, float, float] | None = None
    ) -> Paragraph:
        """Add a paragraph to a page."""
        session, standalone = self._get_session()
        try:
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
            if standalone:
                session.commit()
            else:
                session.flush()
            session.refresh(paragraph)
            return paragraph
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def get_or_create_concept(self, name: str, description: str = None, category: str = None) -> Concept:
        """Get an existing concept or create a new one."""
        session, standalone = self._get_session()
        try:
            concept = session.query(Concept).filter_by(name=name).first()
            if not concept:
                concept = Concept(name=name, description=description, category=category)
                session.add(concept)
                if standalone:
                    session.commit()
                else:
                    session.flush()
                session.refresh(concept)
            return concept
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def link_paragraph_to_concept(self, paragraph_id: int, concept_id: int):
        """Link a paragraph to a concept."""
        session, standalone = self._get_session()
        try:
            paragraph = session.get(Paragraph, paragraph_id)
            concept = session.get(Concept, concept_id)
            if not paragraph or not concept:
                return
            if concept not in paragraph.concepts:
                paragraph.concepts.append(concept)
                if standalone:
                    session.commit()
                else:
                    session.flush()
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def get_paragraphs_by_concept(self, concept_name: str) -> list[Paragraph]:
        """Get all paragraphs related to a concept."""
        session, standalone = self._get_session()
        try:
            concept = (
                session.query(Concept)
                .options(joinedload(Concept.paragraphs))
                .filter_by(name=concept_name)
                .first()
            )
            if concept:
                paragraphs = list(concept.paragraphs)
                if standalone:
                    session.expunge_all()
                return paragraphs
            return []
        finally:
            if standalone:
                session.close()

    def get_all_concepts(self) -> list[Concept]:
        """Get all concepts in the database."""
        session, standalone = self._get_session()
        try:
            concepts = session.query(Concept).all()
            if standalone:
                session.expunge_all()
            return concepts
        finally:
            if standalone:
                session.close()

    def add_section(
        self,
        textbook_id: int,
        title: str,
        number: str = None,
        parent_id: int = None,
        page_start: int = None,
        page_end: int = None
    ) -> Section:
        """Add a section to a textbook."""
        session, standalone = self._get_session()
        try:
            section = Section(
                textbook_id=textbook_id,
                title=title,
                number=number,
                parent_id=parent_id,
                page_start=page_start,
                page_end=page_end
            )
            session.add(section)
            if standalone:
                session.commit()
            else:
                session.flush()
            session.refresh(section)
            return section
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def add_concept_relationship(
        self,
        source_id: int,
        target_id: int,
        relationship_type: str
    ) -> ConceptRelationship:
        """Add a relationship between two concepts."""
        session, standalone = self._get_session()
        try:
            rel = ConceptRelationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type
            )
            session.add(rel)
            if standalone:
                session.commit()
            else:
                session.flush()
            session.refresh(rel)
            return rel
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()

    def update_paragraph_type(self, paragraph_id: int, paragraph_type: str):
        """Set the paragraph_type on an existing paragraph."""
        session, standalone = self._get_session()
        try:
            paragraph = session.get(Paragraph, paragraph_id)
            if paragraph:
                paragraph.paragraph_type = paragraph_type
                if standalone:
                    session.commit()
                else:
                    session.flush()
        except Exception:
            if standalone:
                session.rollback()
            raise
        finally:
            if standalone:
                session.close()
