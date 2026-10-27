
from backend.knowledge_base import indexer


def test_index_file(monkeypatch, tmp_path):
    """
    Verify that a supported file is extracted, chunked, embedded, and indexed.

    Mocking the embedding and storage functions keeps this test fast and
    avoids downloading the real embedding model or modifying Qdrant data.
    """
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text(
        "LappyBrain indexes local documents for semantic search.",
        encoding="utf-8",
    )

    # Replace embedding generation with predictable test vectors.
    monkeypatch.setattr(
        indexer,
        "generate_embeddings",
        lambda chunks: [[0.1] * 384 for _ in chunks],
    )

    stored = {}

    # Capture the data sent to Qdrant so we can verify the indexing result.
    def fake_upsert_chunks(chunks, embeddings, metadatas=None, ids=None):
        stored["chunks"] = chunks
        stored["embeddings"] = embeddings
        stored["metadatas"] = metadatas
        stored["ids"] = ids
        return ids

    monkeypatch.setattr(indexer, "upsert_chunks", fake_upsert_chunks)

    result = indexer.index_file(sample_file, tmp_path)

    assert result["status"] == "indexed"
    assert result["chunks_indexed"] >= 1
    assert len(stored["chunks"]) == len(stored["embeddings"])
    assert stored["metadatas"][0]["file_name"] == "sample.txt"
    assert stored["ids"] == result["point_ids"]


def test_index_file_rejects_unsupported_extension(tmp_path):
    """Verify that unsupported file types are rejected before indexing."""
    sample_file = tmp_path / "sample.bin"
    sample_file.write_bytes(b"\x00\x01")

    try:
        indexer.index_file(sample_file, tmp_path)
    except ValueError as exc:
        assert "Unsupported file type" in str(exc)
    else:
        raise AssertionError("Expected an unsupported file type error.")


def test_index_file_rejects_outside_path(tmp_path):
    """Verify that files outside the permitted directory cannot be indexed."""
    allowed_folder = tmp_path / "allowed"
    allowed_folder.mkdir()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("This file is outside.", encoding="utf-8")

    try:
        indexer.index_file(outside_file, allowed_folder)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected an outside file to be rejected.")


def test_index_file_skips_empty_document(monkeypatch, tmp_path):
    """Verify that empty extracted text is skipped without creating vectors."""
    sample_file = tmp_path / "empty.txt"
    sample_file.write_text(" ", encoding="utf-8")

    monkeypatch.setattr(
        indexer,
        "extract_text_from_file",
        lambda path: "",
    )

    result = indexer.index_file(sample_file, tmp_path)

    assert result["status"] == "skipped"
    assert result["chunks_indexed"] == 0
    assert result["point_ids"] == []
