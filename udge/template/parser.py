"""Markdown template parser that produces a structured TemplateSpec AST."""
import re
from pathlib import Path
from typing import List, Optional
import uuid
from udge.core.exceptions import TemplateError
from udge.core.models import TemplateSpec, TemplateSection, DocumentCategory
from udge.template.spec import validate_template_spec

# Regex patterns for placeholder tokens
PLACEHOLDER_REGEX = re.compile(r"(\{\{[A-Za-z0-9_\s\-]+\}\}|\[INSERT\s+[^\]]+\]|\[TODO:?[^\]]*\]|<[A-Z0-9_]{3,}>)")
WORD_COUNT_REGEX = re.compile(r"\[~?(\d+)\s*words?\]", re.IGNORECASE)

class TemplateParser:
    """Parses document templates (Markdown, TXT, Word DOCX, and PDF) into structured TemplateSpecs."""

    def parse_file(self, template_path: Path) -> TemplateSpec:
        """Loads and parses a template file (supports .md, .txt, .docx, .pdf)."""
        if not template_path.exists():
            raise TemplateError(f"Template file does not exist: {template_path}")

        suffix = template_path.suffix.lower()
        if suffix == ".docx":
            content = self._docx_to_markdown(template_path)
            return self.parse_text(content, filename=template_path.name)
        elif suffix == ".pdf":
            content = self._pdf_to_markdown(template_path)
            return self.parse_text(content, filename=template_path.name)
        else:
            try:
                content = template_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = template_path.read_text(encoding="latin-1", errors="replace")
            return self.parse_text(content, filename=template_path.name)

    def _docx_to_markdown(self, docx_path: Path) -> str:
        """Extracts structured text from a Word DOCX template preserving heading hierarchy."""
        import docx
        doc = docx.Document(docx_path)
        md_lines = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower()
            if "title" in style_name:
                md_lines.append(f"# {text}")
            elif "heading 1" in style_name:
                md_lines.append(f"# {text}")
            elif "heading 2" in style_name:
                md_lines.append(f"## {text}")
            elif "heading 3" in style_name:
                md_lines.append(f"### {text}")
            elif style_name.startswith("heading"):
                md_lines.append(f"## {text}")
            else:
                md_lines.append(text)

        # Also extract table layouts as template guides if present
        for t_idx, table in enumerate(doc.tables, 1):
            t_rows = []
            for r in table.rows:
                t_rows.append([cell.text.strip() for cell in r.cells])
            if t_rows:
                header = t_rows[0]
                md_lines.append(f"\n| " + " | ".join(header) + " |")
                md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for r in t_rows[1:]:
                    padded = r + [""] * (len(header) - len(r))
                    md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")
                md_lines.append("\n")

        return "\n\n".join(md_lines)

    def _pdf_to_markdown(self, pdf_path: Path) -> str:
        """Extracts structured text from a PDF template."""
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        lines = []
        is_first = True
        for p in reader.pages:
            t = p.extract_text() or ""
            for raw_line in t.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if is_first:
                    lines.append(f"# {line}")
                    is_first = False
                    continue
                # Detect common academic/document heading patterns
                if (
                    re.match(r"^(\d+(\.\d+)*)\s+[A-Z]", line)
                    or (line.isupper() and len(line) < 60)
                    or (len(line) < 60 and not line.endswith((".", ";", ":")) and any(w in line.lower() for w in ["report", "overview", "evaluation", "assessment", "summary", "specifications", "benchmarks", "results", "analysis", "work", "conclusion", "references", "metrics"]))
                ):
                    lines.append(f"## {line}")
                else:
                    lines.append(line)
        return "\n\n".join(lines)

    def parse_text(self, markdown_text: str, filename: str = "template.md") -> TemplateSpec:
        """Parses markdown text into TemplateSpec."""
        lines = markdown_text.splitlines()
        spec = TemplateSpec()

        # Check for frontmatter block delineated by ---
        body_lines = []
        in_fm = False
        fm_lines = []
        fm_found = False

        for line in lines:
            stripped = line.strip()
            if stripped == "---" and not fm_found:
                if not in_fm:
                    in_fm = True
                    continue
                else:
                    in_fm = False
                    fm_found = True
                    continue
            if in_fm:
                fm_lines.append(line)
            else:
                body_lines.append(line)

        if fm_lines:
            self._apply_frontmatter(spec, fm_lines)

        current_section: Optional[TemplateSection] = None
        current_content_lines: List[str] = []
        section_order = 0

        for line in body_lines:
            stripped = line.strip()

            # Check for markdown heading (#) or standard section titles (from DOCX/PDF)
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            level = None
            heading_title = ""

            if heading_match:
                level = len(heading_match.group(1))
                heading_title = heading_match.group(2).strip()
            elif re.match(r"^(\d+\.\d+)\s+([A-Za-z0-9\s\-_&]+)$", stripped):
                level = 2
                heading_title = stripped
            elif re.match(r"^(\d+(\.0)?)\s+([A-Za-z0-9\s\-_&]+)$", stripped) and len(stripped) < 80:
                level = 1
                heading_title = stripped
            elif stripped.lower() in {
                "abstract", "introduction", "executive summary", "literature survey",
                "problem statement", "objectives", "methodology", "system architecture",
                "software requirement specification", "implementation plan",
                "results and discussion", "conclusion", "references", "appendices"
            }:
                level = 1
                heading_title = stripped

            if level is not None and heading_title:
                # If this is the top level title and spec doesn't have a title yet, set as document title
                if level == 1 and (spec.title == "Untitled Document" or not spec.title):
                    spec.title = heading_title
                    # Still create a section if it has content, or continue
                    current_section = TemplateSection(
                        id=f"sec-{section_order}-{self._slugify(heading_title)}",
                        title=heading_title,
                        level=level,
                        order=section_order,
                        required=True
                    )
                    section_order += 1
                    current_content_lines = []
                    continue

                # Finish previous section
                if current_section:
                    self._finalize_section(current_section, current_content_lines)
                    if current_section.raw_markdown.strip() or current_section.title != spec.title:
                        spec.sections.append(current_section)
                    current_content_lines = []

                # Start new section
                current_section = TemplateSection(
                    id=f"sec-{section_order}-{self._slugify(heading_title)}",
                    title=heading_title,
                    level=level,
                    order=section_order,
                    required=True
                )
                section_order += 1
            else:
                if current_section is not None:
                    current_content_lines.append(line)
                elif stripped:
                    # Content before any heading: if document title is default, use first non-empty line
                    if spec.title == "Untitled Document":
                        spec.title = stripped

        if current_section:
            self._finalize_section(current_section, current_content_lines)
            if current_section.raw_markdown.strip() or current_section.title != spec.title:
                spec.sections.append(current_section)

        # Fallback if no sections were created but text exists
        if not spec.sections and body_lines:
            non_empty = [l.strip() for l in body_lines if l.strip()]
            if non_empty:
                spec.sections.append(
                    TemplateSection(
                        id="sec-0-content",
                        title=spec.title if spec.title != "Untitled Document" else "Document Content",
                        level=1,
                        order=0,
                        raw_markdown="\n".join(body_lines),
                        required=True
                    )
                )

        # Infer category only if still general
        if spec.document_category == DocumentCategory.GENERAL:
            spec.document_category = self._infer_category(spec.title, spec.sections)

        validate_template_spec(spec)
        return spec

    def _finalize_section(self, section: TemplateSection, lines: List[str]):
        raw_text = "\n".join(lines).strip()
        section.raw_markdown = raw_text

        # Extract placeholders
        matches = PLACEHOLDER_REGEX.findall(raw_text)
        section.placeholder_tokens = list(set(matches))

        # Check for word count hints
        wc_match = WORD_COUNT_REGEX.search(raw_text)
        if wc_match:
            section.expected_word_count = int(wc_match.group(1))

        # Separate instructions from boilerplate
        instruction_lines = []
        for line in lines:
            s = line.strip()
            if s.startswith(">") or s.startswith("<!--") or (s.startswith("*[") and s.endswith("]*")):
                clean = re.sub(r"^(>|<!--|\*\[|\]\*|-->)\s*", "", s).strip()
                if clean:
                    instruction_lines.append(clean)
        section.instructions = "\n".join(instruction_lines) if instruction_lines else raw_text

    def _apply_frontmatter(self, spec: TemplateSpec, fm_lines: List[str]):
        for line in fm_lines:
            if ":" in line:
                k, v = line.split(":", 1)
                key = k.strip().lower()
                val = v.strip().strip("\"'")
                if key == "title":
                    spec.title = val
                elif key in {"category", "type"}:
                    try:
                        spec.document_category = DocumentCategory(val.lower())
                    except ValueError:
                        pass
                elif key in {"require_citations", "citations"}:
                    spec.require_citations = val.lower() in {"true", "yes", "1"}
                elif key in {"include_toc", "toc"}:
                    spec.include_toc = val.lower() in {"true", "yes", "1"}

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
        return s[:30] if s else uuid.uuid4().hex[:6]

    def _infer_category(self, title: str, sections: List[TemplateSection]) -> DocumentCategory:
        text = (title + " " + " ".join(s.title for s in sections)).lower()
        if any(w in text for w in ["academic", "thesis", "dissertation", "literature review", "methodology"]):
            return DocumentCategory.ACADEMIC_REPORT
        if any(w in text for w in ["proposal", "business plan", "executive summary", "roi", "budget"]):
            return DocumentCategory.BUSINESS_PROPOSAL
        if any(w in text for w in ["architecture", "api", "specification", "technical", "system design"]):
            return DocumentCategory.TECHNICAL_DOC
        if any(w in text for w in ["manual", "user guide", "handbook", "troubleshooting"]):
            return DocumentCategory.MANUAL
        if any(w in text for w in ["research summary", "findings", "experiment", "results"]):
            return DocumentCategory.RESEARCH_SUMMARY
        if any(w in text for w in ["project report", "sprint", "milestone", "status report"]):
            return DocumentCategory.PROJECT_REPORT
        return DocumentCategory.GENERAL
