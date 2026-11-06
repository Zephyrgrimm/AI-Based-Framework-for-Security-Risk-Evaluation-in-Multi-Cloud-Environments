"""Multi-format conversion orchestrator leveraging LibreOffice."""
from pathlib import Path
from typing import Dict, List, Optional
from udge.core.models import OutputFormat
from udge.libreoffice.runner import LibreOfficeRunner

class DocumentConverter:
    """Manages multi-format conversions using headless LibreOffice."""

    def __init__(self, runner: Optional[LibreOfficeRunner] = None):
        self.runner = runner or LibreOfficeRunner()

    def convert_all(
        self,
        intermediate_docx: Path,
        intermediate_md: Path,
        target_formats: List[OutputFormat],
        output_dir: Path
    ) -> Dict[str, Path]:
        """Converts intermediate document into all requested target formats."""
        output_files: Dict[str, Path] = {}
        output_dir.mkdir(parents=True, exist_ok=True)

        for fmt in target_formats:
            if fmt == OutputFormat.DOCX:
                # Copy or preserve intermediate DOCX
                dest = output_dir / intermediate_docx.name
                if intermediate_docx != dest:
                    import shutil
                    shutil.copy2(intermediate_docx, dest)
                output_files["docx"] = dest

            elif fmt == OutputFormat.MARKDOWN:
                dest = output_dir / intermediate_md.name
                if intermediate_md != dest:
                    import shutil
                    shutil.copy2(intermediate_md, dest)
                output_files["md"] = dest

            elif fmt == OutputFormat.PDF:
                # Convert DOCX to PDF via LibreOffice headless
                pdf_path = self.runner.convert(
                    source_file=intermediate_docx,
                    target_format="pdf",
                    output_dir=output_dir
                )
                output_files["pdf"] = pdf_path

            elif fmt == OutputFormat.ODT:
                # Convert DOCX to ODT via LibreOffice headless
                odt_path = self.runner.convert(
                    source_file=intermediate_docx,
                    target_format="odt",
                    output_dir=output_dir
                )
                output_files["odt"] = odt_path

            elif fmt == OutputFormat.HTML:
                # Convert DOCX to HTML via LibreOffice headless
                html_path = self.runner.convert(
                    source_file=intermediate_docx,
                    target_format="html",
                    output_dir=output_dir
                )
                output_files["html"] = html_path

        return output_files
