
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.knowledge_base.retriever import (
    format_retrieved_context,
    retrieve_relevant_chunks,
)


# Create the router that FastAPI will register in main.py.
router = APIRouter(
    prefix="/api/knowledge",
    tags=["Knowledge Base"],
)


class KnowledgeSearchRequest(BaseModel):
    """Validate the query and search options received from the client."""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    score_threshold: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
    )


class KnowledgeSearchResponse(BaseModel):
    """Define the response format for knowledge-base searches."""

    query: str
    result_count: int
    results: list[dict]
    context: str


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(request: KnowledgeSearchRequest):
    """
    Search indexed documents and return relevant text and source metadata.

    Existing retriever functions handle embedding generation and Qdrant
    search, keeping database logic outside the API route.
    """
    # Reject queries containing only whitespace.
    if not request.query.strip():
        raise HTTPException(
            status_code=422,
            detail="Search query cannot be empty.",
        )

    try:
        results = retrieve_relevant_chunks(
            query=request.query.strip(),
            limit=request.limit,
            score_threshold=request.score_threshold,
        )

        context = format_retrieved_context(results)

        return KnowledgeSearchResponse(
            query=request.query.strip(),
            result_count=len(results),
            results=results,
            context=context,
        )

    except ValueError as exc:
        # Return invalid search parameters as a client error.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        # Keep internal error details out of the public API response.
        raise HTTPException(
            status_code=500,
            detail="Knowledge search failed. Check the backend logs.",
        ) from exc
