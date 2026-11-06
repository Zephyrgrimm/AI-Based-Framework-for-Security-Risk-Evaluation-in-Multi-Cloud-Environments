"""Tests for LibreOffice headless automation and isolated profiles."""
from pathlib import Path
from udge.libreoffice.runner import LibreOfficeRunner
from udge.libreoffice.styler import DocumentStyler
from udge.core.models import TemplateSpec, TemplateSection, GeneratedSection, OutputFormat
from udge.libreoffice.converter import DocumentConverter

def test_libreoffice_docx_to_pdf_conversion(tmp_path: Path):
    runner = LibreOfficeRunner()
    styler = DocumentStyler()

    # Build dummy DOCX
    spec = TemplateSpec(title="LibreOffice Automation Test")
    sections = [
        GeneratedSection(
            section_id="sec-1",
            title="Introduction",
            level=1,
            content="Testing LibreOffice headless conversion on Windows host environment."
        )
    ]

    docx_path = tmp_path / "test_doc.docx"
    styler.build_docx(spec, sections, catalog=None, output_path=docx_path)
    assert docx_path.exists()

    # Convert to PDF
    pdf_out = runner.convert(
        source_file=docx_path,
        target_format="pdf",
        output_dir=tmp_path / "out"
    )
    assert pdf_out.exists()
    assert pdf_out.suffix.lower() == ".pdf"
    assert pdf_out.stat().st_size > 0

def test_document_converter_multi_format(tmp_path: Path):
    converter = DocumentConverter()
    styler = DocumentStyler()

    spec = TemplateSpec(title="Multi-Format Test")
    sections = [
        GeneratedSection(
            section_id="sec-1",
            title="Overview",
            level=1,
            content="Testing multi-format output generation."
        )
    ]

    docx_path = tmp_path / "multi.docx"
    md_path = tmp_path / "multi.md"
    styler.build_docx(spec, sections, catalog=None, output_path=docx_path)
    md_path.write_text(styler.build_markdown(spec, sections), encoding="utf-8")

    out_dir = tmp_path / "multi_exports"
    exports = converter.convert_all(
        intermediate_docx=docx_path,
        intermediate_md=md_path,
        target_formats=[OutputFormat.PDF, OutputFormat.DOCX, OutputFormat.ODT],
        output_dir=out_dir
    )

    assert "pdf" in exports and exports["pdf"].exists()
    assert "docx" in exports and exports["docx"].exists()
    assert "odt" in exports and exports["odt"].exists()
