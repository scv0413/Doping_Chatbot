"""Safe acquisition helpers for official PDF source candidates."""

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MIN_PDF_BYTES = 1024
PDF_SIGNATURE = b"%PDF-"
DEFAULT_ALLOWED_HOSTS = (
    "wada-ama.org",
    "www.wada-ama.org",
    "kada-ad.or.kr",
    "www.kada-ad.or.kr",
)


class PdfAcquisitionError(RuntimeError):
    """Raised when an official source download cannot be safely accepted."""


def validate_downloaded_pdf(path: Path) -> None:
    """Reject empty, too-small, or non-PDF responses before they become sources."""

    if not path.is_file():
        raise PdfAcquisitionError(f"Downloaded file is missing: {path}")

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise PdfAcquisitionError("Downloaded response is empty.")
    if size_bytes < MIN_PDF_BYTES:
        raise PdfAcquisitionError(
            f"Downloaded response is too small for a source PDF: {size_bytes} bytes."
        )

    with path.open("rb") as source_file:
        signature = source_file.read(len(PDF_SIGNATURE))
    if signature != PDF_SIGNATURE:
        raise PdfAcquisitionError("Downloaded response is not a PDF file.")


def download_official_pdf(
    url: str,
    output_path: Path,
    *,
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
    timeout_seconds: int = 30,
) -> None:
    """Download a trusted PDF atomically, leaving no invalid output behind."""

    validate_source_url(url, allowed_hosts=allowed_hosts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "doping-chatbot-source-audit/0.1"})

    with NamedTemporaryFile(dir=output_path.parent, suffix=".download", delete=False) as temp_file:
        temporary_path = Path(temp_file.name)

    try:
        with urlopen(request, timeout=timeout_seconds) as response, temporary_path.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
        validate_downloaded_pdf(temporary_path)
        temporary_path.replace(output_path)
    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        if isinstance(error, PdfAcquisitionError):
            raise
        raise PdfAcquisitionError(f"Official PDF download failed: {error}") from error


def validate_source_url(url: str, *, allowed_hosts: tuple[str, ...]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        allowed = ", ".join(allowed_hosts)
        raise PdfAcquisitionError(f"Source URL must use HTTPS from an allowed host: {allowed}")
