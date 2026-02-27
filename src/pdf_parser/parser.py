"""PDF Parser - Extract text from textbook PDFs paragraph by paragraph."""

import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpanData:
    """Font-level metadata for a single text span."""
    text: str
    font: str
    size: float
    flags: int  # bit 0=superscript, 1=italic, 2=serif, 3=monospace, 4=bold
    color: int
    bbox: tuple[float, float, float, float]


@dataclass
class LineData:
    """A line of text composed of spans with font metadata."""
    spans: list[SpanData]
    bbox: tuple[float, float, float, float]


@dataclass
class ExtractedParagraph:
    """A paragraph extracted from a PDF."""
    text: str
    page_number: int
    sequence_index: int  # Order within the page
    bbox: tuple[float, float, float, float] | None = None  # Bounding box (x0, y0, x1, y1)
    lines: list[LineData] | None = None  # Rich line/span data with font metadata


@dataclass
class ExtractedPage:
    """A page extracted from a PDF."""
    page_number: int
    paragraphs: list[ExtractedParagraph]
    raw_text: str


class PDFParser:
    """Parse textbook PDFs into structured paragraphs."""

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None

    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    def extract_page(self, page_number: int) -> ExtractedPage:
        """Extract paragraphs from a single page."""
        if not self.doc:
            raise RuntimeError("PDFParser must be used as context manager")

        page = self.doc[page_number]
        blocks = page.get_text("dict")["blocks"]

        paragraphs = []
        sequence_index = 0

        for block in blocks:
            if block["type"] == 0:  # Text block
                text = ""
                line_data_list = []
                for line in block["lines"]:
                    span_data_list = []
                    for span in line["spans"]:
                        text += span["text"]
                        span_data_list.append(SpanData(
                            text=span["text"],
                            font=span["font"],
                            size=span["size"],
                            flags=span["flags"],
                            color=span["color"],
                            bbox=tuple(span["bbox"]),
                        ))
                    text += "\n"
                    line_data_list.append(LineData(
                        spans=span_data_list,
                        bbox=tuple(line["bbox"]),
                    ))

                text = text.strip()
                if text:
                    paragraphs.append(ExtractedParagraph(
                        text=text,
                        page_number=page_number,
                        sequence_index=sequence_index,
                        bbox=tuple(block["bbox"]),
                        lines=line_data_list,
                    ))
                    sequence_index += 1

        raw_text = page.get_text()
        return ExtractedPage(
            page_number=page_number,
            paragraphs=paragraphs,
            raw_text=raw_text
        )

    def extract_all(self) -> list[ExtractedPage]:
        """Extract all pages from the PDF."""
        if not self.doc:
            raise RuntimeError("PDFParser must be used as context manager")

        pages = []
        for page_num in range(len(self.doc)):
            pages.append(self.extract_page(page_num))
        return pages

    @property
    def page_count(self) -> int:
        """Get the number of pages in the PDF."""
        if not self.doc:
            raise RuntimeError("PDFParser must be used as context manager")
        return len(self.doc)
