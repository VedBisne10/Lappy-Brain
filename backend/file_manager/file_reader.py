from pathlib import Path
from backend.file_manager.file_detector import detect_file_type

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

READABLE_TEXT_TYPES = {
    "text",
    "markdown",
    "code",
    "json",
    "xml",
    "yaml",
    "config",
}


def read_text_file(
    file_path: str | Path,
    allowed_root: str | Path,
) -> str:
    """
    Read a supported text-based file inside an allowed directory.

    The reader does not process PDFs, Word documents, or spreadsheets.
    """

    path = Path(file_path).expanduser()
    root_path = Path(allowed_root).expanduser()

    if path.is_symlink() or root_path.is_symlink():
        raise PermissionError("Symbolic-link paths are not allowed.")

    try:
        root = root_path.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FileNotFoundError(
            "The requested file or allowed directory was not found."
        ) from exc

    if not root.is_dir():
        raise NotADirectoryError("The allowed root must be a directory.")

    if not resolved_path.is_relative_to(root):
        raise PermissionError(
            "The requested file is outside the allowed root."
        )

    if not resolved_path.is_file():
        raise ValueError("The requested path is not a file.")

    file_type = detect_file_type(resolved_path)

    if file_type not in READABLE_TEXT_TYPES:
        raise ValueError(
            f"Text reading is not supported for this file type: {file_type}"
        )

    if resolved_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise ValueError("The file exceeds the 5 MB reading limit.")

    with resolved_path.open("r", encoding="utf-8-sig") as file:
        content = file.read(MAX_FILE_SIZE_BYTES + 1)

    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise ValueError("The decoded file content exceeds the reading limit.")

    return content
