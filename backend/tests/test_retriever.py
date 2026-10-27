
import pytest

from backend.knowledge_base import retriever


def test_retrieve_relevant_chunks(monkeypatch):
    """Verify that a query is embedded and its matching chunks are returned."""
    expected_results = [
        {
            "id": "test-id",
            "text": "Python is used for programming.",
            "metadata": {"source": "python.txt"},
            "score": 0.92,
        }
    ]

    # Mock model and database calls so this test does not require Qdrant.
    monkeypatch.setattr(
        retriever,
        "generate_embedding",
        lambda query: [0.1] * 384,
    )

    monkeypatch.setattr(
        retriever,
        "search_similar",
        lambda query_embedding, limit, score_threshold: expected_results,
    )

    results = retriever.retrieve_relevant_chunks("What is Python?")

    assert results == expected_results
    assert results[0]["metadata"]["source"] == "python.txt"


def test_retrieve_rejects_empty_query():
    """Verify that blank queries are rejected before searching."""
    with pytest.raises(ValueError, match="query cannot be empty"):
        retriever.retrieve_relevant_chunks("   ")


def test_retrieve_rejects_invalid_limit():
    """Verify that the result limit must be positive."""
    with pytest.raises(ValueError, match="limit must be greater than zero"):
        retriever.retrieve_relevant_chunks("What is Python?", limit=0)


def test_format_retrieved_context():
    """Verify that retrieved text and source details are formatted correctly."""
    results = [
        {
            "id": "test-id",
            "text": "Python is used for programming.",
            "metadata": {"source": "python.txt"},
            "score": 0.92,
        }
    ]

    context = retriever.format_retrieved_context(results)

    assert "python.txt" in context
    assert "Python is used for programming." in context
    assert "0.9200" in context


def test_format_empty_results():
    """Verify that an empty search result produces a helpful message."""
    context = retriever.format_retrieved_context([])

    assert "No relevant information" in context
