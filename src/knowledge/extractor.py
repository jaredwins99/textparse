"""Concept extractor - Extract sections and concepts from classified paragraphs."""

import re
from dataclasses import dataclass, field

from src.pdf_parser.parser import ExtractedPage, ExtractedParagraph, SpanData


@dataclass
class ExtractedConcept:
    name: str
    description: str
    concept_type: str  # "definition", "theorem", "method", "algorithm", "metric", etc.
    source_paragraph_indices: list[tuple[int, int]]  # [(page_number, sequence_index), ...]
    section_number: str | None = None  # which section this belongs to


@dataclass
class ExtractedSection:
    number: str | None  # "3.2.1"
    title: str
    page_number: int
    parent_number: str | None = None  # inferred from numbering (e.g., "3.2" is parent of "3.2.1")


@dataclass
class ExtractionResult:
    sections: list[ExtractedSection] = field(default_factory=list)
    concepts: list[ExtractedConcept] = field(default_factory=list)


# Regex to parse a section header like "3.2.1 Shrinkage Methods"
_SECTION_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)")

# Regex to match theorem-like headers: "Theorem 3.1 (Gauss-Markov)" or "Lemma 2"
_THEOREM_RE = re.compile(
    r"^(Theorem|Lemma|Corollary)\s+(\d+(?:\.\d+)*)"
    r"(?:\s*\(([^)]+)\))?",
    re.IGNORECASE,
)

# Regex to extract a term after "Definition:" prefix
_DEFINITION_PREFIX_RE = re.compile(r"^Definition\s*[:\.]?\s*(.*)", re.IGNORECASE)

# Regex for quoted terms
_QUOTED_TERM_RE = re.compile(r"""["\u201c]([^"\u201d]+)["\u201d]""")

# Textual introduction patterns — capture the concept name after the trigger
_TEXTUAL_INTRO_PATTERNS = [
    re.compile(r"(?:is|are)\s+called\s+(?:the\s+)?(.+?)(?:[.,;:\n]|$)", re.IGNORECASE),
    re.compile(r"known\s+as\s+(?:the\s+)?(.+?)(?:[.,;:\n]|$)", re.IGNORECASE),
    re.compile(r"referred\s+to\s+as\s+(?:the\s+)?(.+?)(?:[.,;:\n]|$)", re.IGNORECASE),
    re.compile(r"we\s+(?:call|define)\s+(?:this\s+)?(?:the\s+)?(.+?)(?:[.,;:\n]|$)", re.IGNORECASE),
]

# CM math font families — these are math notation, not concept names
_MATH_FONT_PREFIXES = ("CMMI", "CMBX", "CMSY", "CMEX", "CMR7", "CMMI7", "CMSY7")


def _is_bold(flags: int) -> bool:
    return bool(flags & (1 << 4))


def _is_italic(flags: int) -> bool:
    return bool(flags & (1 << 1))


def _infer_parent_number(number: str) -> str | None:
    parts = number.rsplit(".", 1)
    if len(parts) == 2:
        return parts[0]
    return None


def _get_first_line_spans(paragraph: ExtractedParagraph) -> list[SpanData]:
    if paragraph.lines:
        return paragraph.lines[0].spans
    return []


def _word_count(text: str) -> int:
    return len(text.split())


def _dominant_font_family(paragraph: ExtractedParagraph) -> str | None:
    """Get the font family with the most characters in this paragraph."""
    if not paragraph.lines:
        return None
    from collections import Counter
    font_chars: Counter[str] = Counter()
    for line in paragraph.lines:
        for span in line.spans:
            font_chars[span.font] += len(span.text.strip())
    if not font_chars:
        return None
    return font_chars.most_common(1)[0][0]


def _is_math_font(font_name: str) -> bool:
    """Check if a font is a CM math font (not body text, not concept text)."""
    return any(font_name.startswith(prefix) for prefix in _MATH_FONT_PREFIXES)


def _is_math_symbol(text: str) -> bool:
    """Check if text is a single math variable/symbol, not a concept name."""
    stripped = text.strip()
    if len(stripped) <= 2:
        return True
    if all(not c.isalnum() for c in stripped):
        return True
    return False


def _clean_concept_name(name: str) -> str:
    """Normalize a concept name — strip artifacts that aren't part of the real name."""
    cleaned = name.strip()
    # Strip trailing period from Algorithm captions: "Algorithm 3.2 Least Angle Regression." -> no trailing dot
    if cleaned.startswith('Algorithm') and cleaned.endswith('.'):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def _is_garbage_concept(name: str, page_number: int = -1, total_pages: int = -1) -> bool:
    """Filter out names that are clearly not real concepts."""
    stripped = name.strip()
    # Hyphenated line-break fragments: "dictio-", "ir-", "prob-"
    if stripped.endswith("-"):
        return True
    # Starts with quote/paren fragment
    if stripped.startswith('"') or stripped.startswith('\u201c') or stripped.startswith('('):
        return True
    # Too short after stripping
    if len(stripped) < 3:
        return True
    # Repeated characters / scatter plot data points: "ooo", "oo\no"
    alpha_only = re.sub(r'[^a-zA-Z]', '', stripped)
    if alpha_only and len(set(alpha_only)) <= 1:
        return True
    # Contains newlines (multi-line fragments from figures)
    if '\n' in stripped:
        return True
    # Looks like a person's name (proper noun patterns)
    if re.match(r'^[A-Z][a-z]+,?\s+(?:and\s+)?[A-Z][a-z]+', stripped):
        return True
    # Front matter (first 20 pages of a book)
    if 0 <= page_number < 20:
        return True
    # All lowercase single word that's a common variable name
    if re.match(r'^[a-z]{1,6}$', stripped) and stripped not in (
        'lasso', 'ridge', 'bagging', 'boosting', 'kernel',
    ):
        return True
    # URL
    if 'http' in stripped or 'www' in stripped:
        return True

    # --- Additional garbage filters ---

    # 1. Block names starting with "a " or "an " (text fragments like "a cubic spline")
    if re.match(r'^a(?:n)?\s+', stripped, re.IGNORECASE):
        return True

    # 2. Reject unmatched parentheses ("cross-entropy)", "Schwarz criterion (Schwarz")
    if stripped.count('(') != stripped.count(')'):
        return True

    # 3. Reject unmatched quotes ('an "item set')
    if stripped.count('"') % 2 != 0:
        return True

    # 4. Block table/figure label patterns (Row 100, Dimension 1, Net-1, Size of Training Set)
    if re.match(r'^(?:Row|Dimension|Net|Column|Size of|Number of)\b', stripped):
        return True

    # 5. Block "Example:" prefix and "Note for" prefix
    if stripped.startswith('Example:') or stripped.startswith('Note for'):
        return True

    # 6. Block math formula fragments ("˜xk = (¯xk1", "TRULE =", "where ϵ is")
    if '=' in stripped and not stripped.startswith('Algorithm'):
        return True
    if stripped.startswith('where ') or stripped.startswith('Where '):
        return True

    # 7. (Algorithm trailing period stripping handled by _clean_concept_name)

    # 8. Block figure legend entries ("K-means - 5 Prototypes per Class", "ROC Curves for String Kernel")
    if re.search(r'\d+\s+(?:Prototypes?|Subclass(?:es)?|Curves?|Subset)\b', stripped):
        return True

    # 9. Block dataset-specific / non-concept stop terms
    if stripped in _GARBAGE_STOP_TERMS:
        return True

    # 10. Block names containing "ordered by" or "marked"
    if 'ordered by' in stripped.lower() or 'marked' in stripped.lower():
        return True

    # 11. Block "Lack of" / "Instability of" / "Relationship of" / "Computations for" prefixes
    if re.match(r'^(?:Lack of|Instability of|Relationship of|Computations for)\b', stripped):
        return True

    # 12. Block long names with commas (text fragments like "lcp, gleason, and pgg45. We get")
    if ', ' in stripped and len(stripped) > 30:
        return True

    # 13. Reject names ending with "of X" where X is a single uppercase letter
    if re.search(r'\bof\s+[A-Z]$', stripped):
        return True

    # 14. Reject names containing " or " (text fragments like "canonical or discriminant")
    if ' or ' in stripped.lower() and not stripped.lower().startswith('leave-one-out'):
        return True

    # 15. Reject names containing " if " (text fragments like "adjacent if there")
    if ' if ' in stripped.lower():
        return True

    # 16. Block names containing "/" (figure legend entries like "FDA / MARS - Degree 2")
    if '/' in stripped:
        return True

    # 17. Block names ending with common truncation words (cut-off phrases)
    truncation_endings = {'multiple', 'linear', 'Monte', 'forward', 'particular', 'general', 'simple', 'various'}
    last_word = stripped.rsplit(None, 1)[-1] if stripped else ''
    if last_word in truncation_endings:
        return True

    # 18. Block "N-Nearest Neighbor" figure label patterns (the real concept is "k-nearest neighbors")
    if re.match(r'^\d+-Nearest\b', stripped):
        return True

    # 19. Block names starting with "procedure " (malformed extractions)
    if stripped.lower().startswith('procedure '):
        return True

    # 20. Block parenthetical chapter/section references ("weight decay (Chapter 11)")
    if re.search(r'\(Chapter\s+\d+\)', stripped):
        return True

    # 21. Block "ROC Curves for" and similar figure title patterns
    if re.match(r'^ROC\s+Curves?\b', stripped):
        return True

    return False


