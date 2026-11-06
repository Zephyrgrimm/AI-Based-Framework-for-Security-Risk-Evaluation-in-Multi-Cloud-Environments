"""Document layout, styling, and structural assembly engine."""
import re
from pathlib import Path
from typing import List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from udge.core.models import TemplateSpec, GeneratedSection, EvidenceCatalog

class DocumentStyler:
    """Builds styled intermediate documents (DOCX, Markdown, HTML) from generated sections."""

    def build_markdown(self, spec: TemplateSpec, sections: List[GeneratedSection]) -> str:
        """Assembles a clean Markdown document representation."""
        lines = [f"# {spec.title}", ""]

        if spec.include_toc:
            lines.append("## Table of Contents")
            for sec in sections:
                indent = "  " * (sec.level - 1)
                lines.append(f"{indent}- [{sec.title}](#{self._slug(sec.title)})")
            lines.append("")

        for sec in sections:
            prefix = "#" * min(sec.level + 1, 6)
            lines.append(f"{prefix} {sec.title}")
            lines.append("")
            lines.append(sec.content.strip())
            lines.append("")

        return "\n".join(lines)

    def build_docx(
        self,
        spec: TemplateSpec,
        sections: List[GeneratedSection],
        catalog: Optional[EvidenceCatalog],
        output_path: Path
    ) -> Path:
        """Assembles a professionally styled Word document (.docx)."""
        doc = docx.Document()

        # Set page margins to standard 1 inch
        sections_doc = doc.sections
        for s in sections_doc:
            s.top_margin = Inches(1.0)
            s.bottom_margin = Inches(1.0)
            s.left_margin = Inches(1.0)
            s.right_margin = Inches(1.0)

        # Style standard body text font
        style_normal = doc.styles["Normal"]
        font = style_normal.font
        font.name = "Calibri"
        font.size = Pt(11)
        font.color.rgb = RGBColor(0x22, 0x22, 0x22)

        # Document Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_title = p_title.add_run(spec.title)
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(24)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

        # Category subtitle
        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sub = p_sub.add_run(f"Type: {spec.document_category.value.replace('_', ' ').title()}")
        run_sub.font.italic = True
        run_sub.font.size = Pt(10)
        run_sub.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F)

        doc.add_paragraph()  # Spacing

        # Table of Contents outline if requested
        if spec.include_toc:
            h_toc = doc.add_heading(level=2)
            run_toc = h_toc.add_run("Table of Contents")
            run_toc.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

            for sec in sections:
                p_item = doc.add_paragraph(style="List Bullet")
                p_item.paragraph_format.left_indent = Inches(0.25 * (sec.level - 1))
                r = p_item.add_run(sec.title)
                r.font.size = Pt(10.5)

            doc.add_page_break()

        # Add Sections
        img_counter = 0
        extracted_images = catalog.extracted_images if catalog else []

        for sec in sections:
            h = doc.add_heading(level=min(sec.level, 3))
            h_run = h.add_run(sec.title)
            h_run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

            # Process content paragraphs
            paragraphs = sec.content.split("\n\n")
            for para_text in paragraphs:
                p_clean = para_text.strip()
                if not p_clean:
                    continue

                # Check if this paragraph contains a missing info alert
                if "[MISSING_INFORMATION:" in p_clean:
                    p_alert = doc.add_paragraph()
                    self._apply_shading(p_alert, "FFF3CD")  # Warning yellow box
                    r_alert = p_alert.add_run(f"⚠️ {p_clean}")
                    r_alert.font.bold = True
                    r_alert.font.size = Pt(10)
                    r_alert.font.color.rgb = RGBColor(0x85, 0x64, 0x04)
                    continue

                # Check if paragraph is markdown table
                if "|" in p_clean and "\n|" in p_clean:
                    self._add_markdown_table_to_docx(doc, p_clean)
                    continue

                # Regular paragraph with inline citation styling
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(6)

                # Parse citations for italicizing
                self._format_paragraph_with_citations(p, p_clean)

            # Insert an extracted figure if relevant
            if extracted_images and img_counter < len(extracted_images) and sec.level == 1:
                img_info = extracted_images[img_counter]
                img_p = Path(img_info["path"])
                if img_p.exists():
                    try:
                        p_fig = doc.add_paragraph()
                        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        doc.add_picture(str(img_p), width=Inches(4.5))
                        p_cap = doc.add_paragraph()
                        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        r_cap = p_cap.add_run(f"Figure {img_counter+1}: Extracted from {img_info['source_file']}")
                        r_cap.font.italic = True
                        r_cap.font.size = Pt(9)
                        img_counter += 1
                    except Exception:
                        pass

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        return output_path

    def _format_paragraph_with_citations(self, paragraph, text: str):
        # Match citations like [Source: filename, Page 2]
        tokens = re.split(r"(\[Source:[^\]]+\])", text)
        for tok in tokens:
            if tok.startswith("[Source:") and tok.endswith("]"):
                r = paragraph.add_run(f" {tok}")
                r.font.size = Pt(9.5)
                r.font.italic = True
                r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            else:
                paragraph.add_run(tok)

    def _add_markdown_table_to_docx(self, doc, table_text: str):
        lines = [l.strip() for l in table_text.splitlines() if l.strip().startswith("|")]
        if len(lines) < 2:
            return

        rows_data = []
        for line in lines:
            if re.match(r"^\|(\s*[-:]+\s*\|)+$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows_data.append(cells)

        if not rows_data:
            return

        num_cols = max(len(r) for r in rows_data)
        tbl = doc.add_table(rows=len(rows_data), cols=num_cols)
        tbl.style = "Table Grid"

        for r_idx, row in enumerate(rows_data):
            for c_idx, cell_val in enumerate(row):
                if c_idx < num_cols:
                    cell = tbl.cell(r_idx, c_idx)
                    cell.text = cell_val
                    if r_idx == 0:
                        # Header formatting
                        self._apply_shading(cell.paragraphs[0], "EAECEE")
                        for run in cell.paragraphs[0].runs:
                            run.font.bold = True

    def _apply_shading(self, paragraph_or_cell, color_hex: str):
        pPr = paragraph_or_cell._p.get_or_add_pPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
        pPr.append(shd)

    def _slug(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
