"""Unified document ingestion pipeline."""
from pathlib import Path
from typing import List, Optional
from udge.core.exceptions import IngestionError
from udge.core.models import EvidenceCatalog, EvidenceChunk
from udge.ingestion.extractor_base import BaseExtractor
from udge.ingestion.text_extractor import TextExtractor
from udge.ingestion.office_extractor import OfficeExtractor
from udge.ingestion.pdf_extractor import PDFExtractor
from udge.ingestion.ocr_extractor import OCRExtractor

class IngestionPipeline:
    """Orchestrates format detection and extraction across all input files."""

    def __init__(self, extractors: Optional[List[BaseExtractor]] = None):
        ocr = OCRExtractor()
        self.extractors: List[BaseExtractor] = extractors or [
            TextExtractor(),
            OfficeExtractor(),
            PDFExtractor(ocr_extractor=ocr),
            ocr
        ]

    def ingest_files(self, file_paths: List[Path], output_dir: Path) -> EvidenceCatalog:
        """Processes all provided files and returns a unified EvidenceCatalog."""
        catalog = EvidenceCatalog()
        output_dir.mkdir(parents=True, exist_ok=True)

        for f_path in file_paths:
            p = Path(f_path).resolve()
            if not p.exists():
                raise IngestionError(f"Input file not found: {p}")

            catalog.source_files.append(p.name)
            handler = self._find_extractor(p)

            if not handler:
                raise IngestionError(
                    f"Unsupported file format: '{p.suffix}' for file '{p.name}'. "
                    f"Supported formats: .md, .txt, .csv, .docx, .pptx, .xlsx, .pdf, images (.png, .jpg, .tiff, etc.)"
                )

            try:
                chunks = handler.extract(p, output_dir)
                catalog.chunks.extend(chunks)

                # Collect all extracted images for figure catalog
                for c in chunks:
                    for img_p in c.image_paths:
                        catalog.extracted_images.append({
                            "source_file": p.name,
                            "location": c.location,
                            "path": img_p
                        })
            except Exception as e:
                raise IngestionError(f"Failed to extract content from '{p.name}': {e}") from e

        return catalog

    def _find_extractor(self, file_path: Path) -> Optional[BaseExtractor]:
        for extractor in self.extractors:
            if extractor.can_handle(file_path):
                return extractor
        return None
