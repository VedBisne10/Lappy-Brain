from typing import Any, Dict, List, Optional

from backend.knowledge_base.embeddings import generate_embedding
from backend.knowledge_base.vector_store import search_similar


def retrieve_relevant_chunks(
    query: str,
    limit: int = 5,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Find document chunks that are semantically relevant to a user's question.

    The function converts the question into an embedding, searches Qdrant,
    and returns matching text with its source metadata and similarity score.

    Args:
        query: The user's question or search text.
        limit: Maximum number of relevant chunks to return.
        score_threshold: Optional minimum similarity score for returned results.

    Returns:
        A list of matching chunks, ordered by relevance.
    """
    # Reject invalid queries before calling the embedding model.
    if not isinstance(query, str):
        raise TypeError("query must be a string.")

    if not query.strip():
        raise ValueError("query cannot be empty.")

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    if score_threshold is not None and not -1.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between -1 and 1.")

    # Generate the query vector using the same model used for document chunks.
    query_embedding = generate_embedding(query.strip())

    # Search the existing Qdrant collection rather than accessing it directly.
    results = search_similar(
        query_embedding=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
    )

    # Return the database results in the format expected by later modules.
    return results


def format_retrieved_context(
    results: List[Dict[str, Any]],
) -> str:
    """
    Combine retrieved chunks into readable context for the language model.

    Each chunk includes its source path when available, allowing LappyBrain
    to use the retrieved information and identify where it came from.
    """
    if not results:
        return "No relevant information was found in the indexed documents."

    context_parts = []

    # Format each result separately so the source of every passage is clear.
    for index, result in enumerate(results, start=1):
        text = result.get("text", "").strip()
        metadata = result.get("metadata") or {}
        source = metadata.get("source", "Unknown source")
        score = result.get("score")

        # Skip results that do not contain usable text.
        if not text:
            continue

        section = [
            f"Source {index}: {source}",
            f"Content: {text}",
        ]

        # Include the score when the vector store supplies one.
        if score is not None:
            section.append(f"Similarity score: {score:.4f}")

        context_parts.append("\n".join(section))

    if not context_parts:
        return "No relevant information was found in the indexed documents."

    return "\n\n".join(context_parts)
