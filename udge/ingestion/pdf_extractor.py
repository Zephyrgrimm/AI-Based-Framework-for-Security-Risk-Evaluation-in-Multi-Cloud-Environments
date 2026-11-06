"""Hybrid PDF extractor supporting digital text and scanned/image pages via OCR."""
from pathlib import Path
from typing import List, Optional
import uuid
import pypdf
import pypdfium2
from udge.core.config import config
from udge.core.models import EvidenceChunk, SourceType
from udge.ingestion.extractor_base import BaseExtractor
from udge.ingestion.ocr_extractor import OCRExtractor

class PDFExtractor(BaseExtractor):
    """Extracts text, embedded images, and OCRs scanned pages from PDF documents."""

    def __init__(self, ocr_extractor: Optional[OCRExtractor] = None):
        self.ocr_extractor = ocr_extractor or OCRExtractor()

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        chunks: List[EvidenceChunk] = []

        rendered_dir = output_dir / "rendered_pages"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "extracted_images"
        img_dir.mkdir(parents=True, exist_ok=True)

        reader = pypdf.PdfReader(str(file_path))
        num_pages = len(reader.pages)

        # Open pypdfium2 document for rendering scanned pages
        pdf_render_doc = None
        try:
            pdf_render_doc = pypdfium2.PdfDocument(str(file_path))
        except Exception:
            pass

        for page_idx in range(num_pages):
            page_num = page_idx + 1
            page = reader.pages[page_idx]

            # Extract digital text
            text = (page.extract_text() or "").strip()

            # Extract embedded images on this page
            embedded_img_paths: List[str] = []
            try:
                for img_idx, img_obj in enumerate(page.images):
                    img_name = f"{file_path.stem}_p{page_num}_img{img_idx+1}_{img_obj.name}"
                    dest = img_dir / img_name
                    dest.write_bytes(img_obj.data)
                    embedded_img_paths.append(str(dest))
            except Exception:
                pass

            # Classification: digital text vs. scanned / image page
            if len(text) < config.min_pdf_text_density_per_page:
                # Scanned or image-heavy page: Render page to image and run OCR
                page_img_path = rendered_dir / f"{file_path.stem}_page_{page_num}.png"
                rendered = False

                if pdf_render_doc:
                    try:
                        render_page = pdf_render_doc.get_page(page_idx)
                        pil_img = render_page.render(scale=config.ocr_dpi / 72).to_pil()
                        pil_img.save(page_img_path)
                        rendered = True
                    except Exception:
                        pass

                if rendered and page_img_path.exists():
                    ocr_chunk = self.ocr_extractor.extract_from_image(
                        page_img_path,
                        location=f"Page {page_num} (Scanned Image/OCR)",
                        is_pdf_page=True
                    )
                    ocr_chunk.source_file = file_path.name
                    ocr_chunk.image_paths.extend(embedded_img_paths)
                    chunks.append(ocr_chunk)
                else:
                    # Fallback if rendering failed but some text was extracted
                    content = text if text else f"[Blank or unreadable page {page_num}]"
                    chunks.append(
                        EvidenceChunk(
                            id=f"chunk-{uuid.uuid4().hex[:8]}",
                            source_file=file_path.name,
                            source_type=SourceType.PDF,
                            location=f"Page {page_num}",
                            content=content,
                            image_paths=embedded_img_paths
                        )
                    )
            else:
                # Standard digital PDF page
                chunks.append(
                    EvidenceChunk(
                        id=f"chunk-{uuid.uuid4().hex[:8]}",
                        source_file=file_path.name,
                        source_type=SourceType.PDF,
                        location=f"Page {page_num}",
                        content=text,
                        image_paths=embedded_img_paths,
                        confidence=1.0,
                        is_ocr=False
                    )
                )

        if pdf_render_doc:
            try:
                pdf_render_doc.close()
            except Exception:
                pass

        return chunks
