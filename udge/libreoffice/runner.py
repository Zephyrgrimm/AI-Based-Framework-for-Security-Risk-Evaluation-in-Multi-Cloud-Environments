"""Isolated headless LibreOffice execution runner."""
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional
from udge.core.config import config
from udge.core.exceptions import LibreOfficeError

class LibreOfficeRunner:
    """Executes LibreOffice headless commands safely with isolated user profiles."""

    def __init__(self, executable_path: Optional[Path] = None, timeout_sec: int = 120):
        self.exe_path = executable_path or config.resolve_libreoffice()
        self.timeout_sec = timeout_sec

    def convert(self, source_file: Path, target_format: str, output_dir: Path) -> Path:
        """Converts source_file to target_format (e.g. pdf, docx, odt) in output_dir."""
        if not source_file.exists():
            raise LibreOfficeError(f"Source file does not exist: {source_file}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create isolated temporary user profile for this invocation
        temp_profile_dir = Path(tempfile.gettempdir()) / f"lo_profile_{uuid.uuid4().hex[:8]}"
        temp_profile_dir.mkdir(parents=True, exist_ok=True)

        # Build file URI for UserInstallation on Windows / POSIX
        profile_uri = temp_profile_dir.resolve().as_uri()

        cmd = [
            str(self.exe_path),
            f"-env:UserInstallation={profile_uri}",
            "--headless",
            "--invisible",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
            "--nologo",
            "--norestore",
            "--convert-to",
            target_format,
            str(source_file.resolve()),
            "--outdir",
            str(output_dir.resolve())
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            if result.returncode != 0:
                raise LibreOfficeError(
                    f"LibreOffice conversion failed with exit code {result.returncode}.\n"
                    f"Stdout: {result.stdout}\nStderr: {result.stderr}"
                )

            expected_output = output_dir / f"{source_file.stem}.{target_format.lower()}"
            if not expected_output.exists():
                # Check for uppercase or alternate naming
                matches = list(output_dir.glob(f"{source_file.stem}*.{target_format.lower()}"))
                if matches:
                    return matches[0]
                raise LibreOfficeError(
                    f"LibreOffice completed with code 0 but expected output '{expected_output.name}' was not found."
                )

            return expected_output

        except subprocess.TimeoutExpired as e:
            raise LibreOfficeError(f"LibreOffice conversion timed out after {self.timeout_sec}s.") from e
        except Exception as e:
            raise LibreOfficeError(f"LibreOffice execution error: {e}") from e
        finally:
            # Clean up ephemeral user profile
            try:
                shutil.rmtree(temp_profile_dir, ignore_errors=True)
            except Exception:
                pass
