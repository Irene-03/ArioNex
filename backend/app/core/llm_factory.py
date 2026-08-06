"""
/// <summary>
/// ArioNex unified LLM factory (ArioNex Unified LLM Factory)
/// </summary>
/// <remarks>
/// This module provides a unified interface for connecting to different language models.
/// In this way, all internal system code can use any provider without modification.
///
/// Supported providers:
///   - openai      : GPT-4o, GPT-4o-mini and other OpenAI models
///   - anthropic   : Claude 3.5 Sonnet, Claude 3 Haiku and other Anthropic models
///   - google      : Gemini 1.5 Pro, Gemini 1.5 Flash and other Google models
///   - deepseek    : DeepSeek-Chat, DeepSeek-Coder (via the OpenAI-compatible API)
///   - openrouter  : Access to all of the above models through a single API key (recommended for production)
///   - hormouz     : Gateway to 350+ models through a single API key — OpenAI-compatible (https://api.hormouz.net/v1)
///   - ollama      : Local models on personal hardware (no internet or API key required)
///
/// openrouter advantage: one API key, access to all models, automatic fallback, centralized cost management
/// ollama advantage: full privacy, offline, free of charge
/// </remarks>
"""

import logging
from functools import lru_cache
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("arionex.llm_factory")


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
):
    """
    /// <summary>
    /// Central factory for producing an LLM instance based on the provider selected in the settings
    /// </summary>
    /// <param name="provider">Provider name — openai, anthropic, google, deepseek, openrouter</param>
    /// <param name="model">Model name — if None, the default settings model is used</param>
    /// <param name="temperature">Model output temperature (0=deterministic, 1=creative)</param>
    /// <param name="max_tokens">Output token cap — if None, the provider default is used</param>
    /// <returns>An instance of BaseChatModel compatible with LangChain</returns>
    /// <remarks>
    /// This function is used as the single entry point for building a language model across the entire system.
    /// If the key is empty, a ValueError is raised.
    /// Built instances are cached per (provider, model, temperature) to remove the overhead
    /// of recreating the model object on every chain call.
    /// </remarks>
    """
    # Use default values from settings when none are provided
    active_provider = provider or settings.llm_provider
    active_model = model or settings.model_name
    return _get_llm_cached(active_provider, active_model, temperature, max_tokens)


@lru_cache(maxsize=32)
def _get_llm_cached(active_provider: str, active_model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Cached version of LLM instance creation (one instance per active configuration)
    /// </summary>
    """
    # Check whether the provider is enabled in the system settings
    is_enabled = True
    if hasattr(settings, "providers"):
        is_enabled = getattr(settings.providers, active_provider, True)

    if not is_enabled:
        logger.error(f"LLM Provider '{active_provider}' is disabled in configuration.")
        raise ValueError(f"LLM provider '{active_provider}' is currently disabled in config.yaml.")

    logger.info(f"LLM Factory: initializing provider='{active_provider}', model='{active_model}'")

    try:
        if active_provider == "openrouter":
            return _create_openrouter_llm(active_model, temperature, max_tokens)
        elif active_provider == "openai":
            return _create_openai_llm(active_model, temperature, max_tokens)
        elif active_provider == "anthropic":
            return _create_anthropic_llm(active_model, temperature, max_tokens)
        elif active_provider == "google":
            return _create_google_llm(active_model, temperature, max_tokens)
        elif active_provider == "deepseek":
            return _create_deepseek_llm(active_model, temperature, max_tokens)
        elif active_provider == "gapgpt":
            return _create_gapgpt_llm(active_model, temperature, max_tokens)
        elif active_provider == "avalai":
            return _create_avalai_llm(active_model, temperature, max_tokens)
        elif active_provider == "hormouz":
            return _create_hormouz_llm(active_model, temperature, max_tokens)
        elif active_provider == "ollama":
            return _create_ollama_llm(active_model, temperature, max_tokens)
        else:
            logger.warning(f"Unknown LLM provider '{active_provider}'. Falling back to OpenRouter.")
            return _create_openrouter_llm(active_model, temperature, max_tokens)

    except Exception as e:
        logger.error(f"LLM Factory failed to initialize provider '{active_provider}': {str(e)}")
        raise


# -------------------------------------------------------------------
# Internal LLM instance creation functions for each provider
# -------------------------------------------------------------------

def _create_openrouter_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through OpenRouter — one API key for all models
    /// </summary>
    /// <remarks>
    /// OpenRouter uses the OpenAI-compatible API.
    /// </remarks>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.openrouter_api_key
    _warn_if_mock(api_key, "OpenRouter")
    if not api_key or api_key.strip() == "" or "your-" in api_key:
        api_key = "mock-key-for-testing"

    return ChatOpenAI(
        model_name=model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://arionex.ai",
            "X-Title": "ArioNex Enterprise AI",
        },
        max_tokens=1024,
    )


def _create_openai_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the direct OpenAI API
    /// </summary>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.openai_api_key
    _warn_if_mock(api_key, "OpenAI")
    if not api_key or api_key.strip() == "" or "your-" in api_key:
        api_key = "mock-key-for-testing"

    return ChatOpenAI(
        model_name=model,
        temperature=temperature,
        openai_api_key=api_key,
        max_tokens=max_tokens or 1024,
    )



def _create_anthropic_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the Anthropic Claude API
    /// </summary>
    /// <remarks>
    /// Installation required: pip install langchain-anthropic
    /// Recommended model: claude-3-5-sonnet-20241022
    /// </remarks>
    """
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic not installed. Run: pip install langchain-anthropic"
        )

    api_key = settings.anthropic_api_key
    _warn_if_mock(api_key, "Anthropic")

    return ChatAnthropic(
        model_name=model,
        temperature=temperature,
        anthropic_api_key=api_key,
        max_tokens=max_tokens or 1024,
    )