# Dataset-specific and non-concept terms to reject outright
_GARBAGE_STOP_TERMS = frozenset({
    "AveRooms", "Obesity", "Wind", "RESTRICTED", "Hinton", "children",
    "Iteration", "ﬁrst", "responses", "targets", "experts",
    "two functions", "loadings", "discriminant", "encoding",
    "PKA", "tensor-product scenario", "Specificity",
})




class ConceptExtractor:
    """Extract sections and concepts from classified PDF paragraphs."""

    def __init__(self) -> None:
        pass

    def extract(
        self,
        pages: list[ExtractedPage],
        classifications: dict[tuple[int, int], str],
        total_pages: int = 0,
    ) -> ExtractionResult:
        result = ExtractionResult()
        current_section_number: str | None = None
        seen_terms: set[str] = set()
        seen_section_numbers: set[str] = set()  # dedup numbered sections by number only
        seen_unnumbered_sections: set[str] = set()  # dedup unnumbered sections by title

        for page in pages:
            paragraphs = page.paragraphs
            for i, paragraph in enumerate(paragraphs):
                key = (paragraph.page_number, paragraph.sequence_index)
                ptype = classifications.get(key)
                if ptype is None:
                    continue

                if ptype == "section_header":
                    section = self._extract_section(paragraph)
                    # Deduplicate running headers: for numbered sections, key on number only
                    # (running headers produce truncated title variants for the same section)
                    if section.number is not None:
                        if section.number in seen_section_numbers:
                            current_section_number = section.number
                            continue
                        seen_section_numbers.add(section.number)
                    else:
                        if section.title in seen_unnumbered_sections:
                            continue
                        seen_unnumbered_sections.add(section.title)
                    result.sections.append(section)
                    current_section_number = section.number

                elif ptype == "definition":
                    concept = self._extract_definition(paragraph, current_section_number)
                    if concept:
                        concept.name = _clean_concept_name(concept.name)
                    if concept and concept.name.lower() not in seen_terms:
                        if not _is_garbage_concept(concept.name, paragraph.page_number, total_pages):
                            seen_terms.add(concept.name.lower())
                            result.concepts.append(concept)

                elif ptype in ("theorem", "lemma", "corollary"):
                    concept = self._extract_theorem(paragraph, ptype, current_section_number)
                    if concept:
                        concept.name = _clean_concept_name(concept.name)
                    if concept and concept.name.lower() not in seen_terms:
                        seen_terms.add(concept.name.lower())
                        result.concepts.append(concept)

                elif ptype == "narrative":
                    # Strategy 1: sub-header concepts (short Helvetica paragraphs)
                    subheader = self._extract_subheader_concept(
                        paragraph, paragraphs, i, current_section_number, seen_terms,
                        classifications, total_pages,
                    )
                    if subheader:
                        subheader.name = _clean_concept_name(subheader.name)
                        seen_terms.add(subheader.name.lower())
                        result.concepts.append(subheader)
                        continue

                    # Strategy 2: textual introductions ("is called", "known as", etc.)
                    textual = self._extract_textual_introductions(
                        paragraph, current_section_number, seen_terms
                    )
                    for c in textual:
                        c.name = _clean_concept_name(c.name)
                        if not _is_garbage_concept(c.name, paragraph.page_number, total_pages):
                            seen_terms.add(c.name.lower())
                            result.concepts.append(c)

        return result

    # ------------------------------------------------------------------
    # Section extraction
    # ------------------------------------------------------------------

    def _extract_section(self, paragraph: ExtractedParagraph) -> ExtractedSection:
        text = paragraph.text.strip()
        m = _SECTION_NUMBER_RE.match(text)
        if m:
            number = m.group(1)
            title = m.group(2).strip()
            parent = _infer_parent_number(number)
            return ExtractedSection(
                number=number,
                title=title,
                page_number=paragraph.page_number,
                parent_number=parent,
            )
        return ExtractedSection(
            number=None,
            title=text,
            page_number=paragraph.page_number,
            parent_number=None,
        )

    # ------------------------------------------------------------------
    # Definition extraction
    # ------------------------------------------------------------------

    def _extract_definition(
        self, paragraph: ExtractedParagraph, current_section: str | None
    ) -> ExtractedConcept | None:
        text = paragraph.text.strip()
        key = (paragraph.page_number, paragraph.sequence_index)

        term = self._bold_italic_term_from_first_line(paragraph)

        if not term:
            qm = _QUOTED_TERM_RE.search(text.split("\n")[0])
            if qm:
                term = qm.group(1).strip()

        if not term:
            dm = _DEFINITION_PREFIX_RE.match(text)
            if dm:
                rest = dm.group(1).strip()
                chunk = re.split(r"[.,;:\n]", rest)[0].strip()
                if chunk and _word_count(chunk) <= 4:
                    term = chunk

        if not term:
            first_line = text.split("\n")[0]
            chunk = re.split(r"[.,;:]", first_line)[0].strip()
            if chunk and _word_count(chunk) <= 4:
                term = chunk

        if not term:
            return None

        # Reject hyphenated line-break fragments ("prob-", "ir-")
        if term.endswith("-"):
            return None
        # Reject terms ending with prepositions/articles (incomplete phrases)
        last_word = term.split()[-1].lower() if term.split() else ""
        if last_word in ("for", "of", "from", "the", "a", "an", "in", "on", "to", "with", "and", "or", "by", "as"):
            return None

        return ExtractedConcept(
            name=term,
            description=text,
            concept_type="definition",
            source_paragraph_indices=[key],
            section_number=current_section,
        )

    # ------------------------------------------------------------------
    # Theorem / Lemma / Corollary extraction
    # ------------------------------------------------------------------

    def _extract_theorem(
        self,
        paragraph: ExtractedParagraph,
        ptype: str,
        current_section: str | None,
    ) -> ExtractedConcept | None:
        text = paragraph.text.strip()
        key = (paragraph.page_number, paragraph.sequence_index)

        m = _THEOREM_RE.match(text)
        if m:
            kind = m.group(1).capitalize()
            num = m.group(2)
            named = m.group(3)
            if named:
                name = f"{kind} {num} ({named})"
            else:
                name = f"{kind} {num}"
        else:
            name = text.split("\n")[0].strip()

        return ExtractedConcept(
            name=name,
            description=text,
            concept_type=ptype,
            source_paragraph_indices=[key],
            section_number=current_section,
        )

    # ------------------------------------------------------------------
    # Sub-header concept extraction (e.g., "Ridge Regression" in Helvetica)
    # ------------------------------------------------------------------

    def _extract_subheader_concept(
        self,
        paragraph: ExtractedParagraph,
        all_paragraphs: list[ExtractedParagraph],
        index: int,
        current_section: str | None,
        seen_terms: set[str],
        classifications: dict[tuple[int, int], str],
        total_pages: int = 0,
    ) -> ExtractedConcept | None:
        """Extract concept from short sub-header paragraphs in non-body fonts."""
        text = paragraph.text.strip()

        # Must be short (concept name, not body text)
        if len(text) > 60 or _word_count(text) > 6:
            return None

        if _is_math_symbol(text):
            return None
        if re.match(r'^[\d.\s,\-()=+×−]+$', text):
            return None

        # Check font family — must differ from standard CM body fonts
        dominant_font = _dominant_font_family(paragraph)
        if dominant_font is None:
            return None

        is_body_font = dominant_font.startswith("CMR") and dominant_font not in ("CMR7", "CMR5")
        if is_body_font or _is_math_font(dominant_font):
            return None

        if not any(c.isalpha() for c in text):
            return None

        if text.lower() in seen_terms:
            return None
        if _is_garbage_concept(text, paragraph.page_number, total_pages):
            return None

        # Filter axis labels using bounding box analysis
        if paragraph.bbox is not None:
            x0, y0, x1, y1 = paragraph.bbox
            bbox_width = x1 - x0
            bbox_height = y1 - y0
            # Rotated y-axis labels have height >> width
            if bbox_height > bbox_width:
                return None
            # X-axis labels use smaller font (~4.7pt height vs ~7pt for real sub-headers)
            if bbox_height < 5.5:
                return None

        # Skip if near a figure/table caption (likely axis label or legend)
        for offset in range(-3, 4):
            j = index + offset
            if j < 0 or j >= len(all_paragraphs) or j == index:
                continue
            neighbor = all_paragraphs[j]
            neighbor_key = (neighbor.page_number, neighbor.sequence_index)
            neighbor_type = classifications.get(neighbor_key, "")
            if neighbor_type in ("figure_caption", "table_caption"):
                return None

        # Must have a following narrative paragraph (real sub-headers introduce content)
        description = None
        for j in range(index + 1, min(index + 5, len(all_paragraphs))):
            next_para = all_paragraphs[j]
            next_text = next_para.text.strip()
            if len(next_text) > 100:
                description = next_text
                break

        if description is None:
            return None

        key = (paragraph.page_number, paragraph.sequence_index)
        return ExtractedConcept(
            name=text,
            description=description,
            concept_type="method",
            source_paragraph_indices=[key],
            section_number=current_section,
        )

    # ------------------------------------------------------------------
    # Textual introduction extraction ("is called", "known as", etc.)
    # ------------------------------------------------------------------

    def _extract_textual_introductions(
        self,
        paragraph: ExtractedParagraph,
        current_section: str | None,
        seen_terms: set[str],
    ) -> list[ExtractedConcept]:
        """Extract concepts introduced by textual phrases in narrative."""
        text = paragraph.text.strip()
        key = (paragraph.page_number, paragraph.sequence_index)
        concepts = []

        for pattern in _TEXTUAL_INTRO_PATTERNS:
            for match in pattern.finditer(text):
                term = match.group(1).strip()
                # Clean up: remove trailing articles, extra whitespace
                term = re.sub(r'\s+', ' ', term)
                # Reject hyphenated line-break fragments ("prob-", "ir-")
                if term.endswith("-"):
                    continue
                # Reject terms ending with prepositions/articles (incomplete phrases)
                last_word = term.split()[-1].lower() if term.split() else ""
                if last_word in ("for", "of", "from", "the", "a", "an", "in", "on", "to", "with", "and", "or", "by", "as"):
                    continue
                # Must be a reasonable concept name length
                wc = _word_count(term)
                if wc < 1 or wc > 5:
                    continue
                # Skip pure math symbols
                if _is_math_symbol(term):
                    continue
                if _is_garbage_concept(term, paragraph.page_number):
                    continue
                if term.lower() in _STOP_TERMS:
                    continue
                if term.lower() in seen_terms:
                    continue

                concepts.append(ExtractedConcept(
                    name=term,
                    description=text,
                    concept_type="definition",
                    source_paragraph_indices=[key],
                    section_number=current_section,
                ))
                seen_terms.add(term.lower())

        return concepts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bold_italic_term_from_first_line(
        self, paragraph: ExtractedParagraph
    ) -> str | None:
        """Return the first bold or italic span text from the first line, if short enough.
        Only for non-math fonts."""
        spans = _get_first_line_spans(paragraph)
        for span in spans:
            if _is_math_font(span.font):
                continue
            if _is_bold(span.flags) or _is_italic(span.flags):
                term = span.text.strip()
                if term and _word_count(term) <= 4 and not _is_math_symbol(term):
                    return term
        return None


# Common words that shouldn't be extracted as concepts
_STOP_TERMS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "it", "its", "we", "our", "they", "their",
    "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might",
    "not", "no", "yes", "so", "if", "then",
    "and", "or", "but", "with", "from", "to", "of", "in", "on", "at", "by", "for",
    "more", "less", "most", "least", "very", "quite",
    "new", "old", "large", "small", "simple", "complex",
    "first", "second", "third", "last", "next", "previous",
    "same", "different", "similar", "other", "each", "every",
    "all", "some", "any", "both", "either", "neither",
    "scalar", "vector", "matrix", "function", "variable", "parameter",
    "equation", "formula", "expression", "result", "solution",
    "problem", "method", "approach", "technique", "procedure",
    "case", "example", "way", "form", "type", "kind",
    "figure", "table", "chapter", "section", "page",
})
