"""
/// <summary>
/// ماژول تولید امبدینگ‌های برداری آریونکس (ArioNex Embedding Generation Engine)
/// </summary>
/// <remarks>
/// این ماژول وظیفه تبدیل متون چانک به برداری با طول ۳۰۷۲ (با استفاده از مدل text-embedding-3-large)
/// را بر عهده دارد. برای راحتی کار در مرحله توسعه محلی، در صورت بروز خطای عدم وجود یا نامعتبر بودن
/// کلید API، موتور به صورت هوشمند یک بردار صفر با طول ۳۰۷۲ بازمی‌گرداند تا فرآیند پردازش متوقف نشود.
/// </remarks>
"""

import logging
import numpy as np
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger("arionex.embeddings")

def get_embedding(text: str, model: str = "text-embedding-3-large") -> list[float]:
    """
    /// <summary>
    /// تولید بردار ویژگی (Embedding) برای متن ورودی
    /// </summary>
    /// <param name="text">متن ورودی</param>
    /// <param name="model">نام مدل امبدینگ (پیش‌فرض: text-embedding-3-large)</param>
    /// <returns>لیستی از اعداد اعشاری به طول ۳۰۷۲</returns>
    """
    if not text:
        return [0.0] * 3072
        
    # در صورتی که کلید API معتبر نباشد، برای تست محلی بردار صفر برمی‌گردانیم تا سیستم کرش نکند
    if not settings.openai_api_key or settings.openai_api_key == "mock_key" or "your-openai-key" in settings.openai_api_key:
        logger.warning("Using mock zero-embeddings. Please configure a valid OPENAI_API_KEY in backend/.env for real RAG search.")
        return [0.0] * 3072
        
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding from OpenAI API: {str(e)}. Falling back to zero-vector.")
        # برگرداندن بردار صفر به طول ۳۰۷۲
        return [0.0] * 3072
