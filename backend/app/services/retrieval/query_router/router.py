import logging

logger = logging.getLogger("arionex.query_router")

def route_query_intent(query: str) -> str:
    """
    /// <summary>
    /// تعیین هوشمند مسیر جستجو بر اساس کلیدواژه‌های پرسش
    /// </summary>
    /// <param name="query">پرسش مستقل کاربر</param>
    /// <returns>رشته‌ای نشان‌دهنده دسته‌بندی مسیر ('analyst' یا 'rag')</returns>
    """
    query_lower = query.lower()
    
    # کلمات کلیدی محاسباتی، جداول، حسابداری و آماری مالی
    structured_keywords = [
        "بدهکار", "بستانکار", "مجموع", "میانگین", "سند", "حساب", "چک", 
        "فاکتور", "تعداد تیکت", "groupby", "جمع ستون", "تراکنش"
    ]
    
    for kw in structured_keywords:
        if kw in query_lower:
            return "analyst"
            
    return "rag"
