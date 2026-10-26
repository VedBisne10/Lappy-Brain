
"""
Document-processing utilities for LappyBrain.

This package provides a common interface for extracting text from supported
documents and splitting extracted text into chunks for retrieval.
"""

from backend.document_processing.chunker import chunking
from backend.document_processing.code_processor import extract_text_from_code
from backend.document_processing.docx_processor import extract_text_from_docx
from backend.document_processing.excel_processor import extract_text_from_excel
from backend.document_processing.pdf_processor import extract_text_from_pdf
from backend.document_processing.text_processor import extract_text_from_file


__all__ = [
    "chunk_text",
    "remove_duplicate_overlap",
    "extract_text_from_code",
    "extract_text_from_docx",
    "extract_text_from_excel",
    "extract_text_from_pdf",
    "extract_text_from_file",
]
