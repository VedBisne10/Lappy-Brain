
import os
from collections import deque
from pathlib import Path
from typing import Any


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
        onerror=lambda error: None,
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


def search_filesystem(
    query: str,
    search_roots: list[str | Path],
    max_results: int = 50,
    search_files: bool = True,
    search_folders: bool = True,
    strategy: str = "bfs",
) -> list[dict[str, Any]]:
    """
    Search files and folders using BFS or DFS traversal.

    BFS searches directories level by level.
    DFS explores one directory branch before returning.

    Matching is case-insensitive and supports exact and partial names.
    File contents are never opened or read.
    """

    query = query.strip().casefold()
    strategy = strategy.strip().lower()

    if not query:
        raise ValueError("Search query cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    if not search_files and not search_folders:
        raise ValueError("Enable file search, folder search, or both.")

    if strategy not in {"bfs", "dfs"}:
        raise ValueError("Strategy must be either 'bfs' or 'dfs'.")

    results: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    # Search each authorized root independently.
    for root_path in search_roots:
        root = Path(root_path).expanduser()

        if root.is_symlink():
            continue

        try:
            root = root.resolve(strict=True)

            if not root.is_dir():
                continue

        except (OSError, RuntimeError):
            continue

        # BFS uses a queue; DFS uses a stack.
        pending = deque([root])

        while pending:
            if strategy == "bfs":
                current = pending.popleft()
            else:
                current = pending.pop()

            try:
                with os.scandir(current) as iterator:
                    entries = sorted(
                        iterator,
                        key=lambda entry: entry.name.casefold(),
                    )
            except OSError:
                # Skip directories that cannot be accessed.
                continue

            child_directories: list[Path] = []

            for entry in entries:
                entry_path = Path(entry.path)

                try:
                    # Never follow symbolic links.
                    if entry.is_symlink():
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        child_directories.append(entry_path)

                        if not search_folders:
                            continue

                        entry_type = "folder"

                    elif entry.is_file(follow_symlinks=False):
                        if not search_files:
                            continue

                        entry_type = "file"

                    else:
                        continue

                    # Filter names before collecting metadata.
                    if query not in entry.name.casefold():
                        continue

                    resolved = entry_path.resolve(strict=True)

                    # Ensure the resolved entry remains inside its root.
                    if not resolved.is_relative_to(root):
                        continue

                    normalized_path = os.path.normcase(str(resolved))

                    if normalized_path in seen_paths:
                        continue

                    seen_paths.add(normalized_path)

                    results.append({
                        "name": resolved.name,
                        "path": str(resolved),
                        "type": entry_type,
                        "match_type": (
                            "exact"
                            if resolved.name.casefold() == query
                            else "partial"
                        ),
                        "extension": (
                            resolved.suffix.lower()
                            if entry_type == "file"
                            else None
                        ),
                    })

                    # Stop when the requested result limit is reached.
                    if len(results) >= max_results:
                        return results

                except (OSError, RuntimeError):
                    # Skip entries that disappear or become inaccessible.
                    continue

            # Schedule discovered directories according to the strategy.
            if strategy == "bfs":
                pending.extend(child_directories)
            else:
                # Reverse insertion preserves alphabetical DFS traversal.
                pending.extend(reversed(child_directories))

    # Place exact matches before partial matches in the final results.
    results.sort(
        key=lambda item: (
            item["match_type"] != "exact",
            item["name"].casefold(),
            item["path"].casefold(),
        )
    )

    return results
