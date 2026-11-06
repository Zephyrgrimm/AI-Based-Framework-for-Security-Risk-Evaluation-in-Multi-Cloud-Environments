"""Pytest fixtures and test document generator."""
import pytest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import docx
import openpyxl
import pypdf

@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("udge_fixtures")

    # 1. Sample Markdown Template
    template_content = """# Autonomous Robotics Research Report
---
category: technical_doc
require_citations: true
include_toc: true
---

## Executive Summary
> Instruction: Provide an executive synthesis of navigation autonomy and sensor integration.
[INSERT EXECUTIVE SUMMARY]
[~150 words]

## Sensor Subsystems and Performance
> Instruction: Detail lidar, vision sensors, and frame rates.
{{SENSOR_ANALYSIS}}

## Experimental Benchmarks
> Instruction: Present navigation accuracy, obstacle avoidance metrics, and test results.

## Limitations and Future Work
> Instruction: Identify known constraints and subsequent research phases.
"""
    template_path = base / "template.md"
    template_path.write_text(template_content, encoding="utf-8")

    # 2. Sample Image (Diagram / Chart)
    img_path = base / "lidar_diagram.png"
    img = Image.new("RGB", (400, 200), color=(240, 244, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 380, 180], outline=(31, 73, 125), width=3)
    draw.text((40, 50), "Lidar Sensor Subsystem v2.1", fill=(15, 23, 42))
    draw.text((40, 90), "Resolution: 128 beams | Range: 100m", fill=(51, 65, 85))
    draw.text((40, 130), "Latency: 8.5ms | Frequency: 20Hz", fill=(51, 65, 85))
    img.save(img_path)

    # 3. Sample DOCX Document
    docx_path = base / "robotics_sensors.docx"
    doc = docx.Document()
    doc.add_heading("Autonomous Navigation Sensors", level=1)
    doc.add_paragraph("The robotic system utilizes a high-resolution 128-beam lidar paired with stereoscopic vision sensors.")
    doc.add_paragraph("Real-time sensor fusion operates at 20Hz with deterministic latency of 8.5 milliseconds.")

    table = doc.add_table(rows=3, cols=3)
    data = [
        ["Sensor Type", "Sampling Rate", "Range"],
        ["Solid-State Lidar", "20 Hz", "100 meters"],
        ["Stereo Camera", "60 fps", "40 meters"]
    ]
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val

    # Embed image
    doc.add_picture(str(img_path), width=docx.shared.Inches(3))
    doc.save(str(docx_path))

    # 4. Sample Digital PDF Document
    pdf_path = base / "benchmarks.pdf"
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # We create a simple valid PDF with text streams
    writer.write(str(pdf_path))
    writer.close()
    # Write text using reportlab or create plain valid text PDF
    _create_text_pdf(pdf_path, [
        "Robotics Benchmark Evaluation Report",
        "Navigation accuracy achieved 99.4% in structured warehouse environments.",
        "Obstacle avoidance demonstrated zero collision events across 500 trial runs.",
        "Battery consumption averaged 42 Watts during active autonomous traversal."
    ])

    # 5. Sample Scanned / Image-Only PDF
    scanned_pdf_path = base / "scanned_notes.pdf"
    _create_image_pdf(scanned_pdf_path, img_path)

    # 6. Sample CSV spreadsheet
    csv_path = base / "trials_data.csv"
    csv_path.write_text(
        "Trial_ID,Status,Obstacle_Dist_cm,Velocity_mps\n"
        "T-101,Success,45.2,1.5\n"
        "T-102,Success,38.1,1.8\n"
        "T-103,Success,52.6,1.4\n",
        encoding="utf-8"
    )

    return base

def _create_text_pdf(dest_path: Path, lines: list):
    """Creates a clean digital text PDF using pypdf content stream."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject, ArrayObject, NumberObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    # Text stream in PDF format
    stream_content = "BT /F1 12 Tf 50 720 Td 18 TL "
    for line in lines:
        escaped = line.replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({escaped}) ' "
    stream_content += "ET"

    stream = DecodedStreamObject()
    stream.set_data(stream_content.encode("latin-1"))

    # Add standard font resource
    f1 = DictionaryObject()
    f1[NameObject("/Type")] = NameObject("/Font")
    f1[NameObject("/Subtype")] = NameObject("/Type1")
    f1[NameObject("/BaseFont")] = NameObject("/Helvetica")

    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = f1

    res = DictionaryObject()
    res[NameObject("/Font")] = fonts

    page[NameObject("/Resources")] = res
    page[NameObject("/Contents")] = stream

    with open(dest_path, "wb") as f:
        writer.write(f)
    writer.close()

def _create_image_pdf(dest_path: Path, img_path: Path):
    """Creates a PDF page containing only a raster image to simulate scanned PDF."""
    from PIL import Image
    im = Image.open(img_path)
    im.save(dest_path, "PDF", resolution=100.0)
