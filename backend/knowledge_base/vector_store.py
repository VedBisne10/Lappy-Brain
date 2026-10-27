from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient, models

from backend.knowledge_base.embeddings import EMBEDDING_DIMENSION

# Store Qdrant's persistent database inside the existing storage directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
QDRANT_PATH = PROJECT_ROOT / "storage" / "qdrant_db"

# Keep one collection for the chunks indexed from your laptop's files.
COLLECTION_NAME = "lappybrain_knowledge"

# Reuse one client so the local database is not opened repeatedly.
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """
    Create the local Qdrant client once and reuse it.

    The database is saved on disk, so indexed vectors remain available
    when LappyBrain is restarted.
    """
    global _qdrant_client

    if _qdrant_client is None:
        # Create the storage directory before opening the persistent database.
        QDRANT_PATH.mkdir(parents=True, exist_ok=True)

        _qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    return _qdrant_client


def initialize_collection() -> str:
    """
    Create the knowledge collection if it does not already exist.

    The collection uses the same vector dimension as the embedding model
    and cosine distance for semantic similarity comparisons.
    """
    client = get_qdrant_client()

    # Reuse the existing collection instead of deleting previously indexed data.
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )

    return COLLECTION_NAME


def upsert_chunks(
    chunks: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    ids: Optional[List[str]] = None,
) -> List[str]:
    """
    Save document chunks, their embeddings, and metadata in Qdrant.

    Each chunk becomes a point in the collection. Existing points with the
    same IDs are updated, allowing callers to re-index known chunks.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("Each chunk must have exactly one embedding.")

    if not chunks:
        return []

    if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
        raise ValueError("Every chunk must be a non-empty string.")

    if any(len(vector) != EMBEDDING_DIMENSION for vector in embeddings):
        raise ValueError(
            f"Every embedding must contain {EMBEDDING_DIMENSION} values."
        )

    if any(
        not all(isinstance(value, (int, float)) for value in vector)
        for vector in embeddings
    ):
        raise ValueError("Embedding vectors must contain numeric values.")

    if metadatas is None:
        metadatas = [{} for _ in chunks]

    if len(metadatas) != len(chunks):
        raise ValueError("Each chunk must have exactly one metadata dictionary.")

    if any(not isinstance(metadata, dict) for metadata in metadatas):
        raise ValueError("Each metadata entry must be a dictionary.")

    # Generate IDs when the caller does not supply stable IDs for re-indexing.
    if ids is None:
        ids = [str(uuid4()) for _ in chunks]

    if len(ids) != len(chunks):
        raise ValueError("Each chunk must have exactly one ID.")

    if any(not isinstance(point_id, str) or not point_id.strip() for point_id in ids):
        raise ValueError("Every point ID must be a non-empty string.")

    if len(set(ids)) != len(ids):
        raise ValueError("Point IDs must be unique within a batch.")

    client = get_qdrant_client()
    initialize_collection()

    points = []

    # Store the original text and its metadata alongside each vector.
    for chunk, embedding, metadata, point_id in zip(
        chunks, embeddings, metadatas, ids
    ):
        payload = {
            **metadata,
            "text": chunk,
        }

        points.append(
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
        )

    # Send the batch together rather than making one database call per chunk.
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return ids


def search_similar(
    query_embedding: List[float],
    limit: int = 5,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Find the most relevant stored chunks for a query embedding.

    Results include each chunk's text, metadata, point ID, and similarity score.
    A score threshold can exclude results that are not similar enough.
    """
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Query embedding must contain {EMBEDDING_DIMENSION} values."
        )

    if not all(
        isinstance(value, (int, float)) for value in query_embedding
    ):
        raise ValueError("Query embedding must contain numeric values.")

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    if score_threshold is not None and not -1.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between -1 and 1.")

    client = get_qdrant_client()
    initialize_collection()

    # Query Qdrant using the same embedding space as the stored document chunks.
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
        with_vectors=False,
    )

    results = []

    # Convert Qdrant records into simple dictionaries for the retriever.
    for point in response.points:
        payload = point.payload or {}

        results.append(
            {
                "id": str(point.id),
                "text": payload.get("text", ""),
                "metadata": {
                    key: value
                    for key, value in payload.items()
                    if key != "text"
                },
                "score": point.score,
            }
        )

    return results


def delete_points(ids: List[str]) -> int:
    """
    Delete selected points from the collection by their IDs.

    This can be used later when a file is removed or its indexed chunks
    need to be replaced.
    """
    if not ids:
        return 0

    if any(not isinstance(point_id, str) or not point_id.strip() for point_id in ids):
        raise ValueError("Every point ID must be a non-empty string.")

    client = get_qdrant_client()
    initialize_collection()

    # Wait for deletion to finish before returning control to the caller.
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.PointIdsList(points=ids),
        wait=True,
    )

    return len(ids)


def close_qdrant_client() -> None:
    """
    Close the local database client when the application is shutting down.

    Resetting the reference allows a fresh client to be created if needed.
    """
    global _qdrant_client

    if _qdrant_client is not None:
        _qdrant_client.close()
        _qdrant_client = None
