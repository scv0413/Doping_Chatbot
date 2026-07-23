import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz


DEFAULT_OCR_LANGUAGE = "kor+eng"
DEFAULT_OCR_DPI = 300


class TesseractError(RuntimeError):
    """Base error for local Tesseract OCR failures."""


class TesseractUnavailableError(TesseractError):
    """Raised when Tesseract or a requested language pack is unavailable."""


class TesseractExecutionError(TesseractError):
    """Raised when Tesseract exits without a successful OCR result."""


def ensure_tesseract_available(*, language: str = DEFAULT_OCR_LANGUAGE) -> None:
    executable = shutil.which("tesseract")
    if executable is None:
        raise TesseractUnavailableError(
            "tesseract executable was not found. Install Tesseract and ensure it is on PATH."
        )

    completed = subprocess.run(
        [executable, "--list-langs"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise TesseractUnavailableError(
            f"tesseract language check failed: {completed.stderr.strip() or 'unknown error'}"
        )

    available_languages = set(completed.stdout.splitlines())
    missing_languages = set(language.split("+")) - available_languages
    if missing_languages:
        missing = ", ".join(sorted(missing_languages))
        raise TesseractUnavailableError(
            f"tesseract language data is missing: {missing}. Run 'tesseract --list-langs' to verify."
        )


def render_page_to_png(page: fitz.Page, *, dpi: int = DEFAULT_OCR_DPI) -> bytes:
    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pixmap.tobytes("png")


def run_tesseract_ocr(
    page: fitz.Page,
    *,
    language: str = DEFAULT_OCR_LANGUAGE,
    dpi: int = DEFAULT_OCR_DPI,
) -> str:
    ensure_tesseract_available(language=language)

    with TemporaryDirectory() as directory:
        image_path = Path(directory) / "page.png"
        image_path.write_bytes(render_page_to_png(page, dpi=dpi))
        completed = subprocess.run(
            ["tesseract", str(image_path), "stdout", "-l", language],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

    if completed.returncode != 0:
        raise TesseractExecutionError(completed.stderr.strip() or "tesseract OCR failed")

    return completed.stdout.strip()
