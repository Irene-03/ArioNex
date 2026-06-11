"""
/// <summary>
/// فایل واسط مسیریاب و سنتزکننده پرسش آریونکس (ArioNex Query Router Facade)
/// </summary>
/// <remarks>
/// این ماژول برای حفظ سازگاری عقب‌رو قرار دارد و ایمپورت‌ها را به پکیج سازمان‌یافته query_router هدایت می‌کند.
/// </remarks>
"""

from app.services.retrieval.query_router import (
    route_query_intent,
    perform_tavily_web_search,
    synthesize_rag_response,
    synthesize_rag_response_stream
)
