"""Unit tests for Ingestion and OCR Pipeline."""
from pathlib import Path
from udge.ingestion.pipeline import IngestionPipeline
from udge.ingestion.text_extractor import TextExtractor
from udge.ingestion.office_extractor import OfficeExtractor
from udge.ingestion.pdf_extractor import PDFExtractor
from udge.ingestion.ocr_extractor import OCRExtractor
from udge.core.models import SourceType

def test_text_extractor(fixtures_dir: Path, tmp_path: Path):
    extractor = TextExtractor()
    csv_file = fixtures_dir / "trials_data.csv"
    assert extractor.can_handle(csv_file)

    chunks = extractor.extract(csv_file, tmp_path)
    assert len(chunks) >= 1
    assert chunks[0].source_type == SourceType.CSV
    assert "T-101" in chunks[0].content

def test_office_extractor(fixtures_dir: Path, tmp_path: Path):
    extractor = OfficeExtractor()
    docx_file = fixtures_dir / "robotics_sensors.docx"
    assert extractor.can_handle(docx_file)

    chunks = extractor.extract(docx_file, tmp_path)
    assert len(chunks) >= 1
    content_all = " ".join(c.content for c in chunks)
    assert "Solid-State Lidar" in content_all
    assert "Autonomous Navigation Sensors" in content_all

def test_ocr_extractor(fixtures_dir: Path, tmp_path: Path):
    extractor = OCRExtractor()
    img_file = fixtures_dir / "lidar_diagram.png"
    assert extractor.can_handle(img_file)

    chunks = extractor.extract(img_file, tmp_path)
    assert len(chunks) == 1
    assert chunks[0].source_type == SourceType.IMAGE
    assert chunks[0].is_ocr is True

def test_pdf_extractor_digital_and_scanned(fixtures_dir: Path, tmp_path: Path):
    pdf_extractor = PDFExtractor()

    # 1. Digital PDF
    dig_pdf = fixtures_dir / "benchmarks.pdf"
    assert pdf_extractor.can_handle(dig_pdf)
    dig_chunks = pdf_extractor.extract(dig_pdf, tmp_path / "digital_out")
    assert len(dig_chunks) >= 1
    assert "Robotics Benchmark" in dig_chunks[0].content

    # 2. Scanned / Raster PDF
    scanned_pdf = fixtures_dir / "scanned_notes.pdf"
    scanned_chunks = pdf_extractor.extract(scanned_pdf, tmp_path / "scanned_out")
    assert len(scanned_chunks) >= 1
    assert scanned_chunks[0].source_type == SourceType.SCANNED_PDF
    assert scanned_chunks[0].is_ocr is True

def test_unified_pipeline(fixtures_dir: Path, tmp_path: Path):
    pipeline = IngestionPipeline()
    sources = [
        fixtures_dir / "robotics_sensors.docx",
        fixtures_dir / "benchmarks.pdf",
        fixtures_dir / "scanned_notes.pdf",
        fixtures_dir / "trials_data.csv",
        fixtures_dir / "lidar_diagram.png"
    ]
    catalog = pipeline.ingest_files(sources, tmp_path / "unified_catalog")
    assert len(catalog.source_files) == 5
    assert len(catalog.chunks) >= 5
    assert len(catalog.extracted_images) >= 1
