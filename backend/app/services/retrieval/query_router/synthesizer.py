import logging
from typing import Optional, AsyncGenerator
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.prompts.rag_prompts import RESPONDER_TEMPLATE, STANDARD_REFUSAL_MESSAGE
from app.services.retrieval.query_rewriter import rewrite_query

from app.services.retrieval.query_router.web_search import _get_active_api_key, perform_tavily_web_search
from app.services.retrieval.vector_search import vector_search_agent
from app.services.retrieval.qna import qna_agent
from app.services.retrieval.investigator import investigator_agent
from app.services.retrieval.lawyer import lawyer_agent
from app.core.database import get_db_connection

logger = logging.getLogger("arionex.query_router")

# کلمات کلیدی برای تشخیص سوال عمومی/احوال‌پرسی
_GENERAL_QUERY_PATTERNS = [
    "سلام", "خداحافظ", "ممنون", "متشکرم", "چطوری", "چطور هستی",
    "حالت چطور", "hi", "hello", "bye", "thanks", "thank you",
    "کمک کن", "چه کاری می‌تونی", "چه کاری میتونی", "معرفی کن",
    "who are you", "what can you do",
]


def _is_general_query(query: str) -> bool:
    """
    /// <summary>
    /// تشخیص اینکه آیا پرسش کاربر یک سوال عمومی/احوال‌پرسی است یا خیر
    /// </summary>
    /// <returns>True اگر سوال عمومی باشد</returns>
    """
    q = query.strip().lower()
    # سوال‌های خیلی کوتاه (کمتر از ۱۵ کاراکتر) احتمالاً عمومی هستند
    if len(q) < 15 and not any(c.isdigit() for c in q):
        return True
    for pattern in _GENERAL_QUERY_PATTERNS:
        if pattern in q:
            return True
    return False


def synthesize_rag_response(user_input: str, chat_history: list, threshold: float = 0.4, k: int = 4, file_ids: Optional[list[int]] = None) -> dict:
    """
    /// <summary>
    /// هماهنگ‌کننده نهایی زنجیره خواندن RAG: بازنویسی، بازیابی، رتبه‌بندی مجدد، پیوند گراف دانش، و ممیزی انطباق قوانین
    /// </summary>
    /// <remarks>
    /// Routing حذف شده — همه queries از مسیر واحد RAG عبور می‌کنند.
    /// Embedding خودش شباهت معنایی را تشخیص می‌دهد و نیازی به pre-routing نیست.
    /// </remarks>
    """
    logger.info(f"Synthesizer received query from chat session.")

    standalone_query = rewrite_query(user_input, chat_history)

    vector_results = vector_search_agent.retrieve_context(standalone_query, threshold=threshold, k=k, file_ids=file_ids)
    qna_results = qna_agent.retrieve_context(standalone_query, threshold=threshold, k=k, file_ids=file_ids)

    all_results = vector_results + qna_results
    sorted_results = sorted(all_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]

    if not sorted_results and settings.services.web_search:
        logger.info("Local knowledge base yields zero matches. Activating Tavily fallback search...")
        web_results = perform_tavily_web_search(standalone_query)
        sorted_results = sorted(web_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]

    if not sorted_results:
        # بررسی اینکه آیا سوال عمومی است — اگر بله LLM بدون context پاسخ دهد
        if _is_general_query(standalone_query):
            logger.info("No RAG context found but query is general. Delegating to LLM without context (general_chat mode).")
            return _answer_without_context(user_input, chat_history)

        logger.warning("Zero relevant context retrieved across all agents. Refusing to answer to prevent hallucination.")
        return {
            "answer": STANDARD_REFUSAL_MESSAGE,
            "sources": [],
            "is_safe": True
        }

    active_file_id = None
    if file_ids:
        active_file_id = file_ids[0]
    elif sorted_results:
        active_file_id = sorted_results[0].get("file_id")
        if active_file_id == 0:
            active_file_id = None

    formatted_context_list = []
    sources = []

    graph_context = investigator_agent.retrieve_graph_context(standalone_query, active_file_id)
    if graph_context:
        formatted_context_list.append(graph_context)

    for item in sorted_results:
        content = item["content"]
        label = item["label"]
        seq_id = item["sequence_id"]

        clean_content = content.replace(", Answer:", "\nAnswer:")
        formatted_context_list.append(clean_content)

        page_label = f"قطعه {seq_id}" if seq_id else "مخزن داده"
        sources.append({
            "name": label,
            "page": page_label
        })

    context_str = "\n\n".join(formatted_context_list)

    rules_list = []
    if settings.services.rule_extractor and active_file_id:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rule_code, clause FROM extracted_rules WHERE file_id = %s",
                    (active_file_id,)
                )
                rows = cur.fetchall()
                for row in rows:
                    rules_list.append(f"- {row[0]}: {row[1]}")
        except Exception as e:
            logger.error(f"Failed to fetch rules for constraint injection: {str(e)}")
        finally:
            if conn:
                conn.close()

    compliance_constraints = ""
    if rules_list:
        rules_formatted = "\n    ".join(rules_list)
        compliance_constraints = f"\n    5. Follow these strict corporate COMPLIANCE RULES when answering:\n    {rules_formatted}\n"

    system_instruction = _fetch_system_instruction()

    active_provider = settings.llm_provider
    active_key = _get_active_api_key(active_provider)

    try:
        llm = get_llm(temperature=0.1)

        from app.services.retrieval.query_rewriter import format_chat_history
        formatted_history = format_chat_history(chat_history)

        prompt = PromptTemplate.from_template(RESPONDER_TEMPLATE)
        chain = prompt | llm

        response = chain.invoke({
            "reranked_text": context_str,
            "chat_history": formatted_history,
            "user_input": user_input,
            "compliance_constraints": compliance_constraints,
            "system_instruction": system_instruction
        })

        final_answer = response.content.strip()

        if final_answer == "####" or not final_answer:
            logger.warning("Responder LLM outputted refusal placeholder '####'. Emitting standard Persian refusal.")
            return {
                "answer": STANDARD_REFUSAL_MESSAGE,
                "sources": [],
                "is_safe": True
            }

        audit_result = lawyer_agent.audit_compliance(standalone_query, final_answer, active_file_id)
        if not audit_result.get("is_compliant", True):
            logger.warning(f"Lawyer Agent detected compliance violations: {audit_result.get('violations')}. Blocking response.")
            return {
                "answer": STANDARD_REFUSAL_MESSAGE,
                "sources": [],
                "is_safe": False
            }

        if audit_result.get("audit_report"):
            final_answer += f"\n\n⚖️ **گزارش انطباق قوانین (ArioNex Lawyer Audit):**\n*{audit_result['audit_report']}*"

        logger.info("Successfully generated audited RAG response.")
        return {
            "answer": final_answer,
            "sources": sources[:3],
            "is_safe": True
        }

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Final LLM responder synthesis failed: {str(e)}. Emitting refusal.")
        return {
            "answer": STANDARD_REFUSAL_MESSAGE,
            "sources": [],
            "is_safe": True
        }


