
from pathlib import Path

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

SUPPORTED_CODE_EXTENSIONS = {
    ".py", ".java", ".js", ".jsx", ".ts", ".tsx",
    ".c", ".h", ".cpp", ".hpp", ".cs",
    ".go", ".rs", ".php", ".rb", ".swift", ".kt",
    ".html", ".css", ".scss", ".sql",
    ".json", ".yaml", ".yml", ".xml",
    ".sh", ".bat", ".ps1",
    ".env.example", ".toml", ".ini",
    ".md", ".txt",
}


def extract_text_from_code(file_path: str | Path) -> str:
    """
    Read a supported source-code or configuration file.

    Returns the file contents as text.
    """
    path = Path(file_path)

    if path.is_symlink():
        raise ValueError("Symbolic links are not allowed.")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_CODE_EXTENSIONS:
        raise ValueError(
            f"Unsupported code file extension: {path.suffix}"
        )

    file_size = path.stat().st_size

    if file_size > MAX_FILE_SIZE:
        raise ValueError("Code file exceeds the 25 MB size limit.")

    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The code file is not valid UTF-8 text."
        ) from exc
    except OSError as exc:
        raise OSError(f"Could not read code file: {path}") from exc
