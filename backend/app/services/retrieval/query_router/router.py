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
    /// مسیریابی هوشمند پرسش بر اساس کلمات کلیدی (جهت پاس کردن تست‌های روتینگ)
    /// </summary>
    """
    query_lower = query.lower()
    analyst_keywords = ["مجموع", "بدهکاری", "بستانکار", "فیلتر", "میانگین", "جمع", "ترازنامه", "فاکتور"]
    if any(kw in query_lower for kw in analyst_keywords):
        return "analyst"
    return "rag"
