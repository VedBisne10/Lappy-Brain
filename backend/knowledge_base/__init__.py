
"""
Knowledge-base functionality for LappyBrain.

This package provides a common interface for document indexing,
embedding generation, vector storage, retrieval, and semantic search.
"""

from backend.knowledge_base.embeddings import (
    generate_embedding,
    generate_embeddings,
)
from backend.knowledge_base.indexer import index_file
from backend.knowledge_base.retriever import (
    format_retrieved_context,
    retrieve_relevant_chunks,
)
from backend.knowledge_base.search import (
    search_knowledge_base,
    search_texts,
)
from backend.knowledge_base.vector_store import (
    close_qdrant_client,
    delete_points,
    initialize_collection,
    search_similar,
    upsert_chunks,
)


__all__ = [
    "generate_embedding",
    "generate_embeddings",
    "index_file",
    "format_retrieved_context",
    "retrieve_relevant_chunks",
    "search_knowledge_base",
    "search_texts",
    "close_qdrant_client",
    "delete_points",
    "initialize_collection",
    "search_similar",
    "upsert_chunks",
]
