"""
/// <summary>
/// منطق کسب‌وکار اندپوینت پرسش RAG (ArioNex Query Business Logic)
/// </summary>
/// <remarks>
/// این ماژول منطق پردازش درخواست‌های RAG را از لایه روتر FastAPI جدا می‌کند.
/// مسئولیت‌ها:
///   ۱. بررسی فعال بودن کانال REST API در تنظیمات
///   ۲. فراخوانی موتور RAG مرکزی (synthesize_rag_response)
///   ۳. ثبت نتایج در سیستم ممیزی مرکزی
///   ۴. بازگرداندن پاسخ نهایی ساختاریافته
/// </remarks>
"""

import logging
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.services.retrieval.query_router import synthesize_rag_response
from app.helpers.audit_logger import log_audit_event

logger = logging.getLogger("arionex.query_logic")


async def execute_query_logic(request: QueryRequest) -> QueryResponse:
    """
    /// <summary>
    /// اجرای کامل منطق پردازش پرسش RAG از دریافت تا ممیزی
    /// </summary>
    /// <param name="request">درخواست پرسش شامل متن سوال، شناسه نشست و فیلتر فایل‌ها</param>
    /// <returns>پاسخ نهایی دستیار به همراه منابع استنادی و وضعیت ایمنی</returns>
    /// <remarks>
    /// این تابع توسط route /v1/query و هر مصرف‌کننده دیگری فراخوانی می‌شود.
    /// خطاهای ممیزی به صورت silent لاگ می‌شوند تا پاسخ اصلی مختل نشود.
    /// </remarks>
    """
    if not settings.integrations.rest_api:
        logger.warning("REST API Integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="REST API Integration channel is disabled.")

    try:
        # فراخوانی موتور RAG — تاریخچه چت فعلاً خالی است (در فاز بعدی از session store لود می‌شود)
        chat_history = []
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=chat_history,
            threshold=0.4,
            k=4,
            file_ids=request.file_ids
        )

        # ثبت در سیستم ممیزی مرکزی (خطا باعث قطع پاسخ نمی‌شود)
        log_audit_event(
            user_name="API_User",
            user_role="Developer",
            query_text=request.query,
            response_text=result["answer"],
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            is_safe=result["is_safe"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing API query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal RAG engine failure: {str(e)}")
