"""Template specification validation and utilities."""
from typing import List
from udge.core.exceptions import TemplateError
from udge.core.models import TemplateSpec, TemplateSection

def validate_template_spec(spec: TemplateSpec) -> List[str]:
    """Validates that a template specification contains necessary structural elements."""
    warnings: List[str] = []

    if not spec.title or spec.title == "Untitled Document":
        warnings.append("Document has default title 'Untitled Document'.")

    if not spec.sections:
        raise TemplateError("Template must contain at least one heading/section.")

    # Check for duplicate section IDs
    seen_ids = set()
    for s in spec.sections:
        if s.id in seen_ids:
            raise TemplateError(f"Duplicate section ID detected in template: '{s.id}'")
        seen_ids.add(s.id)

    return warnings
