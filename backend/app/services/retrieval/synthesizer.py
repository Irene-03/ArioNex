"""
/// <summary>
/// لایه انطباق عقب‌رو سنتزکننده پاسخ (ArioNex Synthesizer Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// این فایل برای حفظ سازگاری با کدهای فازهای قبلی و تست‌های سیستمی ایجاد شده است
/// و درخواست‌ها را به ماژول جدید query_router هدایت می‌کند.
/// </remarks>
"""

from app.services.retrieval.query_router import route_query_intent, synthesize_rag_response
from app.prompts.rag_prompts import STANDARD_REFUSAL_MESSAGE
