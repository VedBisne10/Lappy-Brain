# Base exception — all custom LappyBrain errors inherit from this,
# so you can catch any app error with a single "except LappyBrainError"
class LappyBrainError(Exception):
    """Base exception for LappyBrain application errors."""


# Raised when something the app is looking for (a file, document, record) doesn't exist
class ResourceNotFoundError(LappyBrainError):
    """Raised when a requested resource cannot be found."""


# Raised when the user or process tries to access something they're not allowed to
class AccessDeniedError(LappyBrainError):
    """Raised when access to a resource is not permitted."""


# Raised when reading, parsing, or converting a document fails
class DocumentProcessingError(LappyBrainError):
    """Raised when a document cannot be processed."""


# Raised when the app can't reach the local Ollama language model
class LLMConnectionError(LappyBrainError):
    """Raised when the local language model is unavailable."""
