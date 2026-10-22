from pathlib import Path

SUPPORTED_FILE_TYPES = {
    ".pdf": "pdf",
    ".docx": "word",
    ".doc": "word_legacy",
    ".txt": "text",
    ".md": "markdown",
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel_legacy",
    ".json": "json",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".html": "code",
    ".css": "code",
    ".java": "code",
    ".cpp": "code",
    ".c": "code",
    ".h": "code",
    ".sql": "code",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".log": "text",
    ".ini": "config",
    ".toml": "config",
}

def detect_file_type(file_path: str | Path) -> str:
    """Return the detected category for a file."""

    path = Path(file_path)

    if path.is_symlink():
        return "unsupported"

    return SUPPORTED_FILE_TYPES.get(
        path.suffix.lower(),
        "unsupported",
    )


def is_supported_file(file_path: str | Path) -> bool:
    """Check whether the file extension is supported."""

    return detect_file_type(file_path) != "unsupported"
