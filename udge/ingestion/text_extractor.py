"""Extractor for Markdown, plain text, and CSV files."""
import csv
from pathlib import Path
from typing import List
import uuid
from udge.core.models import EvidenceChunk, SourceType
from udge.ingestion.extractor_base import BaseExtractor

class TextExtractor(BaseExtractor):
    """Extracts text content from Markdown, TXT, and CSV files."""

    SUPPORTED_EXTS = {".md", ".markdown", ".txt", ".csv"}

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTS

    def extract(self, file_path: Path, output_dir: Path) -> List[EvidenceChunk]:
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return self._extract_csv(file_path)
        return self._extract_text_or_md(file_path, suffix)

    def _extract_text_or_md(self, file_path: Path, suffix: str) -> List[EvidenceChunk]:
        chunks: List[EvidenceChunk] = []
        source_type = SourceType.MARKDOWN if suffix in {".md", ".markdown"} else SourceType.TXT

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines()
        current_section = "Top"
        current_buffer: List[str] = []
        start_line = 1

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # If markdown heading, split chunk
            if suffix in {".md", ".markdown"} and stripped.startswith("#"):
                if current_buffer:
                    chunk_text = "\n".join(current_buffer).strip()
                    if chunk_text:
                        chunks.append(
                            EvidenceChunk(
                                id=f"chunk-{uuid.uuid4().hex[:8]}",
                                source_file=file_path.name,
                                source_type=source_type,
                                location=f"Lines {start_line}-{i-1} ({current_section})",
                                content=chunk_text
                            )
                        )
                    current_buffer = []
                current_section = stripped.lstrip("#").strip()
                start_line = i
            current_buffer.append(line)

            # Keep chunk sizes reasonable (max ~60 lines per chunk)
            if len(current_buffer) >= 60:
                chunk_text = "\n".join(current_buffer).strip()
                if chunk_text:
                    chunks.append(
                        EvidenceChunk(
                            id=f"chunk-{uuid.uuid4().hex[:8]}",
                            source_file=file_path.name,
                            source_type=source_type,
                            location=f"Lines {start_line}-{i} ({current_section})",
                            content=chunk_text
                        )
                    )
                current_buffer = []
                start_line = i + 1

        if current_buffer:
            chunk_text = "\n".join(current_buffer).strip()
            if chunk_text:
                chunks.append(
                    EvidenceChunk(
                        id=f"chunk-{uuid.uuid4().hex[:8]}",
                        source_file=file_path.name,
                        source_type=source_type,
                        location=f"Lines {start_line}-{len(lines)} ({current_section})",
                        content=chunk_text
                    )
                )

        return chunks

    def _extract_csv(self, file_path: Path) -> List[EvidenceChunk]:
        chunks: List[EvidenceChunk] = []
        rows: List[List[str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for r in reader:
                    rows.append(r)
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV {file_path}: {e}")

        if not rows:
            return chunks

        # Format CSV rows into markdown table representation for chunk content
        header = rows[0]
        md_table_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]
        for row in rows[1:100]:  # up to 100 rows per chunk
            padded_row = row + [""] * (len(header) - len(row))
            md_table_lines.append("| " + " | ".join(padded_row[:len(header)]) + " |")

        content_str = f"CSV Table: {file_path.name}\n" + "\n".join(md_table_lines)
        chunks.append(
            EvidenceChunk(
                id=f"chunk-{uuid.uuid4().hex[:8]}",
                source_file=file_path.name,
                source_type=SourceType.CSV,
                location="Sheet/Table",
                content=content_str,
                tables=[rows]
            )
        )
        return chunks
