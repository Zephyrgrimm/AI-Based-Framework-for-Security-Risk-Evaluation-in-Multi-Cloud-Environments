"""End-to-End integration test for Universal Document Generation Engine."""
from pathlib import Path
from udge.core.models import OutputFormat, JobStatus
from udge.agents.intake import IntakeAgent
from udge.agents.orchestrator import MasterOrchestrator

def test_full_pipeline_end_to_end(fixtures_dir: Path, tmp_path: Path):
    intake = IntakeAgent()

    template_file = fixtures_dir / "template.md"
    source_files = [
        fixtures_dir / "robotics_sensors.docx",
        fixtures_dir / "benchmarks.pdf",
        fixtures_dir / "scanned_notes.pdf",
        fixtures_dir / "trials_data.csv",
        fixtures_dir / "lidar_diagram.png"
    ]

    job = intake.initialize_job(
        template_path=template_file,
        source_paths=source_files,
        output_formats=[OutputFormat.PDF, OutputFormat.DOCX, OutputFormat.ODT],
        job_id="test-e2e-run"
    )

    orchestrator = MasterOrchestrator(llm_provider_name="mock")
    completed_job = orchestrator.run(job)

    # 1. Job completion status
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.finished_at is not None

    # 2. Output files verification
    assert "pdf" in completed_job.output_files
    assert "docx" in completed_job.output_files
    assert "odt" in completed_job.output_files

    pdf_path = Path(completed_job.output_files["pdf"])
    docx_path = Path(completed_job.output_files["docx"])
    odt_path = Path(completed_job.output_files["odt"])

    assert pdf_path.exists() and pdf_path.stat().st_size > 0
    assert docx_path.exists() and docx_path.stat().st_size > 0
    assert odt_path.exists() and odt_path.stat().st_size > 0

    # 3. QA Validation report verification
    val_report = completed_job.validation_report
    assert val_report is not None
    assert val_report.passed is True  # No fatal errors
    assert val_report.total_checks > 0

    # Verify report files on disk
    workspace = Path(completed_job.workspace_dir)
    assert (workspace / "validation_report.json").exists()
    assert (workspace / "validation_report.md").exists()
    assert (workspace / "assembled.md").exists()
    assert (workspace / "content_mapping_plan.json").exists()

    # Verify that missing information was cleanly flagged rather than hallucinated
    info_codes = [i.code for i in val_report.info]
    assert "DATA_MISSING_INFORMATION" in info_codes
