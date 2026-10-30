import os
import string
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the LappyBrain project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def get_available_drives() -> list[Path]:
    """Discover all currently accessible Windows drive roots."""

    drives = []

    # Check each possible Windows drive letter.
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")

        try:
            # Include drives that are currently mounted and accessible.
            if os.path.isdir(drive):
                drives.append(drive)

        except OSError:
            # Skip drives that cannot be checked.
            continue

    return drives


class Settings(BaseSettings):
    """Central configuration for the LappyBrain backend."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General application information.
    app_name: str = "LappyBrain API"
    app_version: str = "0.1.0"
    debug: bool = True

    # Local API server configuration.
    host: str = "127.0.0.1"
    port: int = 8000

    # Local Ollama connection settings.
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:12b"

    # Persistent application storage.
    storage_dir: Path = PROJECT_ROOT / "storage"

    @property
    def file_search_roots(self) -> list[Path]:
        """Return all drives currently available for file discovery."""
        return get_available_drives()

    @property
    def chroma_db_dir(self) -> Path:
        """Return the configured ChromaDB directory."""
        return self.storage_dir / "chroma_db"

    @property
    def extracted_text_dir(self) -> Path:
        """Return the directory used for extracted document text."""
        return self.storage_dir / "extracted_text"

    @property
    def conversations_dir(self) -> Path:
        """Return the directory used for conversation histories."""
        return self.storage_dir / "conversations"

    @property
    def database_path(self) -> Path:
        """Return the application SQLite database path."""
        return self.storage_dir / "app.db"


# Create one shared settings instance for the application.
settings = Settings()
