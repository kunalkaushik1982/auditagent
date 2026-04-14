"""
Shared AI client factory.

Centralizes provider/model selection so .env changes apply consistently
across all chat and embedding services.
"""

import os

from backend.app.core.config import settings


def get_llm_provider() -> str:
    return settings.LLM_PROVIDER.strip().lower()


def get_embedding_provider() -> str:
    provider = settings.EMBEDDING_PROVIDER.strip().lower()
    return provider or get_llm_provider()


def get_chat_model_name() -> str:
    if settings.LLM_MODEL.strip():
        return settings.LLM_MODEL.strip()

    provider = get_llm_provider()
    if provider == "ollama":
        return settings.OLLAMA_MODEL
    if provider == "openai":
        return settings.OPENAI_MODEL

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


def get_embedding_model_name() -> str:
    if settings.EMBEDDING_MODEL.strip():
        return settings.EMBEDDING_MODEL.strip()

    provider = get_embedding_provider()
    if provider == "ollama":
        return settings.OLLAMA_EMBEDDING_MODEL
    if provider == "openai":
        return settings.OPENAI_EMBEDDING_MODEL

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")


def get_chat_llm(*, temperature: float = 0):
    provider = get_llm_provider()
    model = get_chat_model_name()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise ImportError(
                "langchain-ollama is required when LLM_PROVIDER=ollama"
            ) from exc

        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model,
            temperature=temperature,
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")

        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


def get_embeddings():
    provider = get_embedding_provider()
    model = get_embedding_model_name()

    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:
            raise ImportError(
                "langchain-ollama is required when EMBEDDING_PROVIDER=ollama"
            ) from exc

        return OllamaEmbeddings(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")

        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=model,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")
