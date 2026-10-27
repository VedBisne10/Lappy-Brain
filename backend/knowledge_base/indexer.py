
import hashlib
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from backend.document_processing.chunker import chunking
from backend.document_processing.code_processor import extract_text_from_code
from backend.document_processing.docx_processor import extract_text_from_docx
from backend.document_processing.excel_processor import extract_text_from_excel
from backend.document_processing.pdf_processor import extract_text_from_pdf
from backend.document_processing.text_processor import extract_text_from_file

from backend.knowledge_base.embeddings import generate_embeddings
from backend.knowledge_base.vector_store import upsert_chunks


# Map supported file extensions to their existing text extraction functions.
PROCESSORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".xlsx": extract_text_from_excel,
    ".xlsm": extract_text_from_excel,
    ".py": extract_text_from_code,
    ".java": extract_text_from_code,
    ".js": extract_text_from_code,
    ".jsx": extract_text_from_code,
    ".ts": extract_text_from_code,
    ".tsx": extract_text_from_code,
    ".c": extract_text_from_code,
    ".cpp": extract_text_from_code,
    ".html": extract_text_from_file,
    ".css": extract_text_from_file,
    ".sql": extract_text_from_file,
    ".json": extract_text_from_file,
    ".yaml": extract_text_from_file,
    ".yml": extract_text_from_file,
    ".xml": extract_text_from_file,
    ".md": extract_text_from_file,
    ".txt": extract_text_from_file,
    ".csv": extract_text_from_file,
    ".log": extract_text_from_file,
}

# These settings control the initial division of extracted text into chunks.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def _split_document_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Divide extracted document text into chunks before overlap cleanup.

    The function prefers paragraph and sentence boundaries when possible.
    The existing chunking() function is then used to remove duplicated
    boundary words from the resulting chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be non-negative and smaller than chunk_size."
        )

    if not text or not text.strip():
        return []

    text = text.strip()
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Prefer a nearby paragraph or sentence boundary instead of cutting
        # the document at an arbitrary position.
        if end < len(text):
            search_start = start + int(chunk_size * 0.7)

            boundaries = [
                text.rfind("\n\n", search_start, end),
                text.rfind(". ", search_start, end),
                text.rfind("? ", search_start, end),
                text.rfind("! ", search_start, end),
                text.rfind("\n", search_start, end),
            ]

            boundary = max(boundaries)

            if boundary != -1:
                end = boundary + 1

        chunk = text[start:end].strip()

        # Keep only non-empty chunks.
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Retain some context while ensuring the next iteration advances.
        start = max(end - chunk_overlap, start + 1)

    return chunks


def _get_processor(file_path: Path):
    """
    Return the existing text extractor for a supported file extension.

    Unsupported files are rejected rather than passed to an incompatible
    document processor.
    """
    processor = PROCESSORS.get(file_path.suffix.lower())

    if processor is None:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix or '(no extension)'}"
        )

    return processor


def index_file(
    file_path: str | Path,
    allowed_root: str | Path,
) -> dict[str, Any]:
    """
    Extract, prepare, embed, and store one document in Qdrant.

    The file must be inside the allowed directory. Deterministic chunk IDs
    allow matching chunks to be updated when the same file is indexed again.
    """
    path = Path(file_path)
    root = Path(allowed_root).resolve()

    # Refuse symbolic links so indexing cannot unintentionally follow them.
    if path.is_symlink():
        raise ValueError("Symbolic links cannot be indexed.")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    resolved_path = path.resolve()

    # Ensure the resolved file path stays inside the permitted directory.
    try:
        resolved_path.relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            "The file is outside the allowed directory."
        ) from exc

    processor = _get_processor(resolved_path)

    # Extract text through the processor already implemented for this format.
    extracted_text = processor(resolved_path)

    if not isinstance(extracted_text, str):
        raise TypeError("The document processor must return a string.")

    if not extracted_text.strip():
        return {
            "file_path": str(resolved_path),
            "status": "skipped",
            "reason": "No extractable text was found.",
            "chunks_indexed": 0,
            "point_ids": [],
        }

    # Split the document, then use the existing module for duplicate cleanup.
    chunks = _split_document_text(extracted_text)
    chunks = chunking(chunks)

    if not chunks:
        return {
            "file_path": str(resolved_path),
            "status": "skipped",
            "reason": "No usable chunks were produced.",
            "chunks_indexed": 0,
            "point_ids": [],
        }

    # Generate all embeddings in a batch to reduce model-call overhead.
    embeddings = generate_embeddings(chunks)

    # Create repeatable UUIDs based on the file path and chunk position.
    normalized_path = str(resolved_path).casefold()
    path_hash = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()

    point_ids = [
        str(uuid5(NAMESPACE_URL, f"{path_hash}:{index}"))
        for index in range(len(chunks))
    ]

    # Save source details with every chunk so retrieval can identify its origin.
    metadatas = [
        {
            "source": str(resolved_path),
            "file_name": resolved_path.name,
            "file_extension": resolved_path.suffix.lower(),
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]

    upsert_chunks(
        chunks=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=point_ids,
    )

    return {
        "file_path": str(resolved_path),
        "status": "indexed",
        "chunks_indexed": len(chunks),
        "point_ids": point_ids,
    }
