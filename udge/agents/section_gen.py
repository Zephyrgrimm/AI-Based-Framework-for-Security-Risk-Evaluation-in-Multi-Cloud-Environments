"""Section Generation Agent."""
import re
from typing import List
from udge.core.models import TemplateSpec, TemplateSection, EvidenceChunk, GeneratedSection
from udge.prompt_engine.builder import PromptBuilder
from udge.llm.provider_base import BaseLLMProvider

CITATION_REGEX = re.compile(r"\[Source:\s*([^\]]+)\]")
MISSING_INFO_REGEX = re.compile(r"\[MISSING_INFORMATION:\s*([^\]]+)\]")

class SectionGenAgent:
    """Generates draft content for a specific template section using grounded evidence."""

    def __init__(self, llm_provider: BaseLLMProvider, prompt_builder: PromptBuilder):
        self.llm = llm_provider
        self.prompt_builder = prompt_builder

    def generate_section(
        self,
        spec: TemplateSpec,
        section: TemplateSection,
        evidence_chunks: List[EvidenceChunk]
    ) -> GeneratedSection:
        """Executes LLM generation for a single section."""
        system_prompt, user_prompt = self.prompt_builder.build_section_prompt(
            spec=spec,
            section=section,
            evidence_chunks=evidence_chunks
        )

        raw_output = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        # Extract citations
        citations = CITATION_REGEX.findall(raw_output)
        missing_flags = MISSING_INFO_REGEX.findall(raw_output)

        return GeneratedSection(
            section_id=section.id,
            title=section.title,
            level=section.level,
            content=raw_output,
            inline_citations=citations,
            missing_info_flags=missing_flags,
            status="drafted"
        )
