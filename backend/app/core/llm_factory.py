"""
/// <summary>
/// کارخانه یکپارچه مدل‌های زبانی آریونکس (ArioNex Unified LLM Factory)
/// </summary>
/// <remarks>
/// این ماژول یک رابط یکپارچه برای اتصال به مدل‌های زبانی مختلف فراهم می‌کند.
/// از این طریق تمام کد داخلی سیستم می‌تواند بدون تغییر از هر provider استفاده کند.
///
/// Provider‌های پشتیبانی‌شده:
///   - openai      : GPT-4o, GPT-4o-mini و سایر مدل‌های OpenAI
///   - anthropic   : Claude 3.5 Sonnet, Claude 3 Haiku و سایر مدل‌های Anthropic
///   - google      : Gemini 1.5 Pro, Gemini 1.5 Flash و سایر مدل‌های Google
///   - deepseek    : DeepSeek-Chat, DeepSeek-Coder (از طریق OpenAI-compatible API)
///   - openrouter  : دسترسی به تمام مدل‌های فوق از طریق یک API key واحد (پیشنهادی برای تولید)
///   - hormouz     : دروازه ۳۵۰+ مدل از طریق یک API key واحد — سازگار با OpenAI (https://api.hormouz.net/v1)
///   - ollama      : مدل‌های محلی روی سخت‌افزار شخصی (بدون نیاز به اینترنت یا API key)
///
/// مزیت openrouter: یک API key، دسترسی به همه مدل‌ها، fallback خودکار، مدیریت هزینه متمرکز
/// مزیت ollama: حریم‌خصوصی کامل، آفلاین، بدون هزینه
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
):
    """
    /// <summary>
    /// کارخانه مرکزی تولید نمونه LLM بر اساس provider انتخاب شده در تنظیمات
    /// </summary>
    /// <param name="provider">نام provider — openai, anthropic, google, deepseek, openrouter</param>
    /// <param name="model">نام مدل — در صورت None از مدل پیش‌فرض settings استفاده می‌شود</param>
    /// <param name="temperature">دمای خروجی مدل (0=قطعی، 1=خلاقانه)</param>
    /// <returns>نمونه‌ای از BaseChatModel سازگار با LangChain</returns>
    /// <remarks>
    /// این تابع به عنوان تنها نقطه ورود برای ساخت مدل زبانی در سراسر سیستم استفاده می‌شود.
    /// در صورت خالی بودن کلید، یک خطای ValueError صادر می‌کند.
    /// نمونه‌های ساخته‌شده برای هر (provider, model, temperature) کش می‌شوند تا سربار
    /// ساخت مجدد آبجکت مدل در هر فراخوانی زنجیره حذف شود.
    /// </remarks>
    """
    # استفاده از مقادیر پیش‌فرض از settings در صورت عدم ارائه
    active_provider = provider or settings.llm_provider
    active_model = model or settings.model_name
    return _get_llm_cached(active_provider, active_model, temperature)


@lru_cache(maxsize=32)
def _get_llm_cached(active_provider: str, active_model: str, temperature: float):
    """
    /// <summary>
    /// نسخه کش‌شده ساخت نمونه LLM (یک نمونه به ازای هر پیکربندی فعال)
    /// </summary>
    """
    # بررسی فعال بودن پروایدر در تنظیمات سیستم
    is_enabled = True
    if hasattr(settings, "providers"):
        is_enabled = getattr(settings.providers, active_provider, True)

    if not is_enabled:
        logger.error(f"LLM Provider '{active_provider}' is disabled in configuration.")
        raise ValueError(f"LLM provider '{active_provider}' is currently disabled in config.yaml.")

    logger.info(f"LLM Factory: initializing provider='{active_provider}', model='{active_model}'")

    try:
        if active_provider == "openrouter":
            return _create_openrouter_llm(active_model, temperature)
        elif active_provider == "openai":
            return _create_openai_llm(active_model, temperature)
        elif active_provider == "anthropic":
            return _create_anthropic_llm(active_model, temperature)
        elif active_provider == "google":
            return _create_google_llm(active_model, temperature)
        elif active_provider == "deepseek":
            return _create_deepseek_llm(active_model, temperature)
        elif active_provider == "gapgpt":
            return _create_gapgpt_llm(active_model, temperature)
        elif active_provider == "avalai":
            return _create_avalai_llm(active_model, temperature)
        elif active_provider == "hormouz":
            return _create_hormouz_llm(active_model, temperature)
        elif active_provider == "ollama":
            return _create_ollama_llm(active_model, temperature)
        else:
            logger.warning(f"Unknown LLM provider '{active_provider}'. Falling back to OpenRouter.")
            return _create_openrouter_llm(active_model, temperature)

    except Exception as e:
        logger.error(f"LLM Factory failed to initialize provider '{active_provider}': {str(e)}")
        raise


# -------------------------------------------------------------------
# توابع داخلی ساخت نمونه LLM برای هر provider
# -------------------------------------------------------------------

def _create_openrouter_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق OpenRouter — یک API key برای همه مدل‌ها
    /// </summary>
    /// <remarks>
    /// OpenRouter از OpenAI-compatible API استفاده می‌کند.
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


def _create_openai_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق OpenAI API مستقیم
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
        max_tokens=1024,
    )



def _create_anthropic_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق Anthropic Claude API
    /// </summary>
    /// <remarks>
    /// نیاز به نصب: pip install langchain-anthropic
    /// مدل پیشنهادی: claude-3-5-sonnet-20241022
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
        max_tokens=1024,
    )


def _create_google_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق Google Gemini API
    /// </summary>
    /// <remarks>
    /// نیاز به نصب: pip install langchain-google-genai
    /// مدل پیشنهادی: gemini-1.5-pro-latest یا gemini-1.5-flash
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
        max_output_tokens=1024,
    )


def _create_deepseek_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق DeepSeek API (سازگار با OpenAI API)
    /// </summary>
    /// <remarks>
    /// DeepSeek از OpenAI-compatible API استفاده می‌کند.
    /// مدل پیشنهادی: deepseek-chat یا deepseek-coder
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
        max_tokens=1024,
    )


def _create_gapgpt_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق GapGPT API (سازگار با OpenAI API)
    /// </summary>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.gapgpt_api_key
    _warn_if_mock(api_key, "GapGPT")

    # اگر مدل پیش‌فرض بود، از gpt-4o-mini به عنوان مقدار پیش‌فرض GapGPT استفاده شود
    active_model = model if model != "openai/gpt-4o-mini" else "gpt-4o-mini"

    return ChatOpenAI(
        model_name=active_model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.gapgpt.app/v1",
        max_tokens=1024,
    )


def _create_avalai_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق AvalAI API (سازگار با OpenAI API)
    /// </summary>
    """
    from langchain_openai import ChatOpenAI

    api_key = settings.avalai_api_key
    _warn_if_mock(api_key, "AvalAI")

    # اگر مدل پیش‌فرض بود، از gpt-4o-mini به عنوان مقدار پیش‌فرض AvalAI استفاده شود
    active_model = model if model != "openai/gpt-4o-mini" else "gpt-4o-mini"

    return ChatOpenAI(
        model_name=active_model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://api.avalai.ir/v1",
        max_tokens=1024,
    )


