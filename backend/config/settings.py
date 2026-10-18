from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: LappyBrain/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central configuration for the LappyBrain backend."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_name: str = "LappyBrain API"
    app_version: str = "0.1.0"
    debug: bool = True

    # Local API server
    host: str = "127.0.0.1"
    port: int = 8000

    # Local LLM configuration
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:12b"

    # Persistent storage
    storage_dir: Path = PROJECT_ROOT / "storage"

    @property
    def chroma_db_dir(self) -> Path:
        return self.storage_dir / "chroma_db"

    @property
    def extracted_text_dir(self) -> Path:
        return self.storage_dir / "extracted_text"

    @property
    def conversations_dir(self) -> Path:
        return self.storage_dir / "conversations"

    @property
    def database_path(self) -> Path:
        return self.storage_dir / "app.db"


# Shared settings instance
settings = Settings()