def _fetch_system_instruction() -> str:
    """
    /// <summary>
    /// دریافت system instruction از دیتابیس یا استفاده از متن پیش‌فرض
    /// </summary>
    """
    system_instruction = None
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT prompt FROM system_prompts WHERE key = 'default_system_instruction'")
            row = cur.fetchone()
            if row:
                system_instruction = row[0]
    except Exception as e:
        logger.error(f"Failed to fetch system instruction from DB: {str(e)}")
    finally:
        if conn:
            conn.close()

    if not system_instruction:
        system_instruction = (
            "شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. "
            "هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید."
        )
    return system_instruction


def _answer_without_context(user_input: str, chat_history: list) -> dict:
    """
    /// <summary>
    /// پاسخ‌دهی LLM به سوالات عمومی بدون context (general_chat mode)
    /// </summary>
    /// <remarks>
    /// این تابع زمانی فراخوانی می‌شود که دیتابیس خالی است یا embedding کار نمی‌کند
    /// اما سوال کاربر عمومی/احوال‌پرسی است و نیازی به RAG context ندارد.
    /// </remarks>
    """
    try:
        from app.services.retrieval.query_rewriter import format_chat_history
        llm = get_llm(temperature=0.3)
        formatted_history = format_chat_history(chat_history)

        general_prompt_template = (
            "{system_instruction}\n\n"
            "تاریخچه مکالمه:\n{chat_history}\n\n"
            "پرسش کاربر: {user_input}\n\n"
            "پاسخ:"
        )
        system_instruction = _fetch_system_instruction()
        prompt = PromptTemplate.from_template(general_prompt_template)
        chain = prompt | llm

        response = chain.invoke({
            "system_instruction": system_instruction,
            "chat_history": formatted_history,
            "user_input": user_input,
        })
        answer = response.content.strip()
        if not answer or answer == "####":
            return {"answer": STANDARD_REFUSAL_MESSAGE, "sources": [], "is_safe": True}
        return {"answer": answer, "sources": [], "is_safe": True}
    except Exception as e:
        logger.error(f"General chat LLM call failed: {str(e)}.")
        return {"answer": STANDARD_REFUSAL_MESSAGE, "sources": [], "is_safe": True}


