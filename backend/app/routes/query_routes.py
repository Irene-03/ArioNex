"""
/// <summary>
/// روتر پرسش RAG آریونکس — POST /v1/query (ArioNex RAG Query Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت اصلی پرسش‌وپاسخ RAG را تعریف می‌کند.
/// منطق کامل پردازش در query_logic.py قرار دارد — این فایل فقط تعریف route است.
///
/// اندپوینت‌ها:
///   POST /v1/query  — دریافت پرسش کاربر و بازگرداندن پاسخ RAG
/// </remarks>
"""

from fastapi import APIRouter, Depends
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.logics.query_logic import execute_query_logic
from app.helpers.auth import verify_api_key

router = APIRouter(prefix="/v1", tags=["Query — RAG Assistant"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="ارسال پرسش به دستیار هوشمند RAG",
    description="پرسش کاربر را دریافت کرده، از طریق موتور بازیابی RAG پاسخ می‌دهد و منابع استنادی را برمی‌گرداند.",
)
async def process_rag_query(
    request: QueryRequest,
    api_key_name: str = Depends(verify_api_key)
):
    """
    /// <summary>
    /// اندپوینت اصلی ارسال پرسش به دستیار هوشمند RAG
    /// </summary>
    /// <param name="request">درخواست پرسش شامل متن سوال، شناسه نشست چت و فیلتر فایل‌ها</param>
    /// <param name="api_key_name">نام کلید استفاده شده برای احراز هویت (توسط Depends)</param>
    /// <returns>پاسخ نهایی دستیار به همراه لیست منابع استناد شده</returns>
    """
    return await execute_query_logic(request)
