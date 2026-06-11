"""
/// <summary>
/// ماژول تولید امبدینگ‌های برداری آریونکس — چندین provider (ArioNex Multi-Provider Embedding Engine)
/// </summary>
/// <remarks>
/// این ماژول وظیفه تبدیل متون chunk به بردار چند-بعدی را بر عهده دارد.
/// Provider و مدل embedding از settings قابل انتخاب هستند:
///
///   - openai:    text-embedding-3-large (۳۰۷۲ بعد) یا text-embedding-3-small (۱۵۳۶ بعد)
///   - google:    models/text-embedding-004
///   - hormouz:   هر مدل سازگار با OpenAI از طریق https://api.hormouz.net/v1
///   - openrouter: هر مدل سازگار با OpenAI از طریق https://openrouter.ai/api/v1
///
/// در صورت عدم وجود کلید API یا بروز خطا، بردار صفر با طول مناسب برمی‌گردد
/// تا فرآیند پردازش بدون کرش ادامه یابد (Graceful Degradation).
/// </remarks>
"""

import logging
import numpy as np
from app.core.config import settings

logger = logging.getLogger("arionex.embeddings")

# نگاشت ابعاد مدل‌های شناخته‌شده
_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    "models/text-embedding-004": 768,
}

def _get_embedding_dimension() -> int:
    """
    /// <summary>
    /// دریافت تعداد ابعاد بردار بر اساس مدل embedding انتخاب‌شده
    /// </summary>
    /// <returns>تعداد ابعاد بردار (پیش‌فرض: ۳۰۷۲)</returns>
    """
    return _EMBEDDING_DIMENSIONS.get(settings.embedding_model, 3072)


def get_embedding(text: str) -> list[float]:
    """
    /// <summary>
    /// تولید بردار ویژگی (Embedding) برای متن ورودی با استفاده از provider انتخاب‌شده
    /// </summary>
    /// <param name="text">متن ورودی برای embedding</param>
    /// <returns>لیستی از اعداد اعشاری — طول بستگی به مدل انتخاب‌شده دارد</returns>
    /// <remarks>
    /// در صورت خطا یا mock mode، بردار صفر با طول مناسب برمی‌گردد.
    /// این رفتار graceful degradation امکان تست بدون API key را فراهم می‌کند.
    /// </remarks>
    """
    dim = _get_embedding_dimension()

    if not text:
        return [0.0] * dim

    provider = settings.embedding_provider

    try:
        if provider == "google":
            return _embed_with_google(text)
        else:
            # پیش‌فرض: OpenAI یا هر endpoint سازگار
            return _embed_with_openai(text)
    except Exception as e:
        logger.error(
            f"Embedding generation failed (provider={provider}): {str(e)}. "
            f"Falling back to zero-vector of dimension {dim}."
        )
        return [0.0] * dim


def _embed_with_openai(text: str) -> list[float]:
    """
    /// <summary>
    /// تولید embedding از طریق OpenAI API یا هر endpoint سازگار با OpenAI (Hormouz, OpenRouter ...)
    /// </summary>
    """
    from openai import OpenAI

    provider = settings.embedding_provider
    model = settings.embedding_model
    dim = _get_embedding_dimension()

    # انتخاب کلید و base_url بر اساس provider فعال
    if provider == "hormouz":
        api_key = settings.hormouz_api_key
        base_url = "https://api.hormouz.net/v1"
    elif provider == "openrouter":
        api_key = settings.openrouter_api_key
        base_url = "https://openrouter.ai/api/v1"
    else:
        api_key = settings.openai_api_key
        base_url = None

    # تولید امبدینگ با کلاینت OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def _embed_with_google(text: str) -> list[float]:
    """
    /// <summary>
    /// تولید embedding از طریق Google Generative AI
    /// </summary>
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai not installed. Run: pip install google-generativeai"
        )

    api_key = settings.google_api_key
    model = settings.embedding_model
    dim = _get_embedding_dimension()

    genai.configure(api_key=api_key)
    result = genai.embed_content(model=model, content=text)
    return result["embedding"]
