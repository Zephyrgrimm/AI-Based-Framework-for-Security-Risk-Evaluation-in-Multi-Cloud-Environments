"""Intake and Requirements Agent."""
from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from udge.core.config import config
from udge.core.exceptions import IngestionError
from udge.core.models import GenerationJob, JobStatus, OutputFormat

class IntakeAgent:
    """Validates inputs, initializes job workspace, and prepares pipeline execution."""

    def initialize_job(
        self,
        template_path: Path,
        source_paths: List[Path],
        output_formats: Optional[List[OutputFormat]] = None,
        job_id: Optional[str] = None
    ) -> GenerationJob:
        """Validates input paths and creates job workspace."""
        if not template_path.exists():
            raise IngestionError(f"Template file not found: {template_path}")

        valid_sources = []
        for src in source_paths:
            p = Path(src).resolve()
            if not p.exists():
                raise IngestionError(f"Source file not found: {p}")
            valid_sources.append(str(p))

        jid = job_id or f"job-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        job_workspace = config.workspace_root / jid
        job_workspace.mkdir(parents=True, exist_ok=True)

        return GenerationJob(
            job_id=jid,
            status=JobStatus.PENDING,
            template_path=str(template_path.resolve()),
            source_paths=valid_sources,
            output_formats=output_formats or [OutputFormat.PDF, OutputFormat.DOCX],
            workspace_dir=str(job_workspace)
        )
