"""Command Line Interface for UDGE."""
import sys
from pathlib import Path
from typing import List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from udge.core.config import config
from udge.core.models import OutputFormat, GenerationJob
from udge.agents.intake import IntakeAgent
from udge.agents.orchestrator import MasterOrchestrator
from udge.template.parser import TemplateParser
from udge.ingestion.pipeline import IngestionPipeline

app = typer.Typer(
    name="udge",
    help="Universal Document Generation Engine - Agentic template-driven document synthesis",
    add_completion=False
)
console = Console(safe_box=True)

@app.command()
def generate(
    template: Path = typer.Option(..., "--template", "-t", help="Path to template file (.md, .txt, .docx, .pdf)"),
    sources: List[Path] = typer.Option(..., "--source", "-s", help="Path(s) to reference source documents"),
    formats: str = typer.Option("pdf,docx", "--formats", "-f", help="Comma-separated output formats: pdf, docx, odt, md, html"),
    llm: str = typer.Option("mock", "--llm", "-m", help="LLM Provider: mock, openai, gemini, ollama"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Custom destination directory for exports")
):
    """Generates a complete document from template and source materials."""
    console.print(Panel.fit("[bold blue]Universal Document Generation Engine (UDGE)[/bold blue]", border_style="blue"))

    # Parse output formats
    fmt_list = []
    for f in formats.split(","):
        cleaned = f.strip().lower()
        try:
            fmt_list.append(OutputFormat(cleaned))
        except ValueError:
            console.print(f"[red]Invalid format: '{cleaned}'. Allowed: pdf, docx, odt, md, html[/red]")
            raise typer.Exit(1)

    intake = IntakeAgent()
    try:
        job = intake.initialize_job(
            template_path=template,
            source_paths=sources,
            output_formats=fmt_list
        )
    except Exception as e:
        console.print(f"[bold red]Intake Error:[/bold red] {e}")
        raise typer.Exit(1)

    console.print(f"[green]Job Initialized:[/green] [bold]{job.job_id}[/bold]")
    console.print(f"Workspace: [dim]{job.workspace_dir}[/dim]\n")

    orchestrator = MasterOrchestrator(llm_provider_name=llm)

    with console.status("[bold green]Executing agentic pipeline...[/bold green]", spinner="dots"):
        try:
            completed_job = orchestrator.run(job)
        except Exception as e:
            console.print(f"\n[bold red]Pipeline Execution Failed:[/bold red] {e}")
            raise typer.Exit(1)

    console.print("\n[bold green][OK] Generation & QA Complete![/bold green]\n")

    # Display exports
    table = Table(title="Generated Document Outputs", border_style="cyan")
    table.add_column("Format", style="cyan", no_wrap=True)
    table.add_column("File Path", style="white")

    for fmt, p in completed_job.output_files.items():
        dest = Path(p)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            new_dest = output_dir / dest.name
            shutil.copy2(dest, new_dest)
            table.add_row(fmt.upper(), str(new_dest.resolve()))
        else:
            table.add_row(fmt.upper(), str(dest.resolve()))

    console.print(table)

    # Display QA validation summary
    if completed_job.validation_report:
        rep = completed_job.validation_report
        status_color = "green" if rep.passed else "red"
        console.print(Panel(
            f"[{status_color}]{rep.summary}[/{status_color}]\n"
            f"Detailed QA Report: [dim]{Path(job.workspace_dir) / 'validation_report.md'}[/dim]",
            title="Quality Assurance Verification",
            border_style=status_color
        ))

@app.command()
def inspect_template(template: Path = typer.Argument(..., help="Path to template file (.md, .txt, .docx, .pdf)")):
    """Parses and inspects the structure of a template."""
    parser = TemplateParser()
    try:
        spec = parser.parse_file(template)
    except Exception as e:
        console.print(f"[red]Error parsing template:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel.fit(f"[bold]{spec.title}[/bold] (Category: {spec.document_category.value})", border_style="green"))
    table = Table(title="Template Sections Hierarchy", border_style="green")
    table.add_column("Level", style="dim", width=6)
    table.add_column("Section Title", style="bold")
    table.add_column("Placeholders", style="yellow")
    table.add_column("Expected Words", style="cyan", width=15)

    for s in spec.sections:
        ph_str = ", ".join(s.placeholder_tokens) if s.placeholder_tokens else "-"
        wc_str = str(s.expected_word_count) if s.expected_word_count else "Adaptive"
        table.add_row(f"H{s.level}", s.title, ph_str, wc_str)

    console.print(table)

@app.command()
def inspect_sources(sources: List[Path] = typer.Argument(..., help="Source files to inspect")):
    """Ingests source files and displays extracted chunks and figures."""
    ingestion = IngestionPipeline()
    temp_out = config.temp_dir / "inspect_temp"
    try:
        catalog = ingestion.ingest_files(sources, temp_out)
    except Exception as e:
        console.print(f"[red]Extraction failed:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel.fit(f"Ingested {len(catalog.source_files)} source(s) into {len(catalog.chunks)} chunks", border_style="blue"))
    table = Table(title="Extracted Evidence Chunks", border_style="blue")
    table.add_column("Chunk ID", style="dim", width=12)
    table.add_column("Source", style="cyan", width=16)
    table.add_column("Location", style="yellow", width=18)
    table.add_column("Content Excerpt", style="white")

    for c in catalog.chunks[:15]:
        first_line = c.content.splitlines()[0] if c.content else ""
        table.add_row(c.id, c.source_file, c.location, first_line[:70] + ("..." if len(first_line) > 70 else ""))

    console.print(table)
    if catalog.extracted_images:
        console.print(f"[dim]Discovered {len(catalog.extracted_images)} embedded images/figures.[/dim]")

@app.command()
def check_env():
    """Diagnoses host environment, LibreOffice availability, and OCR engines."""
    table = Table(title="UDGE Environment Diagnostics", border_style="magenta")
    table.add_column("Component", style="bold")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    # Python
    table.add_row("Python", f"[green]OK ({sys.version.split()[0]})[/green]", sys.executable)

    # LibreOffice
    try:
        lo_path = config.resolve_libreoffice()
        table.add_row("LibreOffice", "[green]FOUND[/green]", str(lo_path))
    except Exception as e:
        table.add_row("LibreOffice", "[red]NOT FOUND[/red]", str(e))

    # OCR Engines
    ocr = IngestionPipeline().extractors[3]
    tess_status = "[green]Available[/green]" if getattr(ocr, "_tesseract_available", False) else "[yellow]Not in PATH (Pillow raster fallback active)[/yellow]"
    rapid_status = "[green]Available[/green]" if getattr(ocr, "_rapidocr_available", False) else "[dim]Not installed[/dim]"

    table.add_row("Tesseract OCR", tess_status, "Used for raster PDF / Image text recognition")
    table.add_row("RapidOCR", rapid_status, "Pure ONNX local OCR fallback")
    table.add_row("Workspace Dir", "[green]OK[/green]", str(config.workspace_root))

    console.print(table)

@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run Web UI"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address")
):
    """Launches the local interactive Web Dashboard."""
    import uvicorn
    console.print(Panel.fit(f"[bold green]Starting UDGE Web Dashboard on http://{host}:{port}[/bold green]"))
    uvicorn.run("udge.web.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    app()
