import os

# Must match db/migrations/0001_init.sql's `embedding vector(384)` column -
# changing the embedding model requires a migration to resize it.
EMBEDDING_DIM = 384
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://triage:triage@localhost:5432/triage_agent"
        )
        self.embedding_model: str = os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


settings = Settings()
