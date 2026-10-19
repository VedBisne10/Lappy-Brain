from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Walk up 2 levels from this file (config/) → backend/ → LappyBrain/ to get the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central configuration for the LappyBrain backend."""

    # Tell pydantic-settings where to find the .env file and how to read it
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",          # Silently ignore any extra keys in .env
    )

    # --- General app info ---
    app_name: str = "LappyBrain API"
    app_version: str = "0.1.0"
    debug: bool = True           # Set to False in production

    # --- Local API server address ---
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Ollama (local LLM) connection settings ---
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:12b"

    # --- Root folder where all persistent data is saved ---
    storage_dir: Path = PROJECT_ROOT / "storage"

    @property
    def chroma_db_dir(self) -> Path:
        # Folder where the ChromaDB vector database files are stored
        return self.storage_dir / "chroma_db"

    @property
    def extracted_text_dir(self) -> Path:
        # Folder where text extracted from documents (PDFs, DOCX, etc.) is saved
        return self.storage_dir / "extracted_text"

    @property
    def conversations_dir(self) -> Path:
        # Folder where saved conversation histories are stored
        return self.storage_dir / "conversations"

    @property
    def database_path(self) -> Path:
        # Full path to the SQLite database file
        return self.storage_dir / "app.db"


# Single shared settings instance — import this everywhere instead of creating a new one
settings = Settings()
