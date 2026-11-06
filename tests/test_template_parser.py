"""Unit tests for Template Parser and Specification."""
from pathlib import Path
from udge.template.parser import TemplateParser
from udge.core.models import DocumentCategory

def test_template_parser_hierarchical_sections(fixtures_dir: Path):
    parser = TemplateParser()
    spec = parser.parse_file(fixtures_dir / "template.md")

    assert spec.title == "Autonomous Robotics Research Report"
    assert spec.document_category == DocumentCategory.TECHNICAL_DOC
    assert spec.require_citations is True
    assert spec.include_toc is True

    assert len(spec.sections) == 4
    section_titles = [s.title for s in spec.sections]
    assert "Executive Summary" in section_titles
    assert "Sensor Subsystems and Performance" in section_titles
    assert "Experimental Benchmarks" in section_titles
    assert "Limitations and Future Work" in section_titles

    # Placeholders check
    sec_summary = next(s for s in spec.sections if s.title == "Executive Summary")
    assert any("[INSERT EXECUTIVE SUMMARY]" in p for p in sec_summary.placeholder_tokens)
    assert sec_summary.expected_word_count == 150

    sec_sensor = next(s for s in spec.sections if s.title == "Sensor Subsystems and Performance")
    assert any("{{SENSOR_ANALYSIS}}" in p for p in sec_sensor.placeholder_tokens)

def test_docx_template_parsing(tmp_path: Path):
    import docx
    docx_file = tmp_path / "template.docx"
    doc = docx.Document()
    doc.add_heading("Cloud Security Audit Template", level=1)
    doc.add_heading("Executive Summary", level=2)
    doc.add_paragraph("Provide brief summary [INSERT SUMMARY]")
    doc.add_heading("Vulnerability Assessment", level=2)
    doc.add_paragraph("Details on findings {{FINDINGS}}")
    doc.save(str(docx_file))

    parser = TemplateParser()
    spec = parser.parse_file(docx_file)

    assert "Cloud Security Audit Template" in spec.title
    assert len(spec.sections) >= 2
    titles = [s.title for s in spec.sections]
    assert any("Executive Summary" in t for t in titles)
    assert any("Vulnerability Assessment" in t for t in titles)

def test_pdf_template_parsing(fixtures_dir: Path):
    parser = TemplateParser()
    pdf_template = fixtures_dir / "benchmarks.pdf"
    spec = parser.parse_file(pdf_template)

    assert len(spec.sections) >= 1
    assert spec.title != "Untitled Document"
