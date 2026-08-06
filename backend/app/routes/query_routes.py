"""
/// <summary>
/// ArioNex RAG Query Router — POST /v1/query (ArioNex RAG Query Router)
/// </summary>
/// <remarks>
/// This module defines the main RAG Q&A endpoint.
/// The full processing logic lives in query_logic.py — this file only defines routes.
///
/// Endpoints:
///   POST /v1/query         — accept a user query and return the RAG answer (one-shot)
///   POST /v1/query/stream  — RAG answer as Server-Sent Events (SSE) — token by token
/// </remarks>
"""

from fastapi import APIRouter, Depends, Request
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
    /// Main endpoint for sending a query to the smart RAG assistant (one-shot answer)
    /// </summary>
    """
    return await execute_query_logic(request, current_user)


@router.post(
    "/query/stream",
    summary="پاسخ پرسش RAG به صورت Streaming (SSE)",
    description="پاسخ مدل را به صورت توکن‌به‌توکن از طریق Server-Sent Events ارسال می‌کند. کلاینت باید رویدادهای sources، token و done را مدیریت کند.",
)
async def stream_rag_query(
    http_request: Request,
    request: QueryRequest,
    current_user: dict = Depends(get_current_user_or_api_key)
):
    """
    /// <summary>
    /// RAG query streaming endpoint — suitable for live chat UIs
    /// </summary>
    /// <returns>StreamingResponse with media-type text/event-stream</returns>
    """
    return StreamingResponse(
        execute_query_stream_logic(request, current_user, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
