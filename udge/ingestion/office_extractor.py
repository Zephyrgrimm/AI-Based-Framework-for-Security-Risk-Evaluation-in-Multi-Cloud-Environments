"""Extractor for Microsoft Office and OpenDocument files (DOCX, PPTX, XLSX)."""
from pathlib import Path
from typing import List, Dict, Any
import uuid
from udge.core.models import EvidenceChunk, SourceType
from udge.ingestion.extractor_base import BaseExtractor

class OfficeExtractor(BaseExtractor):
    """Extracts text, tables, and images from DOCX, PPTX, and XLSX files."""

    SUPPORTED_EXTS = {".docx", ".pptx", ".xlsx"}

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTS

    def extract(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            return self._extract_docx(file_path, output_dir)
        elif suffix == ".pptx":
            return self._extract_pptx(file_path, output_dir)
        elif suffix == ".xlsx":
            return self._extract_xlsx(file_path)
        return []

    def _extract_docx(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        import docx
        doc = docx.Document(file_path)
        chunks: List[EvidenceChunk] = []

        # Directory for extracted images
        img_dir = output_dir / "extracted_images"
        img_dir.mkdir(parents=True, exist_ok=True)

        extracted_img_paths: List[str] = []
        # Extract images from docx relationships
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_data = rel.target_part.blob
                    img_ext = Path(rel.target_ref).suffix or ".png"
                    img_name = f"{file_path.stem}_{uuid.uuid4().hex[:6]}{img_ext}"
                    dest_img = img_dir / img_name
                    dest_img.write_bytes(img_data)
                    extracted_img_paths.append(str(dest_img))
                except Exception:
                    pass

        # Extract paragraphs & headings
        current_heading = "Document Content"
        buffer: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            if p.style.name.startswith("Heading"):
                if buffer:
                    chunk_text = "\n".join(buffer).strip()
                    if chunk_text:
                        chunks.append(
                            EvidenceChunk(
                                id=f"chunk-{uuid.uuid4().hex[:8]}",
                                source_file=file_path.name,
                                source_type=SourceType.DOCX,
                                location=f"Section: {current_heading}",
                                content=chunk_text,
                                image_paths=extracted_img_paths if not chunks else []
                            )
                        )
                    buffer = []
                current_heading = text

            buffer.append(text)

        if buffer:
            chunk_text = "\n".join(buffer).strip()
            if chunk_text:
                chunks.append(
                    EvidenceChunk(
                        id=f"chunk-{uuid.uuid4().hex[:8]}",
                        source_file=file_path.name,
                        source_type=SourceType.DOCX,
                        location=f"Section: {current_heading}",
                        content=chunk_text,
                        image_paths=extracted_img_paths if not chunks else []
                    )
                )

        # Extract tables
        for t_idx, table in enumerate(doc.tables, 1):
            table_rows: List[List[str]] = []
            for row in table.rows:
                table_rows.append([cell.text.strip() for cell in row.cells])

            if table_rows:
                header = table_rows[0]
                md_table = [
                    f"Table {t_idx} from {file_path.name}:",
                    "| " + " | ".join(header) + " |",
                    "| " + " | ".join(["---"] * len(header)) + " |"
                ]
                for r in table_rows[1:]:
                    padded = r + [""] * (len(header) - len(r))
                    md_table.append("| " + " | ".join(padded[:len(header)]) + " |")

                chunks.append(
                    EvidenceChunk(
                        id=f"chunk-{uuid.uuid4().hex[:8]}",
                        source_file=file_path.name,
                        source_type=SourceType.DOCX,
                        location=f"Table {t_idx}",
                        content="\n".join(md_table),
                        tables=[table_rows]
                    )
                )

        return chunks

    def _extract_pptx(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        from pptx import Presentation
        prs = Presentation(file_path)
        chunks: List[EvidenceChunk] = []

        img_dir = output_dir / "extracted_images"
        img_dir.mkdir(parents=True, exist_ok=True)

        for s_idx, slide in enumerate(prs.slides, 1):
            slide_texts: List[str] = []
            slide_tables: List[List[List[str]]] = []
            slide_imgs: List[str] = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)
                elif shape.has_table:
                    tbl: List[List[str]] = []
                    for row in shape.table.rows:
                        tbl.append([c.text.strip() for c in row.cells])
                    if tbl:
                        slide_tables.append(tbl)
                elif shape.shape_type == 13:  # Picture
                    try:
                        image = shape.image
                        img_ext = f".{image.ext}" if image.ext else ".png"
                        img_name = f"{file_path.stem}_slide{s_idx}_{uuid.uuid4().hex[:6]}{img_ext}"
                        dest = img_dir / img_name
                        dest.write_bytes(image.blob)
                        slide_imgs.append(str(dest))
                    except Exception:
                        pass

            content_parts = [f"Slide {s_idx}:"]
            if slide_texts:
                content_parts.extend(slide_texts)

            if slide_tables:
                for t in slide_tables:
                    header = t[0]
                    content_parts.append("| " + " | ".join(header) + " |")
                    content_parts.append("| " + " | ".join(["---"] * len(header)) + " |")
                    for r in t[1:]:
                        padded = r + [""] * (len(header) - len(r))
                        content_parts.append("| " + " | ".join(padded[:len(header)]) + " |")

            if len(content_parts) > 1:
                chunks.append(
                    EvidenceChunk(
                        id=f"chunk-{uuid.uuid4().hex[:8]}",
                        source_file=file_path.name,
                        source_type=SourceType.PPTX,
                        location=f"Slide {s_idx}",
                        content="\n".join(content_parts),
                        tables=slide_tables,
                        image_paths=slide_imgs
                    )
                )

        return chunks

    def _extract_xlsx(self, file_path: Path) -> List[EvidenceChunk]:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        chunks: List[EvidenceChunk] = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows: List[List[str]] = []
            for row in ws.iter_rows(values_only=True):
                str_row = [str(val).strip() if val is not None else "" for val in row]
                if any(str_row):
                    rows.append(str_row)

            if not rows:
                continue

            header = rows[0]
            md_lines = [
                f"Spreadsheet: {file_path.name} | Sheet: {sheet_name}",
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(["---"] * len(header)) + " |"
            ]
            for r in rows[1:100]:
                padded = r + [""] * (len(header) - len(r))
                md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

            chunks.append(
                EvidenceChunk(
                    id=f"chunk-{uuid.uuid4().hex[:8]}",
                    source_file=file_path.name,
                    source_type=SourceType.XLSX,
                    location=f"Sheet '{sheet_name}'",
                    content="\n".join(md_lines),
                    tables=[rows]
                )
            )

        return chunks
