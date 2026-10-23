from pathlib import Path

SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".toml",
    ".html",
    ".css",
    ".sql",
}

MAX_TEXT_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def extract_text_from_file(file_path: str | Path) -> str:
    """
    Extract text from a supported text-based file.

    This function reads file contents but does not modify the file.
    """
    path = Path(file_path).expanduser()

    if path.is_symlink():
        raise PermissionError("Symbolic-link files are not allowed.")

    try:
        resolved_path = path.resolve(strict=True)

        if not resolved_path.is_file():
            raise ValueError("The provided path is not a file.")

        if resolved_path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
            raise ValueError(
                f"Unsupported text file extension: {resolved_path.suffix}"
            )

        if resolved_path.stat().st_size > MAX_TEXT_FILE_SIZE:
            raise ValueError("The file exceeds the 5 MB size limit.")

        with resolved_path.open("r", encoding="utf-8-sig") as file:
            content = file.read(MAX_TEXT_FILE_SIZE + 1)

        if len(content.encode("utf-8")) > MAX_TEXT_FILE_SIZE:
            raise ValueError("The decoded text exceeds the 5 MB size limit.")

        return content

    except UnicodeDecodeError as exc:
        raise ValueError(
            "The file is not valid UTF-8 text."
        ) from exc