def _create_hormouz_llm(model: str, temperature: float):
    """
    /// <summary>
    /// ساخت LLM از طریق Hormouz API (سازگار با OpenAI API) — دروازه ۳۵۰+ مدل
    /// </summary>
    /// <remarks>
    /// Hormouz از OpenAI-compatible API استفاده می‌کند.
    /// Base URL: https://api.hormouz.net/v1
    /// مدل‌ها با فرمت "provider/model-name" مشخص می‌شوند مانند openai/gpt-4o.
    /// پشتیبانی از streaming (SSE) و billing اعتبار-محور.
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
        max_tokens=1024,
    )


def _create_ollama_llm(model: str, temperature: float):
    """
    ساخت LLM محلی از طریق Ollama
    """
    ollama_model = getattr(settings, 'ollama_model', None) or model or 'gemma3:4b'
    ollama_base = getattr(settings, 'ollama_base_url', 'http://localhost:11434')
    
    # لاگ برای دیباگ
    logger.info(f"🖥️ Ollama LLM: model='{ollama_model}', base_url='{ollama_base}'")
    
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=ollama_model,
            temperature=temperature,
            base_url=ollama_base,
            num_predict=1024,
        )
    except ImportError:
        try:
            from langchain_community.chat_models import ChatOllama as CommChatOllama
            return CommChatOllama(
                model=ollama_model,
                temperature=temperature,
                base_url=ollama_base,
                num_predict=1024,
            )
        except ImportError:
            raise ImportError(
                "Ollama LangChain integration not installed.\n"
                "Run: pip install langchain-ollama"
            )


def _warn_if_mock(api_key: str, provider_name: str) -> None:
    """
    /// <summary>
    /// بررسی وجود کلید API معتبر و سلب امکان استفاده از کلیدهای پیش‌فرض یا خالی
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
    /// کارخانه مرکزی تولید مدل Embedding بر اساس provider انتخاب شده
    /// </summary>
    /// <param name="provider">نام provider — openai, google, openrouter</param>
    /// <param name="model">نام مدل embedding — در صورت None از مقدار پیش‌فرض استفاده می‌شود</param>
    /// <returns>یک callable برای تولید embedding بردارها</returns>
    /// <remarks>
    /// این تابع به تابع get_embedding در embeddings.py وصل می‌شود
    /// و امکان انتخاب provider embedding را در runtime فراهم می‌کند.
    /// Provider‌های پشتیبانی‌شده: openai (پیش‌فرض), google
    /// </remarks>
    """
    active_provider = provider or settings.embedding_provider
    active_model = model or settings.embedding_model

    logger.info(f"Embedding Factory: provider='{active_provider}', model='{active_model}'")

    if active_provider == "google":
        return _create_google_embedding(active_model)
    else:
        # پیش‌فرض: OpenAI embeddings (سازگار با openrouter و openai مستقیم)
        return _create_openai_embedding(active_model)


def _create_openai_embedding(model: str):
    """
    /// <summary>
    /// ساخت مدل Embedding از OpenAI (یا هر endpoint سازگار با OpenAI)
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
    /// ساخت مدل Embedding از Google Generative AI
    /// </summary>
    /// <remarks>
    /// نیاز به نصب: pip install google-generativeai
    /// مدل پیشنهادی: models/text-embedding-004
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
