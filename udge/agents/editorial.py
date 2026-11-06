"""Editorial and Consistency Agent."""
from typing import List
from udge.core.models import GeneratedSection
from udge.llm.provider_base import BaseLLMProvider
from udge.prompt_engine.builder import PromptBuilder

class EditorialAgent:
    """Reviews generated draft sections for flow, consistency, and citation integrity."""

    def __init__(self, llm_provider: BaseLLMProvider, prompt_builder: PromptBuilder):
        self.llm = llm_provider
        self.prompt_builder = prompt_builder

    def review_sections(
        self,
        doc_title: str,
        sections: List[GeneratedSection]
    ) -> List[GeneratedSection]:
        """Performs editorial review on draft sections."""
        polished: List[GeneratedSection] = []

        for sec in sections:
            # If section contains critical missing info or is empty, keep without modifying
            if not sec.content or "[MISSING_INFORMATION:" in sec.content:
                sec.status = "reviewed"
                polished.append(sec)
                continue

            system_prompt, user_prompt = self.prompt_builder.build_editorial_prompt(
                doc_title=doc_title,
                section_title=sec.title,
                draft_content=sec.content
            )

            # In mock mode, we preserve content; in live mode, we apply LLM polish
            try:
                # To maintain citation guarantees, if LLM polish drops citations, revert to draft
                reviewed_text = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)
                if all(cit in reviewed_text for cit in sec.inline_citations):
                    sec.content = reviewed_text
            except Exception:
                # Keep original draft if review call encounters an issue
                pass

            sec.status = "reviewed"
            polished.append(sec)

        return polished
