"""FastAPI Web Application and REST API for UDGE Dashboard."""
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from udge.core.config import config
from udge.core.models import OutputFormat, GenerationJob, JobStatus
from udge.agents.intake import IntakeAgent
from udge.agents.orchestrator import MasterOrchestrator
from udge.template.parser import TemplateParser

app = FastAPI(title="UDGE Web Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job registry for active session
active_jobs: dict[str, GenerationJob] = {}

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI template not found")
    return index_file.read_text(encoding="utf-8")

@app.post("/api/inspect/template")
async def inspect_template_api(template: UploadFile = File(...)):
    """Uploads and returns parsed template specification."""
    temp_dir = config.temp_dir / f"inspect_{uuid.uuid4().hex[:6]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / template.filename
    try:
        content = await template.read()
        temp_file.write_bytes(content)
        parser = TemplateParser()
        spec = parser.parse_file(temp_file)
        return spec.model_dump(mode="json")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def _execute_pipeline_task(job: GenerationJob, llm_provider: str):
    orchestrator = MasterOrchestrator(llm_provider_name=llm_provider)
    try:
        orchestrator.run(job)
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)

@app.post("/api/jobs")
async def create_job_api(
    background_tasks: BackgroundTasks,
    template: UploadFile = File(...),
    sources: List[UploadFile] = File(...),
    formats: str = Form("pdf,docx"),
    llm: str = Form("mock")
):
    """Initializes and launches an asynchronous document generation job."""
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    upload_dir = config.workspace_root / job_id / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save template
    template_path = upload_dir / template.filename
    template_path.write_bytes(await template.read())

    # Save sources
    source_paths = []
    for src in sources:
        src_path = upload_dir / src.filename
        src_path.write_bytes(await src.read())
        source_paths.append(src_path)

    # Parse formats
    fmt_list = []
    for f in formats.split(","):
        cleaned = f.strip().lower()
        if cleaned:
            try:
                fmt_list.append(OutputFormat(cleaned))
            except ValueError:
                pass
    if not fmt_list:
        fmt_list = [OutputFormat.PDF, OutputFormat.DOCX]

    intake = IntakeAgent()
    job = intake.initialize_job(
        template_path=template_path,
        source_paths=source_paths,
        output_formats=fmt_list,
        job_id=job_id
    )

    active_jobs[job_id] = job
    background_tasks.add_task(_execute_pipeline_task, job, llm)

    return {
        "job_id": job_id,
        "status": job.status.value,
        "workspace": job.workspace_dir
    }

@app.get("/api/jobs/{job_id}")
async def get_job_status_api(job_id: str):
    """Retrieves status, progress, and validation results of a job."""
    job = active_jobs.get(job_id)
    if not job:
        # Check if exists in workspace root
        job_dir = config.workspace_root / job_id
        if not job_dir.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        # Attempt to read completed artifacts
        rep_file = job_dir / "validation_report.json"
        rep_data = None
        if rep_file.exists():
            import json
            rep_data = json.loads(rep_file.read_text(encoding="utf-8"))
        return {
            "job_id": job_id,
            "status": "completed" if rep_file.exists() else "unknown",
            "validation_report": rep_data
        }

    return job.model_dump(mode="json")

@app.get("/api/jobs/{job_id}/download/{fmt}")
async def download_artifact_api(job_id: str, fmt: str):
    """Downloads an exported document or validation report."""
    job_dir = config.workspace_root / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job directory not found")

    fmt_lower = fmt.lower()
    if fmt_lower == "report":
        report_path = job_dir / "validation_report.md"
        if report_path.exists():
            return FileResponse(report_path, filename=f"validation_report_{job_id}.md")
        raise HTTPException(status_code=404, detail="Validation report not ready")

    export_dir = job_dir / "exports"
    matches = list(export_dir.glob(f"*.{fmt_lower}"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"No {fmt.upper()} export found for this job")

    target_file = matches[0]
    return FileResponse(target_file, filename=target_file.name)
