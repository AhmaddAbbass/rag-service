from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "rag"
    POSTGRES_USER: str = "rag"
    POSTGRES_PASSWORD: str = "rag"
    DATABASE_URL: str | None = None

    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str

    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    REDIS_URL: str = "redis://redis:6379/0"

    DATA_DIR: str = "/app/data"
    MAX_TEXT_CHARS: int = 2_000_000
    DEFAULT_RUNNER: str = "graph"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    SESSION_TTL_DAYS: int = 7

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
