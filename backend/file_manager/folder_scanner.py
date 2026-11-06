
import os
from collections import deque
from pathlib import Path
from typing import Any


# Directories to skip during normal search.
# They remain fully searchable during deep search.
DEEP_SEARCH_DIRECTORIES = {
    "$recycle.bin",
    "system volume information",
    "$windows.~bt",
    "$windows.~ws",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "site-packages",
    ".cache",
    "cache",
    "caches",
    "temp",
    "tmp",
}


def _is_link_or_junction(path: Path) -> bool:
    """Identify symbolic links and Windows junctions."""

    try:
        if path.is_symlink():
            return True

        is_junction = getattr(path, "is_junction", None)

        if callable(is_junction) and is_junction():
            return True

    except OSError:
        return True

    return False


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

    if _is_link_or_junction(requested) or _is_link_or_junction(root_path):
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
            if not _is_link_or_junction(current / name)
        )

        for filename in sorted(filenames):
            file_path = current / filename

            if _is_link_or_junction(file_path):
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


def _search_pass(
    query: str,
    search_roots: list[str | Path],
    max_results: int,
    search_files: bool,
    search_folders: bool,
    strategy: str,
    deep_search: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Perform one filesystem search pass.

    Returns exact matches and partial matches separately.
    """

    exact_results: list[dict[str, Any]] = []
    partial_results: list[dict[str, Any]] = []

    seen_paths: set[str] = set()

    for root_path in search_roots:

        root = Path(root_path).expanduser()

        if _is_link_or_junction(root):
            continue

        try:
            root = root.resolve(strict=True)

            if not root.is_dir():
                continue

        except (OSError, RuntimeError):
            continue

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
                continue

            child_directories: list[Path] = []

            for entry in entries:

                entry_path = Path(entry.path)

                try:
                    if entry.is_symlink():
                        continue

                    is_junction = getattr(
                        entry,
                        "is_junction",
                        None,
                    )

                    if callable(is_junction) and is_junction():
                        continue

                    if entry.is_dir(follow_symlinks=False):

                        # Normal search skips deep-search directories.
                        # Deep search includes them.
                        if (
                            not deep_search
                            and entry.name.casefold()
                            in DEEP_SEARCH_DIRECTORIES
                        ):
                            continue

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

                    entry_name = entry.name.casefold()

                    if query not in entry_name:
                        continue

                    resolved = entry_path.resolve(strict=True)

                    if not resolved.is_relative_to(root):
                        continue

                    normalized_path = os.path.normcase(str(resolved))

                    if normalized_path in seen_paths:
                        continue

                    seen_paths.add(normalized_path)

                    is_exact = entry_name == query

                    result = {
                        "name": resolved.name,
                        "path": str(resolved),
                        "type": entry_type,
                        "match_type": (
                            "exact" if is_exact else "partial"
                        ),
                        "extension": (
                            resolved.suffix.lower()
                            if entry_type == "file"
                            else None
                        ),
                    }

                    if is_exact:
                        if len(exact_results) < max_results:
                            exact_results.append(result)

                    else:
                        if len(partial_results) < max_results:
                            partial_results.append(result)

                except (OSError, RuntimeError):
                    continue

            if strategy == "bfs":
                pending.extend(child_directories)
            else:
                pending.extend(reversed(child_directories))

            # Once enough exact matches are collected,
            # further traversal cannot improve this pass.
            if len(exact_results) >= max_results:
                break

        if len(exact_results) >= max_results:
            break

    exact_results.sort(
        key=lambda item: (
            item["name"].casefold(),
            item["path"].casefold(),
        )
    )

    partial_results.sort(
        key=lambda item: (
            item["name"].casefold(),
            item["path"].casefold(),
        )
    )

    return exact_results, partial_results


def search_filesystem(
    query: str,
    search_roots: list[str | Path],
    max_results: int = 50,
    search_files: bool = True,
    search_folders: bool = True,
    strategy: str = "bfs",
) -> list[dict[str, Any]]:
    """
    Search files and folders using priority-based searching.

    Pass 1: Normal search.
        Searches ordinary directories first.
        If exact matches are found, returns them immediately.

    Pass 2: Deep search.
        Runs only if normal search finds no exact matches.
        Includes system, dependency, cache and hidden application
        directories that were skipped during normal search.

    Exact matches are prioritized over partial matches.

    BFS and DFS traversal are supported.
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

    # PASS 1: Normal search.
    normal_exact, normal_partial = _search_pass(
        query=query,
        search_roots=search_roots,
        max_results=max_results,
        search_files=search_files,
        search_folders=search_folders,
        strategy=strategy,
        deep_search=False,
    )

    # Exact matches in normal search are sufficient.
    # Do not search the remaining deep directories.
    if normal_exact:
        return normal_exact[:max_results]

    # PASS 2: Deep search, only when normal search
    # could not find an exact match.
    deep_exact, deep_partial = _search_pass(
        query=query,
        search_roots=search_roots,
        max_results=max_results,
        search_files=search_files,
        search_folders=search_folders,
        strategy=strategy,
        deep_search=True,
    )

    # If deep search finds exact matches, prioritize them.
    if deep_exact:
        return deep_exact[:max_results]

    # No exact matches anywhere.
    # Return the partial matches collected from both passes.
    combined_partial = normal_partial + deep_partial

    combined_partial.sort(
        key=lambda item: (
            item["name"].casefold(),
            item["path"].casefold(),
        )
    )

    return combined_partial[:max_results]
