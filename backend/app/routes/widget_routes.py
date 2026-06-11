"""
/// <summary>
/// روتر ابزارک چت پاپ‌آپ وب‌سایت آریونکس (ArioNex Web Widget Chat Router)
/// </summary>
/// <remarks>
/// این ماژول دو اندپوینت ابزارک وب‌سایت را تعریف می‌کند:
///   ۱. GET /v1/widget.js   — فایل JavaScript پاپ‌آپ چت
///   ۲. POST /v1/widget/chat — اندپوینت پردازش پیام چت ابزارک
///
/// منطق session و RAG در widget_logic.py قرار دارد.
/// </remarks>
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.database import get_db_connection
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.logics.widget_logic import execute_widget_logic, execute_widget_stream_logic

logger = logging.getLogger("arionex.widget_routes")
router = APIRouter(prefix="/v1", tags=["Widget — Website Chat Popup"])


@router.get(
    "/widget.js",
    summary="دریافت فایل JavaScript ابزارک چت پاپ‌آپ",
    description="اسکریپت JavaScript خودمحور (self-contained) ابزارک چت وب‌سایت را برمی‌گرداند.",
)
async def get_web_widget_script(website: Optional[str] = None):
    """
    /// <summary>
    /// اندپوینت دریافت فایل جاوااسکریپت ابزارک چت پاپ‌آپ وب‌سایت
    /// </summary>
    /// <param name="website">آدرس وب‌سایت درخواست‌دهنده جهت شخصی‌سازی تم و پیام</param>
    /// <returns>کدهای جاوااسکریپت خودمحور با استایل‌دهی لوکس و بومی</returns>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is disabled in settings.")
        return Response(
            content="console.warn('ArioNex Website Chat Widget is disabled by the administrator.');",
            media_type="application/javascript",
        )

    # مقادیر پیش‌فرض تم و پیام خوش‌آمدگویی
    welcome_message = "سلام! من دستیار هوشمند آریونکس (ArioNex) هستم. چطور می‌توانم به شما کمک کنم؟ 💼✨"
    theme_color = "#1a2744"
    accent_color = "#c4894a"

    if website:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT welcome_message, theme_color, accent_color FROM website_widgets WHERE %s LIKE '%' || url || '%' OR url LIKE '%' || %s || '%' LIMIT 1",
                    (website, website)
                )
                row = cur.fetchone()
                if row:
                    welcome_message = row[0] or welcome_message
                    theme_color = row[1] or theme_color
                    accent_color = row[2] or accent_color
                    logger.info(f"Loaded customized widget config for website='{website}': theme_color={theme_color}")
        except Exception as e:
            logger.error(f"Error querying website widget database: {str(e)}")
        finally:
            if conn:
                conn.close()

    # خواندن اسکریپت جاوااسکریپت از فایل تمپلیت
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "widget.js.tmpl"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            js_code = f.read()
    except Exception as e:
        logger.error(f"Failed to read widget JS template from {template_path}: {str(e)}")
        return Response(
            content="console.error('ArioNex Website Chat Widget: template failed to load.');",
            media_type="application/javascript"
        )

    # اعمال پویای تنظیمات ابزارک
    custom_js = js_code.replace("#1a2744", theme_color)
    custom_js = custom_js.replace("#c4894a", accent_color)
    custom_js = custom_js.replace(
        "سلام! من دستیار هوشمند آریونکس (ArioNex) هستم. چطور می‌توانم به شما کمک کنم؟ 💼✨",
        welcome_message
    )

    return Response(content=custom_js, media_type="application/javascript")


@router.post(
    "/widget/chat",
    response_model=QueryResponse,
    summary="پردازش پیام ابزارک چت وب‌سایت",
    description="پرسش ارسال شده از ابزارک پاپ‌آپ وب‌سایت را دریافت کرده و با حفظ تاریخچه نشست پاسخ می‌دهد.",
)
async def process_widget_query(request: QueryRequest):
    """
    /// <summary>
    /// اندپوینت اختصاصی تبادل پیام ابزارک پاپ‌آپ وب‌سایت
    /// </summary>
    """
    return await execute_widget_logic(request)


@router.post(
    "/widget/chat/stream",
    summary="پردازش streaming پیام ابزارک چت وب‌سایت (SSE)",
    description="پاسخ ابزارک را به صورت Server-Sent Events ارسال می‌کند — کاربر هر توکن را به محض تولید می‌بیند.",
)
async def stream_widget_query(request: QueryRequest):
    """
    /// <summary>
    /// اندپوینت streaming تبادل پیام ابزارک — مناسب برای UX چت زنده
    /// </summary>
    """
    return StreamingResponse(
        execute_widget_stream_logic(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
