from pathlib import Path
from typing import Any

from backend.file_manager.folder_scanner import scan_folder
from backend.file_manager.metadata_extractor import extract_metadata


def create_file_snapshot(
    folder_path: str | Path,
    allowed_root: str | Path,
    max_files: int = 1000,
) -> dict[str, dict[str, Any]]:
    """
    Capture file metadata for a directory.

    The returned snapshot is keyed by absolute file path.
    File contents are not read.
    """
    files = scan_folder(
        folder_path=folder_path,
        allowed_root=allowed_root,
        max_files=max_files,
    )

    snapshot: dict[str, dict[str, Any]] = {}

    for file_path in files:
        try:
            metadata = extract_metadata(file_path)
            snapshot[metadata["path"]] = {
                "size_bytes": metadata["size_bytes"],
                "modified_at": metadata["modified_at"],
            }
        except (OSError, ValueError, PermissionError):
            # Skip files that become unavailable during scanning.
            continue

    return snapshot


def compare_snapshots(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """Identify added, modified, and deleted files."""

    previous_paths = set(previous)
    current_paths = set(current)

    added = sorted(current_paths - previous_paths)
    deleted = sorted(previous_paths - current_paths)

    modified = sorted(
        path
        for path in previous_paths & current_paths
        if (
            previous[path].get("size_bytes")
            != current[path].get("size_bytes")
            or previous[path].get("modified_at")
            != current[path].get("modified_at")
        )
    )

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
    }
