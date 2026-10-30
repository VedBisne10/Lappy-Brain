
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.config.settings import settings
from backend.file_manager.folder_scanner import search_filesystem


router = APIRouter(
    prefix="/api/files",
    tags=["File Management"],
)


class FileSearchRequest(BaseModel):
    """Validate file-search requests received from the client."""

    query: str = Field(
        min_length=1,
        max_length=255,
        description="Filename or folder-name search query.",
    )

    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of matching entries.",
    )

    search_files: bool = True
    search_folders: bool = True

    strategy: Literal["bfs", "dfs"] = Field(
        default="bfs",
        description="Directory traversal strategy.",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Remove surrounding whitespace and reject blank queries."""

        value = value.strip()

        if not value:
            raise ValueError("Search query cannot be empty.")

        return value


class FileSearchResponse(BaseModel):
    """Define the response returned by the file-search endpoint."""

    query: str
    strategy: str
    result_count: int
    results: list[dict[str, Any]]


@router.post(
    "/search",
    response_model=FileSearchResponse,
    status_code=status.HTTP_200_OK,
)
def search_files(request: FileSearchRequest) -> FileSearchResponse:
    """
    Search authorized laptop drives for matching files and folders.

    Search roots come from application settings rather than directly
    from the API request, preventing clients from choosing arbitrary roots.
    """

    if not request.search_files and not request.search_folders:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enable file search, folder search, or both.",
        )

    try:
        # Discover available drives dynamically for every search.
        search_roots = settings.file_search_roots

        results = search_filesystem(
            query=request.query,
            search_roots=search_roots,
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

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Avoid exposing internal filesystem details through the API.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File search failed. Check the backend logs.",
        ) from exc