async def synthesize_rag_response_stream(
    user_input: str,
    chat_history: list,
    threshold: float = 0.4,
    k: int = 4,
    file_ids: Optional[list[int]] = None,
) -> AsyncGenerator[dict, None]:
    """
    /// <summary>
    /// نسخه streaming موتور RAG — نتایج را به صورت توکن به توکن (SSE) برمی‌گرداند
    /// </summary>
    /// <remarks>
    /// Routing حذف شده — همه queries از مسیر واحد RAG عبور می‌کنند.
    /// </remarks>
    """
    logger.info("Synthesizer (stream) received query from chat session.")

    standalone_query = rewrite_query(user_input, chat_history)

    vector_results = vector_search_agent.retrieve_context(standalone_query, threshold=threshold, k=k, file_ids=file_ids)
    qna_results = qna_agent.retrieve_context(standalone_query, threshold=threshold, k=k, file_ids=file_ids)
    all_results = vector_results + qna_results
    sorted_results = sorted(all_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]

    if not sorted_results and settings.services.web_search:
        logger.info("Local KB empty in stream. Activating Tavily fallback...")
        web_results = perform_tavily_web_search(standalone_query)
        sorted_results = sorted(web_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]

    if not sorted_results:
        # بررسی اینکه آیا سوال عمومی است
        if _is_general_query(standalone_query):
            logger.info("No RAG context found but query is general (stream). Using general_chat mode.")
            yield {"event": "sources", "data": []}
            async for chunk in _stream_without_context(user_input, chat_history):
                yield chunk
            return

        logger.warning("Zero context in stream mode. Emitting standard refusal.")
        yield {"event": "sources", "data": []}
        yield {"event": "token", "data": STANDARD_REFUSAL_MESSAGE}
        yield {"event": "done", "data": {"is_safe": True}}
        return

    formatted_context_list = []
    sources = []

    active_file_id = None
    if file_ids:
        active_file_id = file_ids[0]
    elif sorted_results:
        active_file_id = sorted_results[0].get("file_id")
        if active_file_id == 0:
            active_file_id = None

    for item in sorted_results:
        clean_content = item["content"].replace(", Answer:", "\nAnswer:")
        formatted_context_list.append(clean_content)
        page_label = f"قطعه {item['sequence_id']}" if item["sequence_id"] else "مخزن داده"
        sources.append({"name": item["label"], "page": page_label})

    context_str = "\n\n".join(formatted_context_list)

    yield {"event": "sources", "data": sources[:3]}

    rules_list = []
    if settings.services.rule_extractor and active_file_id:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rule_code, clause FROM extracted_rules WHERE file_id = %s",
                    (active_file_id,)
                )
                rows = cur.fetchall()
                for row in rows:
                    rules_list.append(f"- {row[0]}: {row[1]}")
        except Exception as e:
            logger.error(f"Failed to fetch rules for stream constraints: {str(e)}")
        finally:
            if conn:
                conn.close()

    compliance_constraints = ""
    if rules_list:
        rules_formatted = "\n    ".join(rules_list)
        compliance_constraints = f"\n    5. Follow these strict corporate COMPLIANCE RULES when answering:\n    {rules_formatted}\n"

    system_instruction = _fetch_system_instruction()

    try:
        llm = get_llm(temperature=0.1)

        from app.services.retrieval.query_rewriter import format_chat_history
        formatted_history = format_chat_history(chat_history)

        prompt = PromptTemplate.from_template(RESPONDER_TEMPLATE)
        chain = prompt | llm

        accumulated = ""
        async for chunk in chain.astream({
            "reranked_text": context_str,
            "chat_history": formatted_history,
            "user_input": user_input,
            "compliance_constraints": compliance_constraints,
            "system_instruction": system_instruction
        }):
            piece = getattr(chunk, "content", None) or ""
            if not piece:
                continue
            accumulated += piece
            yield {"event": "token", "data": piece}

        if accumulated.strip() == "####" or not accumulated.strip():
            logger.warning("Stream responder produced refusal placeholder. Emitting standard refusal.")
            yield {"event": "token", "data": STANDARD_REFUSAL_MESSAGE}

        logger.info("Successfully streamed RAG response.")
        yield {"event": "done", "data": {"is_safe": True}}

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Stream LLM responder failed: {str(e)}. Emitting refusal.")
        yield {"event": "error", "data": str(e)}
        yield {"event": "token", "data": STANDARD_REFUSAL_MESSAGE}
        yield {"event": "done", "data": {"is_safe": True}}


async def _stream_without_context(user_input: str, chat_history: list) -> AsyncGenerator[dict, None]:
    """
    /// <summary>
    /// نسخه streaming پاسخ‌دهی عمومی بدون RAG context
    /// </summary>
    """
    try:
        from app.services.retrieval.query_rewriter import format_chat_history
        llm = get_llm(temperature=0.3)
        formatted_history = format_chat_history(chat_history)
        system_instruction = _fetch_system_instruction()

        general_prompt_template = (
            "{system_instruction}\n\n"
            "تاریخچه مکالمه:\n{chat_history}\n\n"
            "پرسش کاربر: {user_input}\n\n"
            "پاسخ:"
        )
        prompt = PromptTemplate.from_template(general_prompt_template)
        chain = prompt | llm

        accumulated = ""
        async for chunk in chain.astream({
            "system_instruction": system_instruction,
            "chat_history": formatted_history,
            "user_input": user_input,
        }):
            piece = getattr(chunk, "content", None) or ""
            if not piece:
                continue
            accumulated += piece
            yield {"event": "token", "data": piece}

        if not accumulated.strip() or accumulated.strip() == "####":
            yield {"event": "token", "data": STANDARD_REFUSAL_MESSAGE}

        yield {"event": "done", "data": {"is_safe": True}}

    except Exception as e:
        logger.error(f"General chat stream failed: {str(e)}.")
        yield {"event": "token", "data": STANDARD_REFUSAL_MESSAGE}
        yield {"event": "done", "data": {"is_safe": True}}
