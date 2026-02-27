"""Database models - Sequential storage organized by concepts."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, Table, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Many-to-many relationship between paragraphs and concepts
paragraph_concepts = Table(
    'paragraph_concepts',
    Base.metadata,
    Column('paragraph_id', Integer, ForeignKey('paragraphs.id'), primary_key=True),
    Column('concept_id', Integer, ForeignKey('concepts.id'), primary_key=True)
)


class Textbook(Base):
    """A textbook PDF that has been parsed."""
    __tablename__ = 'textbooks'
    __table_args__ = (UniqueConstraint('file_path', name='uq_textbook_file_path'),)

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    total_pages = Column(Integer)

    pages = relationship("Page", back_populates="textbook", cascade="all, delete-orphan")


class Page(Base):
    """A page from a textbook."""
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True)
    textbook_id = Column(Integer, ForeignKey('textbooks.id'), nullable=False)
    page_number = Column(Integer, nullable=False)  # Sequential order
    raw_text = Column(Text)

    textbook = relationship("Textbook", back_populates="pages")
    paragraphs = relationship("Paragraph", back_populates="page", cascade="all, delete-orphan")


class Paragraph(Base):
    """A paragraph from a page, linked to concepts."""
    __tablename__ = 'paragraphs'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'), nullable=False)
    sequence_index = Column(Integer, nullable=False)  # Order within page
    text = Column(Text, nullable=False)

    # Bounding box coordinates (optional)
    bbox_x0 = Column(Float)
    bbox_y0 = Column(Float)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)

    paragraph_type = Column(String(50), nullable=True)

    page = relationship("Page", back_populates="paragraphs")
    concepts = relationship("Concept", secondary=paragraph_concepts, back_populates="paragraphs")


class Section(Base):
    """A section within a textbook, supporting hierarchical nesting."""
    __tablename__ = 'sections'

    id = Column(Integer, primary_key=True)
    textbook_id = Column(Integer, ForeignKey('textbooks.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('sections.id'), nullable=True)  # null = top-level
    number = Column(String(50))   # e.g., "3.2.1"
    title = Column(String(500), nullable=False)
    page_start = Column(Integer)
    page_end = Column(Integer)

    textbook = relationship("Textbook")
    parent = relationship("Section", remote_side="Section.id", backref="children")


class Concept(Base):
    """A concept that one or more paragraphs explain."""
    __tablename__ = 'concepts'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(100))  # Optional grouping
    new_category = Column(String(100), nullable=True)  # New taxonomy: model, estimation, validation, guarantees, multi_model, improvements
    subcategory = Column(String(100), nullable=True)  # Subcategory within new_category
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    quote = Column(Text, nullable=True)
    formula = Column(Text, nullable=True)

    paragraphs = relationship("Paragraph", secondary=paragraph_concepts, back_populates="concepts")
    section = relationship("Section")


class ConceptFact(Base):
    """A key fact about a concept, extracted as a verbatim quote from the textbook."""
    __tablename__ = 'concept_facts'

    id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    fact_text = Column(Text, nullable=False)  # Verbatim quote from textbook
    fact_type = Column(String(50))  # definition, formula, property, comparison, intuition, example
    importance_rank = Column(Integer)  # 1 = most important
    page_number = Column(Integer, nullable=True)
    paragraph_id = Column(Integer, ForeignKey('paragraphs.id'), nullable=True)

    concept = relationship("Concept", backref="facts")
    paragraph = relationship("Paragraph")


class ConceptRelationship(Base):
    """A directed relationship between two concepts."""
    __tablename__ = 'concept_relationships'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    # Types: "prerequisite", "generalizes", "special_case_of", "proved_by", "example_of", "contrasts_with", "uses"

    source = relationship("Concept", foreign_keys=[source_id])
    target = relationship("Concept", foreign_keys=[target_id])
