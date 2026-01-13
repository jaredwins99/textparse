"""Textbook Parser - Main entry point."""

from pathlib import Path

from src.pdf_parser import PDFParser
from src.database import DatabaseManager
from src.visualization import VisualizationRenderer


def parse_textbook(pdf_path: str, title: str = None):
    """Parse a textbook PDF and store in database."""
    pdf_path = Path(pdf_path)
    title = title or pdf_path.stem

    db = DatabaseManager()

    with PDFParser(pdf_path) as parser:
        page_count = parser.page_count

        # Add textbook to database
        textbook = db.add_textbook(
            title=title,
            file_path=str(pdf_path),
            total_pages=page_count
        )

        # Extract and store all pages
        for page_data in parser.extract_all():
            page = db.add_page(
                textbook_id=textbook.id,
                page_number=page_data.page_number,
                raw_text=page_data.raw_text
            )

            for para in page_data.paragraphs:
                db.add_paragraph(
                    page_id=page.id,
                    sequence_index=para.sequence_index,
                    text=para.text,
                    bbox=para.bbox
                )

    print(f"Parsed {title}: {page_count} pages")
    return textbook


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <pdf_path> [title]")
        print("\nThis will parse the PDF and store paragraphs in the database.")
        print("Concepts must be identified manually after parsing.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None

    parse_textbook(pdf_path, title)


if __name__ == "__main__":
    main()
