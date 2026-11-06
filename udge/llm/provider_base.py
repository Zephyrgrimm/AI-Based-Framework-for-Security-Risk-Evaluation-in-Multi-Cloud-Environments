"""Base interface for LLM providers in UDGE."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class BaseLLMProvider(ABC):
    """Abstract base class for LLM text and multimodal generation."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generates text from prompt and system prompt."""
        pass

    @abstractmethod
    def generate_vision(self, prompt: str, image_path: Path) -> str:
        """Processes an image and returns a text transcription or description."""
        pass
