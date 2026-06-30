"""
/// <summary>
/// ثبت‌کننده ممیزی مرکزی آریونکس (ArioNex Centralized Audit Logger)
/// </summary>
/// <remarks>
/// این ماژول وظیفه ثبت تمام تعاملات کاربر با سیستم RAG را در جدول pg_audit_logs دیتابیس
/// بر عهده دارد. هر پرسش ارسال شده از طریق هر کانال (REST API، Widget، Telegram) در این
/// جدول ثبت می‌شود تا قابلیت ممیزی و تحلیل رفتار کاربری وجود داشته باشد.
///
/// استفاده از این helper به جای کد تکراری در هر endpoint، یکپارچگی فرمت داده را تضمین می‌کند.
/// خطاهای ثبت ممیزی به صورت silent لاگ می‌شوند تا پاسخ اصلی مختل نشود.
/// </remarks>
"""

import logging
from app.core.database import get_db_connection

logger = logging.getLogger("arionex.audit_logger")

# دستور SQL ثبت لاگ ممیزی — قابل استفاده در هر channel
_AUDIT_INSERT_SQL = """
INSERT INTO pg_audit_logs (user_name, user_role, query_text, response_text, status, pii_masked_count, total_tokens, response_time_ms)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def log_audit_event(
    user_name: str,
    user_role: str,
    query_text: str,
    response_text: str,
    status: str = "success",
    pii_masked_count: int = 0,
    total_tokens: int = 0,
    response_time_ms: int = 0,
) -> None:
    """
    /// <summary>
    /// ثبت یک رویداد تعامل کاربر در جدول ممیزی مرکزی pg_audit_logs
    /// </summary>
    /// <param name="user_name">نام یا شناسه کاربر (مثال: "API_User", "Widget_User")</param>
    /// <param name="user_role">نقش کاربر در سیستم (مثال: "Developer", "Viewer", "Admin")</param>
    /// <param name="query_text">متن پرسش ارسال شده توسط کاربر</param>
    /// <param name="response_text">متن پاسخ تولید شده توسط سیستم RAG</param>
    /// <param name="status">وضعیت پاسخ — "success" یا "error" (پیش‌فرض: "success")</param>
    /// <param name="pii_masked_count">تعداد اطلاعات حساس ماسک شده (پیش‌فرض: ۰)</param>
    /// <remarks>
    /// این تابع در یک try-except محافظت‌شده اجرا می‌شود تا خطاهای دیتابیس باعث قطع
    /// پاسخ اصلی به کاربر نشوند. خطا فقط در لاگ ثبت می‌شود.
    /// </remarks>
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(_AUDIT_INSERT_SQL, (
                user_name,
                user_role,
                query_text,
                response_text,
                status,
                pii_masked_count,
                total_tokens,
                response_time_ms,
            ))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Audit log insertion failed (non-critical): {str(e)}")
