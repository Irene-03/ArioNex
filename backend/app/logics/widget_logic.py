"""
/// <summary>
/// منطق کسب‌وکار اندپوینت ابزارک چت وب‌سایت (ArioNex Web Widget Business Logic)
/// </summary>
/// <remarks>
/// این ماژول منطق مدیریت نشست‌های گفتگوی ابزارک پاپ‌آپ وب‌سایت را از لایه روتر جدا می‌کند.
/// مسئولیت‌ها:
///   ۱. بررسی فعال بودن ابزارک در تنظیمات
///   ۲. مدیریت حافظه نشست‌های گفتگو (In-Memory Session Store)
///   ۳. فراخوانی موتور RAG مرکزی با تاریخچه چت
///   ۴. به‌روزرسانی تاریخچه نشست
///   ۵. ثبت در سیستم ممیزی مرکزی
/// </remarks>
"""

import json
import logging
from typing import AsyncGenerator
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.services.retrieval.query_router import synthesize_rag_response, synthesize_rag_response_stream
from app.helpers.audit_logger import log_audit_event

logger = logging.getLogger("arionex.widget_logic")

# ذخیره‌ساز In-Memory برای نشست‌های گفتگوی ابزارک
# در محیط تولید، باید با Redis یا دیتابیس جایگزین شود
_widget_sessions: dict[str, list] = {}


async def execute_widget_logic(request: QueryRequest) -> QueryResponse:
    """
    /// <summary>
    /// اجرای کامل منطق پرسش‌وپاسخ ابزارک: session → RAG → ممیزی → پاسخ
    /// </summary>
    /// <param name="request">درخواست شامل متن پرسش و شناسه نشست ابزارک کاربر</param>
    /// <returns>پاسخ نهایی دستیار به همراه منابع استنادی</returns>
    /// <remarks>
    /// تاریخچه نشست حداکثر ۱۰ پیام آخر را نگه می‌دارد تا حافظه در پیام‌های طولانی بلوک نشود.
    /// _widget_sessions یک dict سراسری است — در تست‌های موازی ممکن است تداخل ایجاد شود.
    /// برای محیط تولید، از Redis یا پایگاه داده برای ذخیره نشست استفاده کنید.
    /// </remarks>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="Website Pop-up Widget channel is disabled.")

    try:
        # ۱. بازیابی تاریخچه مکالمه نشست جاری
        session_id = request.session_id
        if session_id not in _widget_sessions:
            _widget_sessions[session_id] = []

        # حداکثر ۱۰ پیام آخر جهت کنترل window context
        history = _widget_sessions[session_id][-10:]

        # ۲. فراخوانی موتور RAG مرکزی
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=history,
            threshold=0.4,
            k=4,
            file_ids=request.file_ids
        )

        # ۳. به‌روزرسانی تاریخچه نشست
        _widget_sessions[session_id].append({"Human": request.query})
        _widget_sessions[session_id].append({"AI": result["answer"]})

        # ۴. ثبت در سیستم ممیزی (خطا باعث قطع پاسخ نمی‌شود)
        log_audit_event(
            user_name="Widget_User",
            user_role="Viewer",
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
        logger.error(f"Error processing widget chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Widget RAG failure: {str(e)}")


async def execute_widget_stream_logic(request: QueryRequest) -> AsyncGenerator[str, None]:
    """
    /// <summary>
    /// نسخه streaming منطق ابزارک — پاسخ را به صورت SSE توکن به توکن می‌فرستد
    /// </summary>
    /// <param name="request">درخواست شامل متن سوال و شناسه نشست ابزارک</param>
    /// <returns>async generator از خطوط SSE</returns>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Widget streaming requested while popup_widget disabled.")
        yield _sse_event("error", "Widget channel disabled")
        yield _sse_event("done", {"is_safe": True})
        return

    session_id = request.session_id
    if session_id not in _widget_sessions:
        _widget_sessions[session_id] = []
    history = _widget_sessions[session_id][-10:]

    accumulated_answer = ""
    try:
        async for event in synthesize_rag_response_stream(
            user_input=request.query,
            chat_history=history,
            threshold=0.4,
            k=4,
        ):
            if event["event"] == "token":
                accumulated_answer += event["data"]
            yield _sse_event(event["event"], event["data"])

        # به‌روزرسانی تاریخچه نشست پس از پایان stream
        _widget_sessions[session_id].append({"Human": request.query})
        _widget_sessions[session_id].append({"AI": accumulated_answer})

        # ثبت ممیزی
        log_audit_event(
            user_name="Widget_User",
            user_role="Viewer",
            query_text=request.query,
            response_text=accumulated_answer,
        )
    except Exception as e:
        logger.error(f"Widget stream error: {str(e)}")
        yield _sse_event("error", str(e))
        yield _sse_event("done", {"is_safe": True})


def _sse_event(event: str, data) -> str:
    """
    /// <summary>
    /// قالب‌بندی یک رویداد در فرمت استاندارد Server-Sent Events
    /// </summary>
    """
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    safe_data = data.replace("\r\n", "\n").replace("\n", "\\n")
    return f"event: {event}\ndata: {safe_data}\n\n"
