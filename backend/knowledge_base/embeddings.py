from typing import List

from sentence_transformers import SentenceTransformer

# Keep one model instance so it is not loaded again for every request.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once and reuse it across requests.

    Lazy loading avoids downloading or loading the model until an embedding
    is actually needed.
    """
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(MODEL_NAME)

    return _embedding_model


def generate_embedding(text: str) -> List[float]:
    """
    Convert a single text string into a numerical embedding vector.

    Empty input is rejected because it does not provide useful content
    for semantic search.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    if not text.strip():
        raise ValueError("text cannot be empty.")

    model = get_embedding_model()

    # Convert the model output to a regular Python list for database storage.
    embedding = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return embedding.tolist()


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Convert multiple texts into vectors in one batch.

    Batch processing is generally faster than calling the single-text
    function repeatedly when indexing many document chunks.
    """
    if not isinstance(texts, list):
        raise TypeError("texts must be a list of strings.")

    if not texts:
        return []

    # Validate the entire batch before running the model.
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Every item must be a non-empty string.")

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()
