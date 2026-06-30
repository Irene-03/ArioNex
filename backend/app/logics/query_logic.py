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

import json
import logging
import asyncio
import time
from typing import AsyncGenerator, Optional
from fastapi import HTTPException, Request

from app.core.config import settings
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.services.retrieval.query_router import synthesize_rag_response, synthesize_rag_response_stream
from app.helpers.audit_logger import log_audit_event

from collections import OrderedDict

class LRUCache(OrderedDict):
    """
    /// <summary>
    /// کش کمکی کمترین استفاده اخیر (Least Recently Used Cache) برای محدودسازی نشست‌های فعال در حافظه جهت جلوگیری از حمله DoS سرریز حافظه
    /// </summary>
    """
    def __init__(self, maxsize=1000, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]

logger = logging.getLogger("arionex.query_logic")
_query_sessions = LRUCache(maxsize=1000)


async def execute_query_logic(request: QueryRequest, current_user: Optional[dict] = None) -> QueryResponse:
    """
    /// <summary>
    /// اجرای کامل منطق پردازش پرسش RAG از دریافت تا ممیزی با اعمال کنترل دسترسی (ACL)
    /// </summary>
    """
    if not settings.integrations.rest_api:
        logger.warning("REST API Integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="REST API Integration channel is disabled.")

    # استخراج شناسه‌های فایل مجاز بر اساس نقش کاربر (RBAC / ACL)
    allowed_file_ids = None
    username = "API_User"
    role = "Developer"
    
    if current_user:
        username = current_user.get("username", "API_User")
        role = current_user.get("role", "Developer")
        
        # اگر کاربر تحلیل‌گر است، فقط اسناد با دسترسی Analyst
        if role == "Analyst":
            from app.core.database import get_db_connection
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM documents WHERE min_role_required = 'Analyst'")
                    allowed_file_ids = [row[0] for row in cur.fetchall()]
                    if not allowed_file_ids:
                        allowed_file_ids = [-1]
            except Exception as e:
                logger.error(f"Failed to fetch allowed documents for {username}: {str(e)}")
                allowed_file_ids = [-1]
            finally:
                if conn:
                    conn.close()

    # اعمال فیلتر نهایی شناسه‌های فایل
    final_file_ids = request.file_ids
    if allowed_file_ids is not None:
        if final_file_ids:
            # اشتراک شناسه‌ها
            final_file_ids = list(set(final_file_ids).intersection(set(allowed_file_ids)))
            if not final_file_ids:
                final_file_ids = [-1]
        else:
            final_file_ids = allowed_file_ids

    try:
        # فراخوانی موتور RAG با تاریخچه نشست
        session_id = request.session_id
        if session_id not in _query_sessions:
            _query_sessions[session_id] = []
        chat_history = _query_sessions[session_id][-10:]

        start_time = time.time()
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=chat_history,
            threshold=0.4,
            k=4,
            file_ids=final_file_ids,
            session_id=session_id
        )
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        # Approximate tokens
        approx_tokens = (len(request.query) + len(result["answer"])) // 4

        # به‌روزرسانی تاریخچه نشست
        _query_sessions[session_id].append({"Human": request.query})
        _query_sessions[session_id].append({"AI": result["answer"]})

        # ثبت در سیستم ممیزی مرکزی
        log_audit_event(
            user_name=username,
            user_role=role,
            query_text=request.query,
            response_text=result["answer"],
            total_tokens=approx_tokens,
            response_time_ms=response_time_ms,
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            is_safe=result["is_safe"]
        )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Configuration/Validation error during query processing: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing API query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal RAG engine failure: {str(e)}")


