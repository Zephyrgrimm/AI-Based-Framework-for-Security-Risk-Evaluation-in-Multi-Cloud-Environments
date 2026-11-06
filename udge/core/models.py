"""Core Pydantic data models for UDGE."""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class SourceType(str, Enum):
    MARKDOWN = "markdown"
    TXT = "txt"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    PDF = "pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"
    ODT = "odt"
    OTHER = "other"

class OutputFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    ODT = "odt"
    HTML = "html"
    MARKDOWN = "md"

class DocumentCategory(str, Enum):
    ACADEMIC_REPORT = "academic_report"
    TECHNICAL_DOC = "technical_doc"
    BUSINESS_PROPOSAL = "business_proposal"
    PROJECT_REPORT = "project_report"
    RESEARCH_SUMMARY = "research_summary"
    MANUAL = "manual"
    GENERAL = "general"

class EvidenceChunk(BaseModel):
    id: str
    source_file: str
    source_type: SourceType
    location: str = ""  # e.g., "Page 2", "Slide 4", "Sheet 'Q3'", "Line 120"
    content: str
    tables: List[List[List[str]]] = Field(default_factory=list)
    image_paths: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    is_ocr: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidenceCatalog(BaseModel):
    source_files: List[str] = Field(default_factory=list)
    chunks: List[EvidenceChunk] = Field(default_factory=list)
    extracted_images: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_chunk(self, chunk_id: str) -> Optional[EvidenceChunk]:
        for c in self.chunks:
            if c.id == chunk_id:
                return c
        return None

class TemplateSection(BaseModel):
    id: str
    title: str
    level: int = 1
    order: int = 0
    instructions: str = ""
    placeholder_tokens: List[str] = Field(default_factory=list)
    required: bool = True
    parent_id: Optional[str] = None
    expected_word_count: Optional[int] = None
    raw_markdown: str = ""

class TemplateSpec(BaseModel):
    title: str = "Untitled Document"
    document_category: DocumentCategory = DocumentCategory.GENERAL
    sections: List[TemplateSection] = Field(default_factory=list)
    style_rules: Dict[str, Any] = Field(default_factory=dict)
    require_citations: bool = True
    include_toc: bool = True
    custom_instructions: str = ""

class SectionMapping(BaseModel):
    section_id: str
    section_title: str
    relevant_chunk_ids: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    coverage_score: float = 1.0  # 0.0 - 1.0

class ContentMappingPlan(BaseModel):
    mappings: List[SectionMapping] = Field(default_factory=list)
    unassigned_chunks: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)

class GeneratedSection(BaseModel):
    section_id: str
    title: str
    level: int = 1
    content: str
    inline_citations: List[str] = Field(default_factory=list)
    missing_info_flags: List[str] = Field(default_factory=list)
    status: str = "completed"

class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ValidationItem(BaseModel):
    code: str
    severity: ValidationSeverity
    message: str
    section_id: Optional[str] = None
    source_ref: Optional[str] = None

class ValidationReport(BaseModel):
    passed: bool
    total_checks: int
    errors: List[ValidationItem] = Field(default_factory=list)
    warnings: List[ValidationItem] = Field(default_factory=list)
    info: List[ValidationItem] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JobStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    ANALYZING_TEMPLATE = "analyzing_template"
    MAPPING_CONTENT = "mapping_content"
    GENERATING_SECTIONS = "generating_sections"
    EDITORIAL_REVIEW = "editorial_review"
    RENDERING = "rendering"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerationJob(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    template_path: str
    source_paths: List[str] = Field(default_factory=list)
    output_formats: List[OutputFormat] = Field(default_factory=lambda: [OutputFormat.PDF, OutputFormat.DOCX])
    output_files: Dict[str, str] = Field(default_factory=dict)
    workspace_dir: str
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    validation_report: Optional[ValidationReport] = None
