"""
/// <summary>
/// لایه انطباق عقب‌رو عامل سرپرست پشتیبانی (ArioNex Support Lead Agent Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// این فایل برای حفظ سازگاری با پرونده‌های تست فازهای قبلی ایجاد شده است
/// و درخواست‌ها را به ماژول جدید qna هدایت می‌کند.
/// </remarks>
"""

from app.services.retrieval.qna import qna_agent as support_lead_agent
