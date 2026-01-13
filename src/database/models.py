"""Database models - Sequential storage organized by concepts."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, Table
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

    page = relationship("Page", back_populates="paragraphs")
    concepts = relationship("Concept", secondary=paragraph_concepts, back_populates="paragraphs")


class Concept(Base):
    """A concept that one or more paragraphs explain."""
    __tablename__ = 'concepts'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(100))  # Optional grouping

    paragraphs = relationship("Paragraph", secondary=paragraph_concepts, back_populates="concepts")
