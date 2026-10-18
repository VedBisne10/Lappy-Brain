
class LappyBrainError(Exception):
    """Base exception for LappyBrain application errors."""


class ResourceNotFoundError(LappyBrainError):
    """Raised when a requested resource cannot be found."""


class AccessDeniedError(LappyBrainError):
    """Raised when access to a resource is not permitted."""


class DocumentProcessingError(LappyBrainError):
    """Raised when a document cannot be processed."""


class LLMConnectionError(LappyBrainError):
    """Raised when the local language model is unavailable."""
