"""Table Extractor - Extract tables from PDFs using pdfplumber."""

import pdfplumber
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedTable:
    """A table extracted from a PDF page."""
    page_number: int
    table_index: int  # 0-indexed per page
    headers: list[str]
    rows: list[list[str]]
    bbox: tuple[float, float, float, float] | None


class TableExtractor:
    """Extract tables from PDFs using pdfplumber."""

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self._pdf = None

    def __enter__(self):
        self._pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._pdf:
            self._pdf.close()

    @property
    def page_count(self) -> int:
        """Get the number of pages in the PDF."""
        if not self._pdf:
            raise RuntimeError("TableExtractor must be used as context manager")
        return len(self._pdf.pages)

    def extract_page_tables(self, page_number: int) -> list[ExtractedTable]:
        """Extract all tables from a given page."""
        if not self._pdf:
            raise RuntimeError("TableExtractor must be used as context manager")

        page = self._pdf.pages[page_number]
        tables = page.extract_tables()

        if tables is None:
            return []

        results = []
        # Get bounding boxes from find_tables to pair with extracted data
        found = page.find_tables()

        for table_index, table_data in enumerate(tables):
            if not table_data:
                continue

            bbox = tuple(found[table_index].bbox) if table_index < len(found) else None

            # First row is treated as headers
            raw_headers = table_data[0] if table_data else []
            headers = [cell if cell is not None else "" for cell in raw_headers]

            rows = []
            for row in table_data[1:]:
                rows.append([cell if cell is not None else "" for cell in row])

            results.append(ExtractedTable(
                page_number=page_number,
                table_index=table_index,
                headers=headers,
                rows=rows,
                bbox=bbox,
            ))

        return results

    def extract_all_tables(self) -> Generator[ExtractedTable]:
        """Yield all tables from all pages."""
        if not self._pdf:
            raise RuntimeError("TableExtractor must be used as context manager")

        for page_number in range(len(self._pdf.pages)):
            yield from self.extract_page_tables(page_number)
