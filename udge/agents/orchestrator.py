"""Master agentic pipeline orchestrator for UDGE."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from udge.core.models import (
    GenerationJob,
    JobStatus,
    OutputFormat,
    EvidenceCatalog,
    TemplateSpec,
    GeneratedSection
)
from udge.core.exceptions import UDGEError
from udge.ingestion.pipeline import IngestionPipeline
from udge.template.parser import TemplateParser
from udge.prompt_engine.builder import PromptBuilder
from udge.llm.factory import get_llm_provider
from udge.agents.intake import IntakeAgent
from udge.agents.mapping import ContentMappingAgent
from udge.agents.section_gen import SectionGenAgent
from udge.agents.editorial import EditorialAgent
from udge.libreoffice.styler import DocumentStyler
from udge.libreoffice.converter import DocumentConverter
from udge.qa.validator import DocumentQAValidator
from udge.qa.reporter import ValidationReporter

class MasterOrchestrator:
    """Coordinates the full document generation pipeline through distinct agent stages."""

    def __init__(
        self,
        llm_provider_name: Optional[str] = None,
        ingestion_pipeline: Optional[IngestionPipeline] = None
    ):
        self.llm = get_llm_provider(llm_provider_name)
        self.prompt_builder = PromptBuilder()
        self.ingestion = ingestion_pipeline or IngestionPipeline()
        self.template_parser = TemplateParser()
        self.mapping_agent = ContentMappingAgent()
        self.section_gen_agent = SectionGenAgent(self.llm, self.prompt_builder)
        self.editorial_agent = EditorialAgent(self.llm, self.prompt_builder)
        self.styler = DocumentStyler()
        self.converter = DocumentConverter()
        self.validator = DocumentQAValidator()
        self.reporter = ValidationReporter()

    def run(self, job: GenerationJob) -> GenerationJob:
        """Executes the complete generation and QA validation pipeline."""
        workspace = Path(job.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Document Ingestion & Extraction (including Scanned PDF & OCR)
            job.status = JobStatus.INGESTING
            catalog: EvidenceCatalog = self.ingestion.ingest_files(
                file_paths=[Path(s) for s in job.source_paths],
                output_dir=workspace / "ingested"
            )

            # Stage 2: Template Analysis
            job.status = JobStatus.ANALYZING_TEMPLATE
            spec: TemplateSpec = self.template_parser.parse_file(Path(job.template_path))

            # Stage 3: Content & Evidence Mapping
            job.status = JobStatus.MAPPING_CONTENT
            mapping_plan = self.mapping_agent.map_content(spec, catalog)

            # Save intermediate mapping plan
            (workspace / "content_mapping_plan.json").write_text(
                mapping_plan.model_dump_json(indent=2),
                encoding="utf-8"
            )

            # Stage 4: Section-by-Section Generation
            job.status = JobStatus.GENERATING_SECTIONS
            chunk_lookup = {c.id: c for c in catalog.chunks}
            generated_sections: List[GeneratedSection] = []

            for mapping in mapping_plan.mappings:
                sec = next((s for s in spec.sections if s.id == mapping.section_id), None)
                if not sec:
                    continue

                matched_chunks = [chunk_lookup[cid] for cid in mapping.relevant_chunk_ids if cid in chunk_lookup]
                gen_sec = self.section_gen_agent.generate_section(
                    spec=spec,
                    section=sec,
                    evidence_chunks=matched_chunks
                )
                generated_sections.append(gen_sec)

            # Stage 5: Editorial & Consistency Review
            job.status = JobStatus.EDITORIAL_REVIEW
            reviewed_sections = self.editorial_agent.review_sections(
                doc_title=spec.title,
                sections=generated_sections
            )

            # Stage 6: Assembly & Rendering via LibreOffice
            job.status = JobStatus.RENDERING
            intermediate_md_path = workspace / "assembled.md"
            intermediate_docx_path = workspace / "assembled.docx"

            # 6a: Save assembled Markdown
            md_content = self.styler.build_markdown(spec, reviewed_sections)
            intermediate_md_path.write_text(md_content, encoding="utf-8")

            # 6b: Save assembled styled DOCX
            self.styler.build_docx(
                spec=spec,
                sections=reviewed_sections,
                catalog=catalog,
                output_path=intermediate_docx_path
            )

            # 6c: Convert to requested output formats using LibreOffice
            output_dir = workspace / "exports"
            converted_files = self.converter.convert_all(
                intermediate_docx=intermediate_docx_path,
                intermediate_md=intermediate_md_path,
                target_formats=job.output_formats,
                output_dir=output_dir
            )

            job.output_files = {k: str(v) for k, v in converted_files.items()}

            # Stage 7: Quality Assurance & Validation
            job.status = JobStatus.VALIDATING
            val_report = self.validator.validate(
                spec=spec,
                sections=reviewed_sections,
                catalog=catalog,
                output_files=converted_files
            )
            job.validation_report = val_report

            # Save validation reports
            self.reporter.save_json(val_report, workspace / "validation_report.json")
            self.reporter.save_markdown(val_report, workspace / "validation_report.md")

            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.now(timezone.utc)
            return job

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            raise UDGEError(f"Generation pipeline failed at stage '{job.status}': {e}") from e
