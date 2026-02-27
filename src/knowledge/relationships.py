"""Relationship mapper - Infer relationships between extracted concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.knowledge.extractor import ExtractedConcept, ExtractedSection


@dataclass
class InferredRelationship:
    source_name: str  # concept name
    target_name: str  # concept name
    relationship_type: str  # "prerequisite", "generalizes", "special_case_of", "proved_by", "example_of", "contrasts_with", "uses"
    confidence: float  # 0.0-1.0, for filtering
    evidence: str  # brief explanation of why this relationship was inferred


def _parent_section(number: str) -> str | None:
    """Return the parent section number, or None if top-level.

    '3.2.1' -> '3.2', '3.1' -> '3', '3' -> None
    """
    parts = number.rsplit(".", 1)
    if len(parts) == 1:
        return None
    return parts[0]


def _concept_name_pattern(name: str) -> re.Pattern:
    """Build a word-boundary regex for case-insensitive matching of a concept name."""
    escaped = re.escape(name)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def _mentions(description: str, name: str) -> bool:
    """Check if description mentions the concept name as a whole word, case-insensitive."""
    return bool(_concept_name_pattern(name).search(description))


def _find_mentioned_concept_name(text: str, concept_names: list[str]) -> str | None:
    """Find first concept name mentioned in text (whole word, case-insensitive)."""
    for name in concept_names:
        if _mentions(text, name):
            return name
    return None


class RelationshipMapper:
    """Infers relationships between concepts based on ordering, hierarchy, and textual cues."""

    def __init__(self) -> None:
        pass

    def infer(
        self,
        concepts: list[ExtractedConcept],
        sections: list[ExtractedSection],
    ) -> list[InferredRelationship]:
        results: list[InferredRelationship] = []
        concept_names = [c.name for c in concepts]
        section_map: dict[str, ExtractedSection] = {
            s.number: s for s in sections if s.number is not None
        }

        # Build a lookup from concept name to concept
        name_to_concept: dict[str, ExtractedConcept] = {c.name: c for c in concepts}

        results.extend(self._ordering_prerequisites(concepts, section_map))
        results.extend(self._section_hierarchy(concepts))
        results.extend(self._textual_references(concepts, concept_names, name_to_concept))

        return self._deduplicate(results)

    # ------------------------------------------------------------------
    # Ordering-based (prerequisite)
    # ------------------------------------------------------------------

    def _ordering_prerequisites(
        self,
        concepts: list[ExtractedConcept],
        section_map: dict[str, ExtractedSection],
    ) -> list[InferredRelationship]:
        """Only infer prerequisite when A is in the same section as B, appears before B,
        and B's description explicitly mentions A by name."""
        results: list[InferredRelationship] = []

        # Group concepts by section for efficiency
        by_section: dict[str, list[ExtractedConcept]] = {}
        for c in concepts:
            if c.section_number:
                by_section.setdefault(c.section_number, []).append(c)

        for section_num, section_concepts in by_section.items():
            for i, a in enumerate(section_concepts):
                # Only check concepts that come after A in the same section
                for b in section_concepts[i + 1:]:
                    # Require A's name to be at least 4 chars to avoid matching noise
                    if len(a.name) < 4:
                        continue
                    if _mentions(b.description, a.name):
                        results.append(InferredRelationship(
                            source_name=a.name,
                            target_name=b.name,
                            relationship_type="prerequisite",
                            confidence=0.7,
                            evidence=f"'{a.name}' appears before '{b.name}' in section {section_num} and is mentioned in its description",
                        ))

        return results

    # ------------------------------------------------------------------
    # Section hierarchy (generalizes)
    # ------------------------------------------------------------------

    def _section_hierarchy(
        self,
        concepts: list[ExtractedConcept],
    ) -> list[InferredRelationship]:
        """Only infer generalizes when B's description mentions A and A is in the parent section."""
        results: list[InferredRelationship] = []

        # Index concepts by section
        by_section: dict[str, list[ExtractedConcept]] = {}
        for c in concepts:
            if c.section_number:
                by_section.setdefault(c.section_number, []).append(c)

        for b in concepts:
            if not b.section_number:
                continue
            parent = _parent_section(b.section_number)
            if parent is None or parent not in by_section:
                continue
            for a in by_section[parent]:
                if len(a.name) < 4:
                    continue
                if _mentions(b.description, a.name):
                    results.append(InferredRelationship(
                        source_name=a.name,
                        target_name=b.name,
                        relationship_type="generalizes",
                        confidence=0.5,
                        evidence=f"'{a.name}' is in parent section {a.section_number} of '{b.name}' in section {b.section_number}",
                    ))

        return results

    # ------------------------------------------------------------------
    # Explicit textual references
    # ------------------------------------------------------------------

    def _textual_references(
        self,
        concepts: list[ExtractedConcept],
        concept_names: list[str],
        name_to_concept: dict[str, ExtractedConcept],
    ) -> list[InferredRelationship]:
        results: list[InferredRelationship] = []

        # Patterns: (regex, handler_function)
        # Each handler returns (source_name, target_name, rel_type, confidence, evidence) or None
        patterns: list[tuple[re.Pattern, str, str, float]] = [
            # "a special case of X" -> (X, this_concept, "generalizes"), 0.9
            (re.compile(r"(?:a\s+)?special\s+case\s+of\s+", re.IGNORECASE), "special_case_of", "generalizes", 0.9),
            # "generalizes X" / "generalization of X" -> (this_concept, X, "generalizes"), 0.9
            (re.compile(r"generali[sz](?:es|ation\s+of)\s+", re.IGNORECASE), "generalizes", "generalizes", 0.9),
            # "using X" / "based on X" / "relies on X" -> (X, this_concept, "prerequisite"), 0.8
            (re.compile(r"(?:using|based\s+on|relies\s+on)\s+", re.IGNORECASE), "uses_prereq", "prerequisite", 0.8),
            # "proved by" / "proof follows from" -> (referenced, this_concept, "proved_by"), 0.8
            (re.compile(r"(?:proved\s+by|proof\s+follows\s+from)\s+", re.IGNORECASE), "proved_by", "proved_by", 0.8),
            # "for example" + nearby concept -> (this_concept, example_concept, "example_of"), 0.6
            (re.compile(r"for\s+example\s+", re.IGNORECASE), "example_of", "example_of", 0.6),
            # "in contrast to X" / "unlike X" / "compared to X" -> (this_concept, X, "contrasts_with"), 0.7
            (re.compile(r"(?:in\s+contrast\s+to|unlike|compared\s+to)\s+", re.IGNORECASE), "contrasts_with", "contrasts_with", 0.7),
            # "see Theorem/Lemma/Section X" -> (this_concept, X, "uses"), 0.6
            (re.compile(r"see\s+(?:Theorem|Lemma|Section)\s+", re.IGNORECASE), "see_ref", "uses", 0.6),
        ]

        for concept in concepts:
            desc = concept.description
            if not desc:
                continue

            for pattern, tag, rel_type, confidence in patterns:
                for match in pattern.finditer(desc):
                    # The text after the pattern match - look for a concept name
                    after_text = desc[match.end():]
                    referenced = _find_mentioned_concept_name(after_text, concept_names)
                    if referenced is None or referenced == concept.name:
                        continue

                    if tag == "special_case_of":
                        # (X, this_concept, "generalizes")
                        results.append(InferredRelationship(
                            source_name=referenced,
                            target_name=concept.name,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' described as special case of '{referenced}'",
                        ))
                    elif tag == "generalizes":
                        # (this_concept, X, "generalizes")
                        results.append(InferredRelationship(
                            source_name=concept.name,
                            target_name=referenced,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' described as generalizing '{referenced}'",
                        ))
                    elif tag == "uses_prereq":
                        # (X, this_concept, "prerequisite")
                        results.append(InferredRelationship(
                            source_name=referenced,
                            target_name=concept.name,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' described as based on/using '{referenced}'",
                        ))
                    elif tag == "proved_by":
                        # (referenced, this_concept, "proved_by")
                        results.append(InferredRelationship(
                            source_name=referenced,
                            target_name=concept.name,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' described as proved by '{referenced}'",
                        ))
                    elif tag == "example_of":
                        # (this_concept, example_concept, "example_of")
                        results.append(InferredRelationship(
                            source_name=concept.name,
                            target_name=referenced,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{referenced}' referenced as example near '{concept.name}'",
                        ))
                    elif tag == "contrasts_with":
                        # (this_concept, X, "contrasts_with")
                        results.append(InferredRelationship(
                            source_name=concept.name,
                            target_name=referenced,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' described in contrast to '{referenced}'",
                        ))
                    elif tag == "see_ref":
                        # (this_concept, X, "uses")
                        results.append(InferredRelationship(
                            source_name=concept.name,
                            target_name=referenced,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence=f"'{concept.name}' references '{referenced}' via see-reference",
                        ))

        return results

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(
        relationships: list[InferredRelationship],
    ) -> list[InferredRelationship]:
        """Keep only the highest-confidence entry for each (source, target, type) triple."""
        best: dict[tuple[str, str, str], InferredRelationship] = {}
        for rel in relationships:
            key = (rel.source_name, rel.target_name, rel.relationship_type)
            if key not in best or rel.confidence > best[key].confidence:
                best[key] = rel
        return list(best.values())