def _create_google_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the Google Gemini API
    /// </summary>
    /// <remarks>
    /// Installation required: pip install langchain-google-genai
    /// Recommended model: gemini-1.5-pro-latest or gemini-1.5-flash
    /// </remarks>
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai not installed. Run: pip install langchain-google-genai"
        )

    api_key = settings.google_api_key
    _warn_if_mock(api_key, "Google Gemini")

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=api_key,
        max_output_tokens=max_tokens or 1024,
    )


def _create_deepseek_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the DeepSeek API (compatible with the OpenAI API)
    /// </summary>
    /// <remarks>
    /// DeepSeek uses the OpenAI-compatible API.
    /// Recommended model: deepseek-chat or deepseek-coder
    /// </remarks>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.deepseek_api_key
    _warn_if_mock(api_key, "DeepSeek")

    return ChatOpenAI(
        model_name=model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com/v1",
        max_tokens=max_tokens or 1024,
    )


def _create_gapgpt_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the GapGPT API (compatible with the OpenAI API)
    /// </summary>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.gapgpt_api_key
    _warn_if_mock(api_key, "GapGPT")

    # If the model is the default one, use gpt-4o-mini as the GapGPT default value
    active_model = model if model != "openai/gpt-4o-mini" else "gpt-4o-mini"

    return ChatOpenAI(
        model_name=active_model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.gapgpt.app/v1",
        max_tokens=max_tokens or 1024,
    )


def _create_avalai_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the AvalAI API (compatible with the OpenAI API)
    /// </summary>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.avalai_api_key
    _warn_if_mock(api_key, "AvalAI")

    # If the model is the default one, use gpt-4o-mini as the AvalAI default value
    active_model = model if model != "openai/gpt-4o-mini" else "gpt-4o-mini"

    return ChatOpenAI(
        model_name=active_model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.avalai.ir/v1",
        max_tokens=max_tokens or 1024,
    )


def _create_hormouz_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    /// <summary>
    /// Build an LLM through the Hormouz API (compatible with the OpenAI API) — gateway to 350+ models
    /// </summary>
    /// <remarks>
    /// Hormouz uses the OpenAI-compatible API.
    /// Base URL: https://api.hormouz.net/v1
    /// Models are specified in the "provider/model-name" format such as openai/gpt-4o.
    /// Supports streaming (SSE) and credit-based billing.
    /// </remarks>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.hormouz_api_key
    _warn_if_mock(api_key, "Hormouz")

    return ChatOpenAI(
        model_name=model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.hormouz.net/v1",
        streaming=True,
        max_tokens=max_tokens or 1024,
    )


