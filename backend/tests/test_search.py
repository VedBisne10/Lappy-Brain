
import pytest

from backend.knowledge_base import search


def test_search_knowledge_base(monkeypatch):
    """Verify that search returns matching chunks and formatted context."""
    fake_results = [
        {
            "id": "test-id",
            "text": "Python is a programming language.",
            "metadata": {"source": "python.txt"},
            "score": 0.91,
        }
    ]

    # Mock retrieval and formatting to test the search interface independently.
    monkeypatch.setattr(
        search,
        "retrieve_relevant_chunks",
        lambda query, limit, score_threshold: fake_results,
    )

    monkeypatch.setattr(
        search,
        "format_retrieved_context",
        lambda results: "Source: python.txt\nPython is a programming language.",
    )

    response = search.search_knowledge_base("What is Python?")

    assert response["query"] == "What is Python?"
    assert response["result_count"] == 1
    assert response["results"] == fake_results
    assert "Python is a programming language." in response["context"]


def test_search_texts(monkeypatch):
    """Verify that the simplified search returns only non-empty text."""
    monkeypatch.setattr(
        search,
        "search_knowledge_base",
        lambda query, limit, score_threshold: {
            "query": query,
            "result_count": 2,
            "results": [
                {"text": "Relevant document text."},
                {"text": "   "},
            ],
            "context": "",
        },
    )

    results = search.search_texts("Find a document")

    assert results == ["Relevant document text."]


def test_search_rejects_empty_query():
    """Verify that an empty query is rejected."""
    with pytest.raises(ValueError, match="query cannot be empty"):
        search.search_knowledge_base("   ")


def test_search_rejects_invalid_limit():
    """Verify that a non-positive result limit is rejected."""
    with pytest.raises(ValueError, match="limit must be greater than zero"):
        search.search_knowledge_base("Find something", limit=0)
