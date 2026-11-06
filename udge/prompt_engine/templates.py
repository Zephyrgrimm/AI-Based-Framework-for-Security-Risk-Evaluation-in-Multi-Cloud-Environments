"""Modular prompt components and behavioural constraints for UDGE."""

SYSTEM_GROUNDING_RULES = """
You are a precision document generation engine. You must follow these strict operational rules:
1. TRUTHFULNESS & GROUNDING: Generate content grounded ONLY in the provided source evidence.
2. ZERO FABRICATION: Never invent facts, data, statistics, dates, or source citations.
3. CITATION DISCIPLINE: Every factual claim must include an inline citation tag in the exact format: [Source: <filename>, <location>].
4. MISSING INFORMATION: If the provided evidence lacks details required by the section instructions or placeholders, do NOT guess. Insert an explicit flag: [MISSING_INFORMATION: <description of missing item>].
5. CONTRADICTIONS: If source documents contradict each other, explicitly note the discrepancy: [CONTRADICTION: <details>].
6. PROFESSIONAL TONE: Write in publication-ready, formal prose suitable for the specified document category.
"""

SECTION_GENERATION_TEMPLATE = """
DOCUMENT CATEGORY: {category}
DOCUMENT TITLE: {doc_title}

SECTION TITLE: {section_title} (Heading Level {level})
SECTION INSTRUCTIONS:
{instructions}

REQUESTED PLACEHOLDERS:
{placeholders}

EXPECTED DETAIL / WORD COUNT: {word_count_hint}

VERIFIED SOURCE EVIDENCE:
{evidence_blocks}

TASK:
Write the complete text for section "{section_title}".
- Follow all section instructions.
- Base all assertions on the provided evidence blocks.
- Include accurate inline citations: [Source: <filename>, <location>].
- If critical evidence is missing, state [MISSING_INFORMATION: ...].
- Output markdown content only (do not repeat the top-level section heading itself, write the section body).
"""

EDITORIAL_REVIEW_TEMPLATE = """
DOCUMENT TITLE: {doc_title}
SECTION: {section_title}

DRAFT CONTENT:
{draft_content}

TASK:
Review the draft content for:
1. Clarity and flow.
2. Removal of redundancies.
3. Preservation of all citations and [MISSING_INFORMATION: ...] tags.
4. Professional tone.

Output the polished version of the draft text. Do not omit citations or missing information tags.
"""
