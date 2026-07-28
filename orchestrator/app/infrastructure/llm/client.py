"""Factory del modelo de chat. Un solo punto de cambio de proveedor.

- anthropic: Claude directo (default).
- openai: cualquier endpoint OpenAI-compatible (OpenAI, LiteLLM proxy,
  OpenRouter, Groq…) usando LLM_BASE_URL.
"""
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )
