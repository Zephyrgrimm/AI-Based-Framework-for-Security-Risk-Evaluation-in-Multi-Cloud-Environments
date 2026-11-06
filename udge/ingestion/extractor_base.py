"""Base interface for all document extractors."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from udge.core.models import EvidenceChunk

class BaseExtractor(ABC):
    """Abstract base class for document format extractors."""

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Returns True if this extractor can process the given file."""
        pass

    @abstractmethod
    def extract(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        """Extracts text, tables, and images from the file into structured EvidenceChunks."""
        pass
