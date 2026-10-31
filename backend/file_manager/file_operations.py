import os
from pathlib import Path
from typing import Any


def _resolve_allowed_root(
    path: str | Path,
    allowed_roots: list[str | Path],
) -> tuple[Path, Path]:
    """Resolve a path and verify that it belongs to an authorized root."""

    requested = Path(path).expanduser()

    # Reject symbolic links in the requested path.
    current = Path(requested.anchor)

    for part in requested.parts[1:]:
        current = current / part

        if current.is_symlink():
            raise PermissionError("Symbolic-link paths are not allowed.")

    try:
        resolved = requested.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError("The requested path cannot be resolved.") from exc

    for root_path in allowed_roots:
        root = Path(root_path).expanduser()

        if root.is_symlink():
            continue

        try:
            resolved_root = root.resolve(strict=True)

            if resolved.is_relative_to(resolved_root):
                return resolved, resolved_root

        except (OSError, RuntimeError):
            continue

    raise PermissionError("The requested path is outside authorized locations.")


def _validate_existing_path(
    path: str | Path,
    allowed_roots: list[str | Path],
) -> Path:
    """Validate an existing file or directory inside an authorized root."""

    resolved, root = _resolve_allowed_root(path, allowed_roots)

    try:
        existing = resolved.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FileNotFoundError("The requested path does not exist.") from exc

    if not existing.is_relative_to(root):
        raise PermissionError("The requested path is outside its authorized root.")

    return existing


def _validate_new_path(
    path: str | Path,
    allowed_roots: list[str | Path],
) -> Path:
    """Validate a new destination using its existing parent directory."""

    resolved, root = _resolve_allowed_root(path, allowed_roots)

    if resolved == root:
        raise ValueError("An operation cannot replace an authorized root.")

    if resolved.exists():
        raise FileExistsError(f"The destination already exists: {resolved}")

    parent = resolved.parent

    try:
        resolved_parent = parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FileNotFoundError(
            "The destination parent directory does not exist."
        ) from exc

    if not resolved_parent.is_dir():
        raise NotADirectoryError("The destination parent must be a directory.")

    if not resolved_parent.is_relative_to(root):
        raise PermissionError("The destination is outside its authorized root.")

    return resolved


def create_folder(
    folder_path: str | Path,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    """Create a new directory inside an authorized location."""

    destination = _validate_new_path(folder_path, allowed_roots)

    try:
        destination.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        raise
    except OSError as exc:
        raise OSError("The folder could not be created.") from exc

    return {
        "status": "created",
        "type": "folder",
        "path": str(destination),
    }


def create_file(
    file_path: str | Path,
    allowed_roots: list[str | Path],
    content: str = "",
) -> dict[str, Any]:
    """Create a new UTF-8 text file without overwriting existing content."""

    if not isinstance(content, str):
        raise TypeError("File content must be a string.")

    destination = _validate_new_path(file_path, allowed_roots)

    # Exclusive creation prevents accidental overwriting of existing files.
    try:
        with destination.open("x", encoding="utf-8", newline="") as file:
            file.write(content)

    except FileExistsError:
        raise
    except OSError as exc:
        raise OSError("The file could not be created.") from exc

    return {
        "status": "created",
        "type": "file",
        "path": str(destination),
        "size_bytes": destination.stat().st_size,
    }


def rename_path(
    source_path: str | Path,
    new_name: str,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    """Rename a file or directory without replacing another entry."""

    if not new_name or new_name.strip() != new_name:
        raise ValueError("A valid new name is required.")

    if new_name in {".", ".."} or Path(new_name).name != new_name:
        raise ValueError("The new name must not contain directory components.")

    source = _validate_existing_path(source_path, allowed_roots)
    destination = source.with_name(new_name)

    _validate_new_path(destination, allowed_roots)

    try:
        renamed = source.rename(destination)
    except OSError as exc:
        raise OSError("The path could not be renamed.") from exc

    return {
        "status": "renamed",
        "old_path": str(source),
        "new_path": str(renamed),
    }


def move_path(
    source_path: str | Path,
    destination_path: str | Path,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    """Move a file or directory without overwriting an existing destination."""

    source = _validate_existing_path(source_path, allowed_roots)
    destination = _validate_new_path(destination_path, allowed_roots)

    # Prevent moving a directory into itself or one of its descendants.
    if source.is_dir() and destination.is_relative_to(source):
        raise ValueError("A directory cannot be moved inside itself.")

    try:
        moved = source.rename(destination)
    except OSError as exc:
        raise OSError(
            "The path could not be moved. Cross-drive moves may require "
            "a copy-and-delete implementation."
        ) from exc

    return {
        "status": "moved",
        "old_path": str(source),
        "new_path": str(moved),
    }


def list_directory(
    directory_path: str | Path,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    """List files and folders inside an authorized directory."""

    directory = _validate_existing_path(directory_path, allowed_roots)

    if not directory.is_dir():
        raise NotADirectoryError("The requested path is not a directory.")

    entries = []

    try:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                # Skip symbolic links and inaccessible entries.
                try:
                    if entry.is_symlink():
                        continue

                    entry_type = (
                        "folder"
                        if entry.is_dir(follow_symlinks=False)
                        else "file"
                    )

                    entries.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": entry_type,
                    })

                except OSError:
                    continue

    except OSError as exc:
        raise OSError("The directory could not be listed.") from exc

    entries.sort(key=lambda item: (item["type"] != "folder", item["name"].casefold()))

    return {
        "path": str(directory),
        "entry_count": len(entries),
        "entries": entries,
    }


def delete_path(
    target_path: str | Path,
    allowed_roots: list[str | Path],
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a file or empty directory after explicit confirmation."""

    if confirm is not True:
        raise PermissionError("Explicit deletion confirmation is required.")

    target = _validate_existing_path(target_path, allowed_roots)

    if target.is_dir():
        # Never recursively delete directories in this initial implementation.
        try:
            target.rmdir()
        except OSError as exc:
            raise OSError(
                "The directory is not empty or cannot be deleted."
            ) from exc

        target_type = "folder"

    elif target.is_file():
        target.unlink()
        target_type = "file"

    else:
        raise ValueError("Only regular files and empty directories can be deleted.")

    return {
        "status": "deleted",
        "type": target_type,
        "path": str(target),
    }
