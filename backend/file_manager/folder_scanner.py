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

# Project indicators used for automatic project discovery.
PROJECT_MARKERS = {
    ".git",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "pom.xml",
    "cargo.toml",
    "go.mod",
    "composer.json",
    "build.gradle",
    "build.gradle.kts",
    "setup.py",
    "manage.py",
    "README.md",
    ".gitignore",
}

# Common personal folders.
PERSONAL_DIRECTORY_NAMES = (
    "Desktop",
    "Documents",
    "Downloads",
    "Pictures",
    "Videos",
    "Music",
    "OneDrive",
)

# Common development workspace names.
DEVELOPMENT_DIRECTORY_NAMES = (
    "Projects",
    "Development",
    "Workspace",
    "Workspaces",
    "Code",
    "Repositories",
    "GitHub",
)

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


# Avoid scanning too deeply just to discover project markers.
PROJECT_DISCOVERY_MAX_DEPTH = 4


def _is_authorized_path(path: Path, allowed_roots: list[str | Path]) -> bool:
    """Check whether a path is inside one of the authorized drive roots."""

    try:
        resolved_path = path.resolve(strict=True)

        for allowed_root in allowed_roots:
            try:
                resolved_root = Path(allowed_root).resolve(strict=True)

                if resolved_path.is_relative_to(resolved_root):
                    return True

            except (OSError, RuntimeError):
                continue

    except (OSError, RuntimeError):
        return False

    return False


def _discover_personal_roots(
    search_roots: list[str | Path],
) -> list[Path]:
    """Discover common personal directories without exceeding allowed roots."""

    home = Path.home()

    candidates = [
        home / name for name in PERSONAL_DIRECTORY_NAMES
    ]

    # OneDrive may use a different location or environment variable.
    for variable in (
        "OneDrive",
        "OneDriveCommercial",
        "OneDriveConsumer",
    ):
        value = os.environ.get(variable)

        if value:
            candidates.append(Path(value).expanduser())

    discovered = []
    seen = set()

    for candidate in candidates:
        if _is_link_or_junction(candidate):
            continue

        if not _is_authorized_path(candidate, search_roots):
            continue

        try:
            resolved = candidate.resolve(strict=True)

            if not resolved.is_dir():
                continue

            key = os.path.normcase(str(resolved))

            if key not in seen:
                seen.add(key)
                discovered.append(resolved)

        except (OSError, RuntimeError):
            continue

    return discovered


def _discover_development_roots(
    search_roots: list[str | Path],
) -> list[Path]:
    """Discover common development workspace directories."""

    candidates = [
        Path.home() / name
        for name in DEVELOPMENT_DIRECTORY_NAMES
    ]

    discovered = []
    seen = set()

    for candidate in candidates:
        if _is_link_or_junction(candidate):
            continue

        if not _is_authorized_path(candidate, search_roots):
            continue

        try:
            resolved = candidate.resolve(strict=True)

            if not resolved.is_dir():
                continue

            key = os.path.normcase(str(resolved))

            if key not in seen:
                seen.add(key)
                discovered.append(resolved)

        except (OSError, RuntimeError):
            continue

    return discovered


def _contains_project_marker(directory: Path) -> bool:
    """Determine whether a directory looks like a development project."""

    try:
        for marker in PROJECT_MARKERS:
            marker_path = directory / marker

            if marker_path.exists():
                return True

    except OSError:
        return False

    return False


def _discover_project_roots(
    discovery_roots: list[Path],
) -> list[Path]:
    """
    Discover project directories using common project markers.

    Discovery is depth-limited and skips generated/system directories.
    """

    projects = []
    seen = set()

    for scan_root in discovery_roots:
        if _is_link_or_junction(scan_root):
            continue

        try:
            if not scan_root.is_dir():
                continue

            for current_path, directories, _ in os.walk(
                scan_root,
                followlinks=False,
                onerror=lambda error: None,
            ):
                current = Path(current_path)

                try:
                    depth = len(current.relative_to(scan_root).parts)
                except ValueError:
                    directories[:] = []
                    continue

                # Never descend through links, junctions or generated folders.
                directories[:] =  sorted(
                    (
                        name
                        for name in directories
                        if (
                            not _is_link_or_junction(current / name)
                            and name.casefold() not in DEEP_SEARCH_DIRECTORIES
                        )
                    ),
                    key=str.casefold,
                )


                if _contains_project_marker(current):
                    try:
                        resolved = current.resolve(strict=True)
                        key = os.path.normcase(str(resolved))

                        if key not in seen:
                            seen.add(key)
                            projects.append(resolved)

                    except (OSError, RuntimeError):
                        pass

                    # Avoid treating nested folders inside this project
                    # as separate projects during this discovery pass.
                    directories[:] = []
                    continue

                if depth >= PROJECT_DISCOVERY_MAX_DEPTH:
                    directories[:] = []

        except (OSError, RuntimeError):
            continue

    return sorted(projects, key=lambda path: str(path).casefold())


