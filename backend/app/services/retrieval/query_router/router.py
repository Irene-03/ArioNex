"""
/// <summary>
/// [DEPRECATED] ماژول تشخیص مسیر پرسش — routing حذف شده است
/// </summary>
/// <remarks>
/// این ماژول برای حفظ سازگاری با import‌های موجود نگه داشته شده اما دیگر در
/// synthesizer.py فراخوانی نمی‌شود.
/// 
/// دلیل حذف routing:
///   - در یک سیستم RAG واقعی، embedding خودش شباهت معنایی را تشخیص می‌دهد
///   - keyword matching ساده می‌تواند route اشتباه بدهد (مثل "قوانین مجموع جرایم" → analyst)
///   - یک مسیر واحد بدون فرض درباره محتوای داده کاربر کار می‌کند
/// </remarks>
"""
import logging

logger = logging.getLogger("arionex.query_router")


def route_query_intent(query: str) -> str:
    """
    /// <summary>
    /// [DEPRECATED] این تابع دیگر استفاده نمی‌شود — routing حذف شده است
    /// </summary>
    /// <returns>همیشه 'rag' برمی‌گرداند</returns>
    """
    logger.debug("route_query_intent called but routing is disabled. Returning 'rag' always.")
    return "rag"
