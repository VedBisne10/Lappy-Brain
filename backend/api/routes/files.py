from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.config.settings import settings
from backend.file_manager.file_operations import (
    create_folder,
    create_file,
    rename_path,
    move_path,
    list_directory,
    delete_path,
)
from backend.file_manager.folder_scanner import search_filesystem


router = APIRouter(
    prefix="/api/files",
    tags=["File Management"],
)


class FileSearchRequest(BaseModel):
    """Validate file and folder search requests."""

    query: str = Field(min_length=1, max_length=255)
    max_results: int = Field(default=50, ge=1, le=500)
    search_files: bool = True
    search_folders: bool = True
    strategy: Literal["bfs", "dfs"] = "bfs"

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Remove surrounding whitespace and reject blank queries."""

        value = value.strip()

        if not value:
            raise ValueError("Search query cannot be empty.")

        return value


class CreateFolderRequest(BaseModel):
    """Validate folder creation requests."""

    folder_path: str = Field(min_length=1, max_length=1000)


class CreateFileRequest(BaseModel):
    """Validate file creation requests."""

    file_path: str = Field(min_length=1, max_length=1000)
    content: str = Field(default="", max_length=5 * 1024 * 1024)


class RenamePathRequest(BaseModel):
    """Validate file or folder rename requests."""

    source_path: str = Field(min_length=1, max_length=1000)
    new_name: str = Field(min_length=1, max_length=255)


class MovePathRequest(BaseModel):
    """Validate file or folder move requests."""

    source_path: str = Field(min_length=1, max_length=1000)
    destination_path: str = Field(min_length=1, max_length=1000)


class ListDirectoryRequest(BaseModel):
    """Validate directory listing requests."""

    directory_path: str = Field(min_length=1, max_length=1000)


class DeletePathRequest(BaseModel):
    """Validate deletion requests."""

    target_path: str = Field(min_length=1, max_length=1000)
    confirm: bool = False


class OperationResponse(BaseModel):
    """Represent a successful filesystem operation."""

    status: str
    path: str | None = None
    type: str | None = None
    old_path: str | None = None
    new_path: str | None = None
    size_bytes: int | None = None
    entry_count: int | None = None
    entries: list[dict[str, Any]] | None = None


class FileSearchResponse(BaseModel):
    """Represent file-search results."""

    query: str
    strategy: str
    result_count: int
    results: list[dict[str, Any]]


def execute_file_operation(operation, *args, **kwargs):
    """Execute a filesystem operation and translate errors into HTTP responses."""

    try:
        return operation(*args, **kwargs)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except (ValueError, TypeError, NotADirectoryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/search",
    response_model=FileSearchResponse,
)
def search_files(request: FileSearchRequest) -> FileSearchResponse:
    """Search authorized drives for files and folders."""

    if not request.search_files and not request.search_folders:
        raise HTTPException(
            status_code=422,
            detail="Enable file search, folder search, or both.",
        )

    results = execute_file_operation(
        search_filesystem,
        query=request.query,
        search_roots=settings.file_search_roots,
        max_results=request.max_results,
        search_files=request.search_files,
        search_folders=request.search_folders,
        strategy=request.strategy,
    )

    return FileSearchResponse(
        query=request.query,
        strategy=request.strategy,
        result_count=len(results),
        results=results,
    )


@router.post(
    "/create-folder",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_folder_endpoint(request: CreateFolderRequest):
    """Create a new folder inside an authorized drive."""

    result = execute_file_operation(
        create_folder,
        folder_path=request.folder_path,
        allowed_roots=settings.file_search_roots,
    )

    return result


@router.post(
    "/create-file",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_file_endpoint(request: CreateFileRequest):
    """Create a new text file without overwriting existing files."""

    result = execute_file_operation(
        create_file,
        file_path=request.file_path,
        allowed_roots=settings.file_search_roots,
        content=request.content,
    )

    return result


@router.post(
    "/rename",
    response_model=OperationResponse,
)
def rename_path_endpoint(request: RenamePathRequest):
    """Rename an existing file or directory."""

    result = execute_file_operation(
        rename_path,
        source_path=request.source_path,
        new_name=request.new_name,
        allowed_roots=settings.file_search_roots,
    )

    return result


@router.post(
    "/move",
    response_model=OperationResponse,
)
def move_path_endpoint(request: MovePathRequest):
    """Move a file or directory to another authorized location."""

    result = execute_file_operation(
        move_path,
        source_path=request.source_path,
        destination_path=request.destination_path,
        allowed_roots=settings.file_search_roots,
    )

    return result


@router.post(
    "/list",
    response_model=OperationResponse,
)
def list_directory_endpoint(request: ListDirectoryRequest):
    """List files and subdirectories inside an authorized directory."""

    result = execute_file_operation(
        list_directory,
        directory_path=request.directory_path,
        allowed_roots=settings.file_search_roots,
    )

    return {
        "status": "success",
        **result,
    }
    

@router.post(
    "/delete",
    response_model=OperationResponse,
)
def delete_path_endpoint(request: DeletePathRequest):
    """Delete a file or empty folder after explicit confirmation."""

    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit deletion confirmation is required.",
        )

    result = execute_file_operation(
        delete_path,
        target_path=request.target_path,
        allowed_roots=settings.file_search_roots,
        confirm=request.confirm,
    )

    return result
