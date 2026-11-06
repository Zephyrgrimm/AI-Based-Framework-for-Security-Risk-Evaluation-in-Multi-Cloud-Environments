"""Quality Assurance and Document Validation Engine."""
import re
from pathlib import Path
from typing import Dict, List, Optional
from udge.core.models import (
    TemplateSpec,
    GeneratedSection,
    EvidenceCatalog,
    ValidationReport,
    ValidationItem,
    ValidationSeverity
)

UNRESOLVED_PLACEHOLDER_REGEX = re.compile(r"(\{\{[A-Za-z0-9_\s\-]+\}\}|\[INSERT\s+[^\]]+\])")

class DocumentQAValidator:
    """Performs structural, citation, semantic, and output validation on generated documents."""

    def validate(
        self,
        spec: TemplateSpec,
        sections: List[GeneratedSection],
        catalog: EvidenceCatalog,
        output_files: Optional[Dict[str, Path]] = None
    ) -> ValidationReport:
        items: List[ValidationItem] = []
        total_checks = 0

        # 1. Structural Completeness Check
        total_checks += len(spec.sections)
        gen_section_titles = {s.title.lower() for s in sections}
        for sec in spec.sections:
            if sec.required and sec.title.lower() not in gen_section_titles:
                items.append(
                    ValidationItem(
                        code="STRUCT_MISSING_SECTION",
                        severity=ValidationSeverity.ERROR,
                        message=f"Required section '{sec.title}' was omitted from generated output.",
                        section_id=sec.id
                    )
                )

        # 2. Unresolved Placeholder Check
        total_checks += len(sections)
        for sec in sections:
            matches = UNRESOLVED_PLACEHOLDER_REGEX.findall(sec.content)
            for m in matches:
                items.append(
                    ValidationItem(
                        code="CONTENT_UNRESOLVED_PLACEHOLDER",
                        severity=ValidationSeverity.WARNING,
                        message=f"Unresolved placeholder detected: {m}",
                        section_id=sec.section_id
                    )
                )

        # 3. Citation & Grounding Check
        total_checks += len(sections)
        all_sources = set(catalog.source_files)
        for sec in sections:
            if spec.require_citations and not sec.inline_citations and "[MISSING_INFORMATION:" not in sec.content:
                items.append(
                    ValidationItem(
                        code="CITATION_MISSING",
                        severity=ValidationSeverity.WARNING,
                        message=f"Section '{sec.title}' has claims without inline source citations.",
                        section_id=sec.section_id
                    )
                )

            # Check if cited sources exist in catalog
            for cit in sec.inline_citations:
                matched_source = any(src.lower() in cit.lower() for src in all_sources)
                if not matched_source and all_sources:
                    items.append(
                        ValidationItem(
                            code="CITATION_UNVERIFIED_SOURCE",
                            severity=ValidationSeverity.WARNING,
                            message=f"Citation refers to unverified source file: {cit}",
                            section_id=sec.section_id
                        )
                    )

        # 4. Missing Information Tracking
        for sec in sections:
            for flag in sec.missing_info_flags:
                items.append(
                    ValidationItem(
                        code="DATA_MISSING_INFORMATION",
                        severity=ValidationSeverity.INFO,
                        message=f"Source data gap flagged: {flag}",
                        section_id=sec.section_id
                    )
                )

        # 5. Output Artifact Verification
        if output_files:
            total_checks += len(output_files)
            for fmt, fpath in output_files.items():
                p = Path(fpath)
                if not p.exists() or p.stat().st_size == 0:
                    items.append(
                        ValidationItem(
                            code="OUTPUT_FILE_INVALID",
                            severity=ValidationSeverity.ERROR,
                            message=f"Exported {fmt.upper()} output file is missing or empty: {p.name}"
                        )
                    )

        errors = [i for i in items if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in items if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in items if i.severity == ValidationSeverity.INFO]
        passed = len(errors) == 0

        summary = (
            f"Validation {'PASSED' if passed else 'FAILED'}: "
            f"{total_checks} checks executed. "
            f"{len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} notice(s)."
        )

        return ValidationReport(
            passed=passed,
            total_checks=total_checks,
            errors=errors,
            warnings=warnings,
            info=infos,
            summary=summary
        )
