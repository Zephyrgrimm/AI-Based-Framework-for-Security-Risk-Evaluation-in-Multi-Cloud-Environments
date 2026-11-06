"""Deterministic offline mock LLM provider for testing and offline runs."""
import re
from pathlib import Path
from udge.llm.provider_base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """Offline deterministic provider that synthesizes grounded text from prompt context."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # Check if the prompt includes evidence blocks
        evidence_matches = re.findall(r"\[Evidence Chunk\s+([a-zA-Z0-9_\-]+)\s*\(([^)]+)\)\]:\s*([\s\S]*?)(?=\[Evidence Chunk|\Z)", prompt)

        section_title_match = re.search(r"Section:\s*(.*)", prompt)
        section_title = section_title_match.group(1).strip() if section_title_match else "Overview"

        paragraphs = []
        citations = []

        if evidence_matches:
            for chunk_id, location, text in evidence_matches:
                cleaned_text = text.strip()
                # Take key sentences
                first_lines = [line.strip() for line in cleaned_text.splitlines() if line.strip() and not line.strip().startswith("|")]
                summary = " ".join(first_lines[:3]) if first_lines else cleaned_text[:200]
                citation = f"[Source: {location}]"
                citations.append(citation)
                paragraphs.append(f"Regarding {section_title}, the source materials indicate: {summary} {citation}")
        else:
            paragraphs.append(
                f"[MISSING_INFORMATION: Insufficient source evidence provided for section '{section_title}']"
            )

        # Check if placeholders were requested in prompt
        placeholder_matches = re.findall(r"Placeholder:\s*([A-Za-z0-9_\{\}\[\]\<\>\s]+)", prompt)
        for ph in placeholder_matches:
            paragraphs.append(f"Note: Specific requirements for {ph.strip()} were integrated into this section.")

        return "\n\n".join(paragraphs)

    def generate_vision(self, prompt: str, image_path: Path) -> str:
        return (
            f"[Visual Content Extracted from {image_path.name}]: "
            f"Image elements, data plots, and visual labels have been transcribed for technical synthesis."
        )
