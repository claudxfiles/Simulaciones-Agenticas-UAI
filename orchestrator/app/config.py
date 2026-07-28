"""Configuración central de la aplicación.

Todo llega por variables de entorno (.env en local, secrets del
orquestador en producción). Nada de credenciales en el código.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    llm_model: str = "claude-sonnet-5"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2

    # Persistencia (opcional). Ej: postgresql://user:pass@host:5432/db
    database_url: str | None = None

    # Aplicación
    app_name: str = "agent"
    app_env: Literal["local", "staging", "production"] = "local"
    app_port: int = 8000
    app_log_level: str = "INFO"

    # Guardrails
    guardrail_max_input_chars: int = 4000

    # Agentes worker (sql_agent y stock_agent llaman un endpoint
    # OpenAI-compatible directo). openai_base_url permite apuntar a
    # DeepSeek/OpenRouter/etc en vez de OpenAI real.
    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    # RAG
    chroma_persist_dir: str = "./chroma_data"
    rag_top_k: int = 5

    # Trazabilidad (paso 07)
    trace_db_url: str = "sqlite:///./data/interactions.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
