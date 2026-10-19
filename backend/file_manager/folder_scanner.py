
import os
from pathlib import Path


def scan_folder(
    folder_path: str | Path,
    allowed_root: str | Path,
    max_files: int = 1000,
) -> list[Path]:
    """Discover files within an explicitly allowed directory."""

    if max_files < 1:
        raise ValueError("max_files must be at least 1.")

    requested = Path(folder_path).expanduser()
    root_path = Path(allowed_root).expanduser()

    if requested.is_symlink() or root_path.is_symlink():
        raise PermissionError("Symbolic-link roots are not allowed.")

    try:
        root = root_path.resolve(strict=True)
        target = requested.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FileNotFoundError(
            "The requested directory could not be accessed."
        ) from exc

    if not root.is_dir() or not target.is_dir():
        raise NotADirectoryError("Both paths must be directories.")

    if not target.is_relative_to(root):
        raise PermissionError(
            "The requested folder is outside the allowed root."
        )

    discovered: list[Path] = []

    for current_path, directories, filenames in os.walk(
        target,
        followlinks=False,
    ):
        current = Path(current_path)

        directories[:] = sorted(
            name
            for name in directories
            if not (current / name).is_symlink()
        )

        for filename in sorted(filenames):
            file_path = current / filename

            if file_path.is_symlink():
                continue

            try:
                if not file_path.is_file():
                    continue
            except OSError:
                continue

            discovered.append(file_path)

            if len(discovered) >= max_files:
                return discovered

    return discovered