def _annotate_results(
    results: list[dict[str, Any]],
    classification: str,
    priority: int,
) -> list[dict[str, Any]]:
    """Add folder classification information to search results."""

    for result in results:
        result["classification"] = classification
        result["priority"] = priority

    return results


def _deduplicate_results(
    results: list[dict[str, Any]],
    max_results: int,
) -> list[dict[str, Any]]:
    """Remove duplicate paths while preserving result priority."""

    unique = []
    seen = set()

    for result in results:
        key = os.path.normcase(result["path"])

        if key in seen:
            continue

        seen.add(key)
        unique.append(result)

        if len(unique) >= max_results:
            break

    return unique


def search_filesystem(
    query: str,
    search_roots: list[str | Path],
    max_results: int = 50,
    search_files: bool = True,
    search_folders: bool = True,
    strategy: str = "bfs",
) -> list[dict[str, Any]]:
    """
    Search using automatic folder discovery and classification.

    Priority 1: Detected development projects.
    Priority 2: Common personal folders.
    Priority 3: Other accessible drive locations.
    Priority 4: Deep search through system/generated directories.

    Exact matches are preferred over partial matches.
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

    # Remove inaccessible and duplicate search roots.
    authorized_roots = []
    seen_roots = set()

    for root in search_roots:
        path = Path(root).expanduser()

        if _is_link_or_junction(path):
            continue

        try:
            resolved = path.resolve(strict=True)

            if not resolved.is_dir():
                continue

            key = os.path.normcase(str(resolved))

            if key not in seen_roots:
                seen_roots.add(key)
                authorized_roots.append(resolved)

        except (OSError, RuntimeError):
            continue

    if not authorized_roots:
        return []

    # Discover personal and development locations.
    personal_roots = _discover_personal_roots(authorized_roots)

    development_roots = _discover_development_roots(
        authorized_roots
    )

    # Search both personal folders and known development workspaces
    # when discovering project markers.
    discovery_roots = list(
        dict.fromkeys(personal_roots + development_roots)
    )

    project_roots = _discover_project_roots(discovery_roots)
    
    # PRIORITY 1: DEVELOPMENT PROJECTS
    if project_roots:
        exact, partial = _search_pass(
            query=query,
            search_roots=project_roots,
            max_results=max_results,
            search_files=search_files,
            search_folders=search_folders,
            strategy=strategy,
            deep_search=True,
        )

        if exact:
            return _annotate_results(
                exact,
                classification="project",
                priority=1,
            )[:max_results]

        project_partial = _annotate_results(
            partial,
            classification="project",
            priority=1,
        )
    else:
        project_partial = []
 
    # PRIORITY 2: PERSONAL FOLDERS
    if personal_roots:
        exact, partial = _search_pass(
            query=query,
            search_roots=personal_roots,
            max_results=max_results,
            search_files=search_files,
            search_folders=search_folders,
            strategy=strategy,
            deep_search=True,
        )

        if exact:
            return _annotate_results(
                exact,
                classification="personal",
                priority=2,
            )[:max_results]

        personal_partial = _annotate_results(
            partial,
            classification="personal",
            priority=2,
        )
    else:
        personal_partial = []

    # PRIORITY 3: ALL OTHER ACCESSIBLE DRIVE LOCATIONS
    exact, partial = _search_pass(
        query=query,
        search_roots=authorized_roots,
        max_results=max_results,
        search_files=search_files,
        search_folders=search_folders,
        strategy=strategy,
        deep_search=False,
    )

    if exact:
        return _annotate_results(
            exact,
            classification="ordinary",
            priority=3,
        )[:max_results]

    ordinary_partial = _annotate_results(
        partial,
        classification="ordinary",
        priority=3,
    )

    # PRIORITY 4: DEEP SEARCH
    # Only used when no exact match was found above.
    deep_exact, deep_partial = _search_pass(
        query=query,
        search_roots=authorized_roots,
        max_results=max_results,
        search_files=search_files,
        search_folders=search_folders,
        strategy=strategy,
        deep_search=True,
    )

    if deep_exact:
        return _annotate_results(
            deep_exact,
            classification="system_or_generated",
            priority=4,
        )[:max_results]

    deep_partial = _annotate_results(
        deep_partial,
        classification="system_or_generated",
        priority=4,
    )

    # No exact matches found anywhere.
    # Return partial matches in classification priority order.
    combined_partial = (
        project_partial
        + personal_partial
        + ordinary_partial
        + deep_partial
    )

    return _deduplicate_results(
        combined_partial,
        max_results,
    )