def _create_ollama_llm(model: str, temperature: float, max_tokens: Optional[int] = None):
    """
    Build a local LLM through Ollama
    """
    ollama_model = getattr(settings, 'ollama_model', None) or model or 'gemma3:4b'
    ollama_base = getattr(settings, 'ollama_base_url', 'http://localhost:11434')
    
    # Log for debugging
    logger.info(f"🖥️ Ollama LLM: model='{ollama_model}', base_url='{ollama_base}'")
    
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=ollama_model,
            temperature=temperature,
            base_url=ollama_base,
            num_predict=max_tokens or 1024,
        )
    except ImportError:
        try:
            from langchain_community.chat_models import ChatOllama as CommChatOllama
            return CommChatOllama(
                model=ollama_model,
                temperature=temperature,
                base_url=ollama_base,
                num_predict=max_tokens or 1024,
            )
        except ImportError:
            raise ImportError(
                "Ollama LangChain integration not installed.\n"
                "Run: pip install langchain-ollama"
            )


def _warn_if_mock(api_key: str, provider_name: str) -> None:
    """
    /// <summary>
    /// Validate the presence of a valid API key and prevent the use of default or empty keys
    /// </summary>
    """
    import sys
    import os

    if not api_key or api_key.strip() == "" or "your-" in api_key:
        raise ValueError(
            f"کلید API برای پروایدر '{provider_name}' تنظیم نشده است. "
            f"لطفاً ابتدا از پنل مدیریت یکپارچه‌سازی، کلید API معتبر برای آن ست کنید."
        )

    if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING") == "true":
        logger.warning(f"Test environment detected. Skipping API key requirement validation for provider '{provider_name}'.")
        return



def get_embedding_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """
    /// <summary>
    /// Central factory for producing an Embedding model based on the selected provider
    /// </summary>
    /// <param name="provider">Provider name — openai, google, openrouter</param>
    /// <param name="model">Embedding model name — if None, the default value is used</param>
    /// <returns>A callable for generating embedding vectors</returns>
    /// <remarks>
    /// This function connects to the get_embedding function in embeddings.py
    /// and allows the embedding provider to be selected at runtime.
    /// Supported providers: openai (default), google
    /// </remarks>
    """
    active_provider = provider or settings.embedding_provider
    active_model = model or settings.embedding_model

    logger.info(f"Embedding Factory: provider='{active_provider}', model='{active_model}'")

    if active_provider == "google":
        return _create_google_embedding(active_model)
    else:
        # Default: OpenAI embeddings (compatible with openrouter and direct openai)
        return _create_openai_embedding(active_model)


def _create_openai_embedding(model: str):
    """
    /// <summary>
    /// Build an Embedding model from OpenAI (or any OpenAI-compatible endpoint)
    /// </summary>
    """
    from openai import OpenAI

    provider = settings.embedding_provider
    if provider == "openrouter":
        api_key = settings.openrouter_api_key
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "hormouz":
        api_key = settings.hormouz_api_key
        base_url = "https://api.hormouz.net/v1"
    elif provider == "deepseek":
        api_key = settings.deepseek_api_key
        base_url = "https://api.deepseek.com/v1"
    else:
        api_key = settings.openai_api_key
        base_url = None

    if not api_key or api_key.strip() == "" or "your-" in api_key:
        raise ValueError(
            f"کلید API برای پروایدر '{provider}' تنظیم نشده است. "
            f"لطفاً از پنل مدیریت، کلید API معتبر برای آن ست کنید."
        )

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    def embed(text: str) -> list:
        response = client.embeddings.create(model=model, input=text)
        return response.data[0].embedding

    return embed


def _create_google_embedding(model: str):
    """
    /// <summary>
    /// Build an Embedding model from Google Generative AI
    /// </summary>
    /// <remarks>
    /// Installation required: pip install google-generativeai
    /// Recommended model: models/text-embedding-004
    /// </remarks>
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai not installed. Run: pip install google-generativeai"
        )

    genai.configure(api_key=settings.google_api_key)

    def embed(text: str) -> list:
        result = genai.embed_content(model=model, content=text)
        return result["embedding"]

    return embed
