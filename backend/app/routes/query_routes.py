"""
/// <summary>
/// روتر پرسش RAG آریونکس — POST /v1/query (ArioNex RAG Query Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت اصلی پرسش‌وپاسخ RAG را تعریف می‌کند.
/// منطق کامل پردازش در query_logic.py قرار دارد — این فایل فقط تعریف route است.
///
/// اندپوینت‌ها:
///   POST /v1/query         — دریافت پرسش کاربر و بازگرداندن پاسخ RAG (یکجا)
///   POST /v1/query/stream  — پاسخ RAG به صورت Server-Sent Events (SSE) — توکن به توکن
/// </remarks>
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.logics.query_logic import execute_query_logic, execute_query_stream_logic
from app.helpers.auth import get_current_user_or_api_key

router = APIRouter(prefix="/v1", tags=["Query — RAG Assistant"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="ارسال پرسش به دستیار هوشمند RAG",
    description="پرسش کاربر را دریافت کرده، از طریق موتور بازیابی RAG پاسخ می‌دهد و منابع استنادی را برمی‌گرداند.",
)
async def process_rag_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user_or_api_key)
):
    """
    /// <summary>
    /// اندپوینت اصلی ارسال پرسش به دستیار هوشمند RAG (پاسخ یکجا)
    /// </summary>
    """
    return await execute_query_logic(request, current_user)


@router.post(
    "/query/stream",
    summary="پاسخ پرسش RAG به صورت Streaming (SSE)",
    description="پاسخ مدل را به صورت توکن‌به‌توکن از طریق Server-Sent Events ارسال می‌کند. کلاینت باید رویدادهای sources، token و done را مدیریت کند.",
)
async def stream_rag_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user_or_api_key)
):
    """
    /// <summary>
    /// اندپوینت streaming پرسش RAG — مناسب برای UIهای چت زنده
    /// </summary>
    /// <returns>StreamingResponse با media-type text/event-stream</returns>
    """
    return StreamingResponse(
        execute_query_stream_logic(request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