async def execute_query_stream_logic(
    request: QueryRequest,
    current_user: Optional[dict] = None,
    http_request: Optional[Request] = None
) -> AsyncGenerator[str, None]:
    """
    /// <summary>
    /// نسخه streaming منطق پرسش با اعمال قوانین سطح دسترسی اسناد (ACL)
    /// </summary>
    """
    if not settings.integrations.rest_api:
        logger.warning("REST API streaming requested while disabled.")
        yield _sse_event("error", "REST API channel disabled")
        yield _sse_event("done", {"is_safe": True})
        return

    # استخراج شناسه‌های فایل مجاز بر اساس نقش کاربر (RBAC / ACL)
    allowed_file_ids = None
    username = "API_User"
    role = "Developer"
    
    if current_user:
        username = current_user.get("username", "API_User")
        role = current_user.get("role", "Developer")
        
        if role == "Analyst":
            from app.core.database import get_db_connection
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM documents WHERE min_role_required = 'Analyst'")
                    allowed_file_ids = [row[0] for row in cur.fetchall()]
                    if not allowed_file_ids:
                        allowed_file_ids = [-1]
            except Exception as e:
                logger.error(f"Failed to fetch allowed documents for {username} in stream: {str(e)}")
                allowed_file_ids = [-1]
            finally:
                if conn:
                    conn.close()

    final_file_ids = request.file_ids
    if allowed_file_ids is not None:
        if final_file_ids:
            final_file_ids = list(set(final_file_ids).intersection(set(allowed_file_ids)))
            if not final_file_ids:
                final_file_ids = [-1]
        else:
            final_file_ids = allowed_file_ids

    session_id = request.session_id
    if session_id not in _query_sessions:
        _query_sessions[session_id] = []
    history = _query_sessions[session_id][-10:]

    accumulated_answer = ""
    start_time = time.time()
    try:
        # Enforce a 60-second execution/inactivity timeout on the stream
        async with asyncio.timeout(60.0):
            async for event in synthesize_rag_response_stream(
                user_input=request.query,
                chat_history=history,
                threshold=0.4,
                k=4,
                file_ids=final_file_ids,
                session_id=session_id
            ):
                # Active cancellation check
                if http_request and await http_request.is_disconnected():
                    logger.warning("Streaming client disconnected actively. Aborting generation task.")
                    break

                if event["event"] == "token":
                    # Cap accumulated response memory buffer at 100k characters to prevent memory exhaustion leaks
                    if len(accumulated_answer) < 100000:
                        accumulated_answer += event["data"]
                    else:
                        if not accumulated_answer.endswith("... [Answer Truncated]"):
                            accumulated_answer += "... [Answer Truncated]"
                            logger.warning("Stream response output exceeded 100k char limit. Truncating audit record.")

                yield _sse_event(event["event"], event["data"])

        # Check if the client did not disconnect before saving session history & auditing
        if not (http_request and await http_request.is_disconnected()):
            # ثبت تاریخچه نشست
            _query_sessions[session_id].append({"Human": request.query})
            _query_sessions[session_id].append({"AI": accumulated_answer})

            # ثبت در سیستم ممیزی پس از پایان stream
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            approx_tokens = (len(request.query) + len(accumulated_answer)) // 4
            log_audit_event(
                user_name=username,
                user_role=role,
                query_text=request.query,
                response_text=accumulated_answer,
                total_tokens=approx_tokens,
                response_time_ms=response_time_ms,
            )
            yield _sse_event("done", {"is_safe": True})

    except TimeoutError as te:
        logger.error(f"Stream RAG timeout: {str(te)}")
        yield _sse_event("error", "Streaming request timed out.")
        yield _sse_event("done", {"is_safe": True})
    except Exception as e:
        logger.error(f"Stream RAG error: {str(e)}")
        yield _sse_event("error", str(e))
        yield _sse_event("done", {"is_safe": True})


def _sse_event(event: str, data) -> str:
    """
    /// <summary>
    /// قالب‌بندی یک رویداد در فرمت استاندارد Server-Sent Events
    /// </summary>
    /// <param name="event">نام رویداد (sources, token, done, error)</param>
    /// <param name="data">داده — رشته یا dict که به JSON تبدیل می‌شود</param>
    """
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    # حذف خطوط جدید از داده‌ها — SSE برای هر line جدا data: می‌خواهد
    safe_data = data.replace("\r\n", "\n").replace("\n", "\\n")
    return f"event: {event}\ndata: {safe_data}\n\n"
