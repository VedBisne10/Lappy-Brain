
from typing import Any, Dict, List, Optional

from backend.knowledge_base.retriever import format_retrieved_context, retrieve_relevant_chunks


def search_knowledge_base(
    query: str,
    limit: int = 5,
    score_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Search LappyBrain's indexed documents using a natural-language query.

    The function delegates retrieval to the existing retriever and returns
    both the matching chunks and a formatted context for the language model.
    """
    # Validate the query before starting embedding generation or database search.
    if not isinstance(query, str):
        raise TypeError("query must be a string.")

    if not query.strip():
        raise ValueError("query cannot be empty.")

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    if score_threshold is not None and not -1.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between -1 and 1.")

    # Retrieve relevant chunks using the existing retrieval pipeline.
    results = retrieve_relevant_chunks(
        query=query.strip(),
        limit=limit,
        score_threshold=score_threshold,
    )

    # Format the retrieved passages so they can be passed to the LLM.
    context = format_retrieved_context(results)

    return {
        "query": query.strip(),
        "result_count": len(results),
        "results": results,
        "context": context,
    }


def search_texts(
    query: str,
    limit: int = 5,
    score_threshold: Optional[float] = None,
) -> List[str]:
    """
    Return only the text passages matching a user's query.

    This simplified interface is useful when a caller needs the retrieved
    text but does not need metadata, similarity scores, or formatted context.
    """
    response = search_knowledge_base(
        query=query,
        limit=limit,
        score_threshold=score_threshold,
    )

    # Extract non-empty passages while preserving their relevance order.
    return [
        result["text"]
        for result in response["results"]
        if result.get("text", "").strip()
    ]
