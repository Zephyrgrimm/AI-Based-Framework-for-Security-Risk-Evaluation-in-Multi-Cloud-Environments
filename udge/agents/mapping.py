"""Content Mapping Agent that correlates evidence chunks to template sections."""
import re
from typing import List, Set
from udge.core.models import (
    TemplateSpec,
    TemplateSection,
    EvidenceCatalog,
    EvidenceChunk,
    SectionMapping,
    ContentMappingPlan
)

class ContentMappingAgent:
    """Aligns evidence chunks to template sections and identifies critical content gaps."""

    def map_content(self, spec: TemplateSpec, catalog: EvidenceCatalog) -> ContentMappingPlan:
        plan = ContentMappingPlan()
        all_assigned_chunk_ids: Set[str] = set()

        for section in spec.sections:
            mapping = self._map_section(section, catalog.chunks)
            plan.mappings.append(mapping)
            for cid in mapping.relevant_chunk_ids:
                all_assigned_chunk_ids.add(cid)

            if not mapping.relevant_chunk_ids and section.required:
                plan.critical_gaps.append(
                    f"Section '{section.title}' has no matching source evidence."
                )

        # Record unassigned chunks
        for chunk in catalog.chunks:
            if chunk.id not in all_assigned_chunk_ids:
                plan.unassigned_chunks.append(chunk.id)

        return plan

    def _map_section(self, section: TemplateSection, chunks: List[EvidenceChunk]) -> SectionMapping:
        relevant_ids: List[str] = []
        section_tokens = self._extract_keywords(f"{section.title} {section.instructions} {section.raw_markdown}")

        for chunk in chunks:
            chunk_tokens = self._extract_keywords(f"{chunk.content} {chunk.location}")
            # Compute token overlap
            overlap = section_tokens.intersection(chunk_tokens)
            score = len(overlap) / max(len(section_tokens), 1)

            # Match criteria: direct title hit or high token overlap
            has_title_match = any(word in chunk.content.lower() for word in section.title.lower().split() if len(word) > 3)
            if score > 0.15 or has_title_match:
                relevant_ids.append(chunk.id)

        coverage_score = 1.0 if relevant_ids else 0.0
        missing_fields = []
        if not relevant_ids and section.required:
            missing_fields.append(f"Source evidence for '{section.title}'")

        return SectionMapping(
            section_id=section.id,
            section_title=section.title,
            relevant_chunk_ids=relevant_ids,
            missing_fields=missing_fields,
            coverage_score=coverage_score
        )

    def _extract_keywords(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "this", "that", "from", "are", "was",
            "section", "provide", "include", "overview", "document", "report"
        }
        return set(w for w in words if w not in stopwords)
