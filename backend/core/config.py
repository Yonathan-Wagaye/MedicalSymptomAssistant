from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# `backend/core/config.py` -> two parents up is `backend/` (where `.env` lives).
_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=_env_path,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ENV_STATE: Literal["dev", "prod"] = Field(
        default="dev",
        validation_alias="ENV_STATE",
    )

    DATABASE_URL: str = Field(
        ...,
        validation_alias="DATABASE_URL"
    )

    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    LLM_MAX_TOKENS: int = Field(default=1024, validation_alias="LLM_MAX_TOKENS")
    LLM_TEMPERATURE: float = Field(default=0.3, validation_alias="LLM_TEMPERATURE")
    EMBEDDING_MODEL: str = Field(default="all-mpnet-base-v2", validation_alias="EMBEDDING_MODEL")
    EMBEDDING_DIM: int = Field(default=768, validation_alias="EMBEDDING_DIM")
    RERANKER_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias="RERANKER_MODEL",
    )
    BM25_INDEX_PATH: str = Field(default="./bm25_index.pkl", validation_alias="BM25_INDEX_PATH")


@lru_cache
def get_settings() -> Settings:
    # Values come from env / `.env`; type checkers do not model BaseSettings env binding.
    return Settings()  # type: ignore[call-arg]


config = get_settings()
