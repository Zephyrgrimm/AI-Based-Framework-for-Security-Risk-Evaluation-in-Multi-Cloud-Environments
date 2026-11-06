"""OCR and Vision Extractor for standalone images and scanned PDF pages."""
from pathlib import Path
from typing import List, Optional
import uuid
from PIL import Image, ImageEnhance
from udge.core.models import EvidenceChunk, SourceType
from udge.ingestion.extractor_base import BaseExtractor

class OCRExtractor(BaseExtractor):
    """Extracts text and visual descriptions from images and scanned document pages."""

    SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}

    def __init__(self, vision_llm_callable=None):
        self.vision_llm = vision_llm_callable
        self._tesseract_available = self._check_tesseract()
        self._rapidocr_available = self._check_rapidocr()

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract
            # Test if tesseract binary is runnable
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def _check_rapidocr(self) -> bool:
        try:
            import rapidocr_onnxruntime
            return True
        except Exception:
            return False

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTS

    def extract(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        """Extracts text from a standalone image file."""
        return [self.extract_from_image(file_path, location=f"Image {file_path.name}")]

    def extract_from_image(
        self,
        image_path: Path,
        location: str = "Image",
        is_pdf_page: bool = False
    ) -> EvidenceChunk:
        """Processes an image file or rendered page and returns an EvidenceChunk."""
        extracted_text = ""
        method_used = "metadata"

        # 1. Image preprocessing
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                img_format = img.format or "IMAGE"
                # Preprocess copy for OCR
                gray = img.convert("L")
                enhancer = ImageEnhance.Contrast(gray)
                enhanced_img = enhancer.enhance(1.8)
        except Exception as e:
            return EvidenceChunk(
                id=f"chunk-{uuid.uuid4().hex[:8]}",
                source_file=image_path.name,
                source_type=SourceType.IMAGE,
                location=location,
                content=f"[Error reading image file: {e}]",
                confidence=0.0
            )

        # 2. Try Local OCR (Tesseract / RapidOCR)
        if self._tesseract_available:
            try:
                import pytesseract
                text = pytesseract.image_to_string(enhanced_img).strip()
                if text:
                    extracted_text = text
                    method_used = "tesseract_ocr"
            except Exception:
                pass

        if not extracted_text and self._rapidocr_available:
            try:
                from rapidocr_onnxruntime import RapidOCR
                engine = RapidOCR()
                result, _ = engine(str(image_path))
                if result:
                    extracted_text = "\n".join([line[1] for line in result]).strip()
                    method_used = "rapid_ocr"
            except Exception:
                pass

        # 3. Vision LLM fallback if provided
        if not extracted_text and self.vision_llm:
            try:
                vision_text = self.vision_llm(image_path)
                if vision_text:
                    extracted_text = vision_text.strip()
                    method_used = "vision_llm"
            except Exception:
                pass

        # 4. Fallback text representation if OCR engine is not locally installed
        if not extracted_text:
            extracted_text = (
                f"[Image/Figure: {image_path.name} | Resolution: {width}x{height} | Format: {img_format}]\n"
                f"(Visual element extracted and cataloged for document layout and figure references)"
            )

        chunk_type = SourceType.SCANNED_PDF if is_pdf_page else SourceType.IMAGE

        return EvidenceChunk(
            id=f"chunk-{uuid.uuid4().hex[:8]}",
            source_file=image_path.name,
            source_type=chunk_type,
            location=location,
            content=extracted_text,
            image_paths=[str(image_path)],
            confidence=0.9 if method_used != "metadata" else 0.7,
            is_ocr=True,
            metadata={
                "method": method_used,
                "width": width,
                "height": height
            }
        )
