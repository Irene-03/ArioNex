"""
/// <summary>
/// لایه انطباق عقب‌رو عامل کتابدار (ArioNex Librarian Agent Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// این فایل برای حفظ سازگاری با پرونده‌های تست فازهای قبلی ایجاد شده است
/// و درخواست‌ها را به ماژول جدید vector_search هدایت می‌کند.
/// </remarks>
"""

from app.services.retrieval.vector_search import vector_search_agent as librarian_agent
