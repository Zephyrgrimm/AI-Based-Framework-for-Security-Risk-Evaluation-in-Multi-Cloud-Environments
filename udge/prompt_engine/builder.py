"""Prompt builder that composes task-specific prompts from modular components."""
from typing import List
from udge.core.models import TemplateSpec, TemplateSection, EvidenceChunk
from udge.prompt_engine.templates import (
    SYSTEM_GROUNDING_RULES,
    SECTION_GENERATION_TEMPLATE,
    EDITORIAL_REVIEW_TEMPLATE
)

class PromptBuilder:
    """Constructs focused, section-level prompts with grounding constraints."""

    def build_section_prompt(
        self,
        spec: TemplateSpec,
        section: TemplateSection,
        evidence_chunks: List[EvidenceChunk]
    ) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt) for generating a single section."""
        system_prompt = SYSTEM_GROUNDING_RULES.strip()

        evidence_str_list = []
        for c in evidence_chunks:
            tables_repr = ""
            if c.tables:
                tables_repr = "\nTables:\n" + str(c.tables)
            evidence_str_list.append(
                f"[Evidence Chunk {c.id} ({c.source_file}, {c.location})]:\n"
                f"{c.content}{tables_repr}"
            )

        evidence_blocks = "\n\n".join(evidence_str_list) if evidence_str_list else "[No matching source evidence found]"

        placeholders_str = "\n".join([f"- Placeholder: {p}" for p in section.placeholder_tokens]) if section.placeholder_tokens else "None"
        word_count_hint = f"~{section.expected_word_count} words" if section.expected_word_count else "Appropriate depth for topic"

        user_prompt = SECTION_GENERATION_TEMPLATE.format(
            category=spec.document_category.value,
            doc_title=spec.title,
            section_title=section.title,
            level=section.level,
            instructions=section.instructions or "Elaborate based on evidence.",
            placeholders=placeholders_str,
            word_count_hint=word_count_hint,
            evidence_blocks=evidence_blocks
        )

        return system_prompt, user_prompt

    def build_editorial_prompt(
        self,
        doc_title: str,
        section_title: str,
        draft_content: str
    ) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt) for editorial polish."""
        system_prompt = (
            "You are a professional editor. Enhance tone and clarity while preserving all facts, "
            "citations, and bracketed notices."
        )
        user_prompt = EDITORIAL_REVIEW_TEMPLATE.format(
            doc_title=doc_title,
            section_title=section_title,
            draft_content=draft_content
        )
        return system_prompt, user_prompt
