from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def extract_metadata(file_path: str | Path) -> dict[str, Any]:
    """Extract basic metadata without reading file contents."""

    path = Path(file_path)

    if path.is_symlink():
        raise PermissionError("Symbolic-link files are not allowed.")

    try:
        resolved_path = path.resolve(strict=True)

        if not resolved_path.is_file():
            raise ValueError("The provided path is not a file.")

        stat = resolved_path.stat()

    except (OSError, RuntimeError) as exc:
        raise FileNotFoundError(
            f"Cannot access file: {path}"
        ) from exc

    created_timestamp = getattr(stat, "st_birthtime", None)

    return {
        "name": resolved_path.name,
        "path": str(resolved_path),
        "extension": resolved_path.suffix.lower(),
        "size_bytes": stat.st_size,
        "created_at": (
            datetime.fromtimestamp(
                created_timestamp, tz=timezone.utc
            ).isoformat()
            if created_timestamp is not None
            else None
        ),
        "modified_at": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "is_hidden": resolved_path.name.startswith("."),
    }
