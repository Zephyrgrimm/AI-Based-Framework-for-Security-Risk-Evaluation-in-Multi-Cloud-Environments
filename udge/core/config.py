"""Configuration management for UDGE."""
import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

DEFAULT_SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.com",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice"
]

class UDGEConfig(BaseModel):
    # Workspace & storage
    workspace_root: Path = Field(default_factory=lambda: Path(os.environ.get("UDGE_WORKSPACE", ".udge_jobs")).resolve())
    temp_dir: Path = Field(default_factory=lambda: Path(os.environ.get("UDGE_TEMP", ".udge_jobs/tmp")).resolve())

    # LibreOffice configuration
    libreoffice_path: Optional[Path] = Field(default=None)
    libreoffice_timeout_sec: int = 120

    # OCR & Vision configuration
    min_pdf_text_density_per_page: int = 60  # Minimum characters to consider page non-scanned
    enable_local_ocr: bool = True
    enable_vision_ocr: bool = True
    ocr_dpi: int = 200

    # LLM Provider configuration
    default_llm_provider: str = Field(default_factory=lambda: os.environ.get("UDGE_LLM_PROVIDER", "mock"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    openai_model: str = Field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("GEMINI_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    anthropic_model: str = Field(default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"))
    ollama_base_url: str = Field(default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = Field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3.2"))

    def resolve_libreoffice(self) -> Path:
        """Finds a verified working LibreOffice executable."""
        if self.libreoffice_path and self.libreoffice_path.exists():
            return self.libreoffice_path

        env_path = os.environ.get("LIBREOFFICE_PATH")
        if env_path and Path(env_path).exists():
            self.libreoffice_path = Path(env_path)
            return self.libreoffice_path

        # Check standard Windows / Linux locations
        for p_str in DEFAULT_SOFFICE_PATHS:
            p = Path(p_str)
            if p.exists():
                self.libreoffice_path = p
                return self.libreoffice_path

        # Check PATH
        which_path = shutil.which("soffice") or shutil.which("libreoffice")
        if which_path:
            self.libreoffice_path = Path(which_path)
            return self.libreoffice_path

        raise FileNotFoundError(
            "LibreOffice executable (soffice.com or soffice.exe) could not be found. "
            "Please ensure LibreOffice is installed or set LIBREOFFICE_PATH."
        )

# Global default config instance
config = UDGEConfig()
config.workspace_root.mkdir(parents=True, exist_ok=True)
config.temp_dir.mkdir(parents=True, exist_ok=True)
