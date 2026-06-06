"""
/// <summary>
/// [DEPRECATED] فایل endpoint‌های قدیمی آریونکس — منسوخ شده
/// </summary>
/// <remarks>
/// این فایل در نسخه ۱.۱.۰ منسوخ شده و فقط برای سازگاری با کدهای قدیمی نگهداری می‌شود.
///
/// مسیر جدید endpoint‌ها:
///   /v1/query       → app/routes/query_routes.py
///   /v1/upload      → app/routes/upload_routes.py
///   /v1/config      → app/routes/config_routes.py
///   /v1/widget.*    → app/routes/widget_routes.py
///
/// منطق کسب‌وکار:
///   → app/logics/query_logic.py
///   → app/logics/upload_logic.py
///   → app/logics/widget_logic.py
///
/// این فایل در نسخه بعدی حذف خواهد شد.
/// </remarks>
"""

# این فایل منسوخ شده است.
# کد اصلی به app/routes/ و app/logics/ منتقل شده است.
# برای راهنمایی به backend/README.md مراجعه کنید.

raise ImportError(
    "endpoints.py is deprecated in v1.1.0. "
    "Use app.routes.* and app.logics.* instead. "
    "See backend/README.md for the new structure."
)
