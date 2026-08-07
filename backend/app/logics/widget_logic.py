"""
/// <summary>
/// ArioNex Web Widget Business Logic (ArioNex Web Widget Business Logic)
/// </summary>
/// <remarks>
/// This module separates the session management logic of the website popup chat widget from the router layer.
/// Responsibilities:
///   1. Check whether the widget is enabled in settings
///   2. Manage the chat session memory (In-Memory Session Store)
///   3. Call the central RAG engine with chat history
///   4. Update the session history
///   5. Log in the central audit system
/// </remarks>
"""

import json
import logging
import time
from typing import AsyncGenerator
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.services.retrieval.query_router import synthesize_rag_response, synthesize_rag_response_stream
from app.helpers.audit_logger import log_audit_event

logger = logging.getLogger("arionex.widget_logic")

# In-Memory store for the widget chat sessions
# In production, it should be replaced with Redis or a database
_widget_sessions: dict[str, list] = {}


async def execute_widget_logic(request: QueryRequest) -> QueryResponse:
    """
    /// <summary>
    /// Runs the full widget Q&A logic: session → RAG → audit → answer
    /// </summary>
    /// <param name="request">Request including the question text and the user's widget session ID</param>
    /// <returns>The assistant's final answer along with cited sources</returns>
    /// <remarks>
    /// The session history keeps at most the last 10 messages so memory is not blocked by long messages.
    /// _widget_sessions is a global dict — it may cause interference in parallel tests.
    /// For production, use Redis or a database to store sessions.
    /// </remarks>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="Website Pop-up Widget channel is disabled.")

    try:
        # 1. Retrieve the conversation history of the current session
        session_id = request.session_id
        if session_id not in _widget_sessions:
            _widget_sessions[session_id] = []

        # Keep at most the last 10 messages to control the context window
        history = _widget_sessions[session_id][-10:]

        # 2. Call the central RAG engine
        start_time = time.time()
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=history,
            threshold=0.4,
            k=4,
            file_ids=request.file_ids,
            session_id=session_id
        )
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        approx_input_tokens = len(request.query) // 4
        approx_output_tokens = len(result["answer"]) // 4
        approx_tokens = approx_input_tokens + approx_output_tokens

        # 3. Update the session history
        _widget_sessions[session_id].append({"Human": request.query})
        _widget_sessions[session_id].append({"AI": result["answer"]})

        # 4. Log in the audit system (an error does not interrupt the answer)
        log_audit_event(
            user_name="Widget_User",
            user_role="Viewer",
            query_text=request.query,
            response_text=result["answer"],
            total_tokens=approx_tokens,
            input_tokens=approx_input_tokens,
            output_tokens=approx_output_tokens,
            response_time_ms=response_time_ms,
            agent_type=result.get("agent_type", "rag"),
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
    /// Streaming version of the widget logic — sends the answer as SSE token by token
    /// </summary>
    /// <param name="request">Request including the question text and the widget session ID</param>
    /// <returns>async generator of SSE lines</returns>
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
    start_time = time.time()
    agent_type = "rag"
    try:
        async for event in synthesize_rag_response_stream(
            user_input=request.query,
            chat_history=history,
            threshold=0.4,
            k=4,
            session_id=session_id
        ):
            if event["event"] == "agent_type":
                agent_type = event["data"]
            elif event["event"] == "token":
                accumulated_answer += event["data"]
            yield _sse_event(event["event"], event["data"])

        # Update the session history after the stream ends
        _widget_sessions[session_id].append({"Human": request.query})
        _widget_sessions[session_id].append({"AI": accumulated_answer})

        # Audit logging
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        approx_input_tokens = len(request.query) // 4
        approx_output_tokens = len(accumulated_answer) // 4
        approx_tokens = approx_input_tokens + approx_output_tokens
        log_audit_event(
            user_name="Widget_User",
            user_role="Viewer",
            query_text=request.query,
            response_text=accumulated_answer,
            total_tokens=approx_tokens,
            input_tokens=approx_input_tokens,
            output_tokens=approx_output_tokens,
            response_time_ms=response_time_ms,
            agent_type=agent_type,
        )
    except Exception as e:
        logger.error(f"Widget stream error: {str(e)}")
        yield _sse_event("error", str(e))
        yield _sse_event("done", {"is_safe": True})


def _sse_event(event: str, data) -> str:
    """
    /// <summary>
    /// Format an event in the standard Server-Sent Events format
    /// </summary>
    """
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    safe_data = data.replace("\r\n", "\n").replace("\n", "\\n")
    return f"event: {event}\ndata: {safe_data}\n\n"
