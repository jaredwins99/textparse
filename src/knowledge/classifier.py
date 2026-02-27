"""Structural paragraph classifier - classify paragraphs by their role in a textbook."""

import re
from collections import Counter
from dataclasses import dataclass

from src.pdf_parser.parser import ExtractedParagraph

# Paragraph type constants
SECTION_HEADER = "section_header"
DEFINITION = "definition"
THEOREM = "theorem"
LEMMA = "lemma"
COROLLARY = "corollary"
PROOF = "proof"
EXAMPLE = "example"
EXERCISE = "exercise"
FIGURE_CAPTION = "figure_caption"
TABLE_CAPTION = "table_caption"
EQUATION = "equation"
BIBLIOGRAPHY = "bibliography"
NARRATIVE = "narrative"


@dataclass
class ClassifierConfig:
    """Tunable parameters for paragraph classification."""
    body_font_size: float
    header_size_ratio: float = 1.3
    header_max_chars: int = 150
    section_number_pattern: str = r'^\d+(\.\d+)*\s+'

    @classmethod
    def for_esl(cls) -> "ClassifierConfig":
        """Return ESL-specific config."""
        return cls(body_font_size=9.5)


class ParagraphClassifier:
    """Classify ExtractedParagraph instances by their structural role."""

    def __init__(self, config: ClassifierConfig):
        self.config = config
        self._section_re = re.compile(config.section_number_pattern)

    def classify(self, paragraph: ExtractedParagraph, total_pages: int | None = None) -> str:
        """Classify a single paragraph. Returns one of the type constants.

        Args:
            paragraph: The paragraph to classify.
            total_pages: Total pages in the book (needed for bibliography detection).
        """
        text = paragraph.text.strip()
        if not text:
            return NARRATIVE

        dominant_size = self._dominant_font_size(paragraph)

        # Check rules in priority order

        # FIGURE_CAPTION
        if re.match(r'^(FIGURE|Figure)\s*\d', text):
            return FIGURE_CAPTION

        # TABLE_CAPTION
        if re.match(r'^(TABLE|Table)\s*\d', text):
            return TABLE_CAPTION

        # SECTION_HEADER
        if self._is_section_header(text, dominant_size, paragraph):
            return SECTION_HEADER

        # DEFINITION
        if re.match(r'^definition\b', text, re.IGNORECASE) or \
           re.search(r'is defined as\b', text, re.IGNORECASE) or \
           re.search(r'we define\b', text, re.IGNORECASE):
            return DEFINITION

        # THEOREM
        if re.match(r'^Theorem\s*\d*\.?\s', text) or re.match(r'^Theorem\.?\s*$', text):
            return THEOREM

        # LEMMA
        if re.match(r'^Lemma\s*\d*\.?\s', text) or re.match(r'^Lemma\.?\s*$', text):
            return LEMMA

        # COROLLARY
        if re.match(r'^Corollary\s*\d*\.?\s', text) or re.match(r'^Corollary\.?\s*$', text):
            return COROLLARY

        # PROOF
        if re.match(r'^Proof\.?\s', text) or text == "Proof" or text == "Proof.":
            return PROOF

        # EXAMPLE
        if re.match(r'^Example\s*\d*\.?\s', text) or re.match(r'^Example\.?\s*$', text):
            return EXAMPLE

        # EXERCISE
        if re.match(r'^(Exercise|Ex\.)\s*\d*\.?\s', text) or \
           re.match(r'^(Exercise|Ex\.)\.?\s*$', text):
            return EXERCISE

        # EQUATION
        if self._is_equation(text):
            return EQUATION

        # BIBLIOGRAPHY
        if self._is_bibliography(text, paragraph.page_number, total_pages):
            return BIBLIOGRAPHY

        return NARRATIVE

    def classify_batch(
        self,
        paragraphs: list[ExtractedParagraph],
        total_pages: int | None = None,
    ) -> dict[int, str]:
        """Classify a list of paragraphs.

        Returns:
            Dict mapping paragraph.sequence_index to its type string.
        """
        return {
            p.sequence_index: self.classify(p, total_pages=total_pages)
            for p in paragraphs
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dominant_font_size(self, paragraph: ExtractedParagraph) -> float | None:
        """Compute the font size with the most total characters across all spans.

        Returns None when lines metadata is unavailable.
        """
        if paragraph.lines is None:
            return None

        char_counts: Counter[float] = Counter()
        for line in paragraph.lines:
            for span in line.spans:
                char_counts[span.size] += len(span.text)

        if not char_counts:
            return None

        return char_counts.most_common(1)[0][0]

    # Characters commonly found in math expressions — reject text containing these
    _MATH_CHARS = set(
        '|⟨⟩λαβγδεϵθκμνξπρσςτυφχψωΓΔΘΛΞΠΣΦΨΩ=∗ˆ˜¯≤≥∑∏∫±∓×÷∂∇∞∈∉⊂⊃⊆⊇∪∩'
    )

    def _is_section_header(self, text: str, dominant_size: float | None, paragraph=None) -> bool:
        """Check whether the paragraph is a section header."""
        # Reject very short numeric-only text (axis labels, page numbers)
        stripped = text.strip()
        if re.match(r'^[\d.\s,\-]+$', stripped):
            return False

        # Reject text containing math symbols (equations misclassified as headers)
        if any(c in self._MATH_CHARS for c in stripped):
            return False

        # Reject ellipsis patterns like "j = 1, . . . , p"
        if re.search(r'\.\s*\.\s*\.', stripped):
            return False

        # Reject metadata / title page artifacts
        if 'Printer:' in stripped or 'Opaque' in stripped:
            return False
        if stripped.startswith('This is page'):
            return False
        if 'Springer' in stripped:
            return False

        # Font-size based check — require text to contain at least one letter
        if dominant_size is not None and any(c.isalpha() for c in stripped):
            threshold = self.config.body_font_size * self.config.header_size_ratio
            if dominant_size > threshold and len(stripped) < self.config.header_max_chars:
                # Additional filter: must have substantial text (not just "12" or "0.4")
                if len(stripped) > 3:
                    # Reject standalone numbers > 30 (page numbers, not sections)
                    if re.match(r'^\d+$', stripped) and int(stripped) > 30:
                        return False
                    return True

        # Section-number based: require a proper section number followed by a word
        # e.g. "3.2 Shrinkage Methods" but NOT "0.0 0.4" or "40 50"
        section_match = re.match(r'^(\d+(?:\.\d+)*)\s+([A-Z])', stripped)
        if section_match and len(stripped) < self.config.header_max_chars:
            # Verify the number looks like a section number (starts > 0, not a decimal like 0.4)
            num = section_match.group(1)
            if not num.startswith('0'):
                top_level = int(num.split('.')[0])
                # ESL has 18 chapters. Numbers > 18 at top level are page numbers, not sections.
                if top_level > 18:
                    return False
                # Require the title portion to have at least 2 words or 8+ characters
                # This rejects fragments like "1 N" (number + single letter)
                title_part = stripped[section_match.end() - 1:].strip()  # text from the capital letter onward
                if len(title_part.split()) < 2 and len(title_part) < 8:
                    return False
                return True

        return False

    @staticmethod
    def _is_equation(text: str) -> bool:
        """Short text dominated by non-alpha characters."""
        if len(text) >= 80:
            return False
        alpha_count = sum(1 for c in text if c.isalpha())
        total = len(text.replace(" ", ""))
        if total == 0:
            return False
        return alpha_count / total < 0.3

    @staticmethod
    def _is_bibliography(text: str, page_number: int, total_pages: int | None) -> bool:
        """Check for reference / bibliography patterns in the tail of the book."""
        # Must be in the last 10% of the book
        if total_pages is not None:
            if page_number < total_pages * 0.9:
                return False
        else:
            # Without page info we can't confirm position; skip this rule
            return False

        # Bracketed reference like [1] or [23]
        if re.match(r'^\[\d+\]', text):
            return True

        # Author-year pattern like "Smith, J. (2003)"
        if re.match(r'^[A-Z][a-z]+,?\s.*\(\d{4}\)', text):
            return True

        return False
