from pathlib import Path
from pypdf import PdfReader

MAX_PDF_SIZE_BYTES = 40 * 1024 * 1024  # 40 MB
MAX_PDF_PAGES = 500

def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract text from a PDF document.

    This function reads text-based PDF content. It does not perform OCR
    on scanned pages that contain only images.
    """
    path = Path(file_path).expanduser()

    if path.is_symlink():
        raise PermissionError("Symbolic-link files are not allowed.")

    try:
        resolved_path = path.resolve(strict=True)

        if not resolved_path.is_file():
            raise ValueError("The provided path is not a file.")

        if resolved_path.suffix.lower() != ".pdf":
            raise ValueError("The provided file must have a .pdf extension.")

        if resolved_path.stat().st_size > MAX_PDF_SIZE_BYTES:
            raise ValueError("The PDF exceeds the 40 MB size limit.")

        reader = PdfReader(str(resolved_path), strict=True)

        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError("The PDF exceeds the 500-page limit.")

        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                raise ValueError(
                    f"Could not extract text from PDF page {page_number}."
                ) from exc

            if text.strip():
                extracted_pages.append(text.strip())

        return "\n\n".join(extracted_pages)

    except (OSError, Exception) as exc:
        if isinstance(exc, (ValueError, PermissionError)):
            raise

        raise ValueError(
            "The PDF could not be opened or processed."
        ) from exc
