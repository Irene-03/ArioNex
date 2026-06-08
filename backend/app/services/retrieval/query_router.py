"""
/// <summary>
/// موتور مرکزی مسیریابی، بازیابی، رتبه‌بندی مجدد و پاسخ‌دهی RAG (ArioNex Query Router & Synthesizer)
/// </summary>
/// <remarks>
/// این ماژول قلب تپنده خواندن (Read Path) سیستم RAG است. وظیفه روت کردن پرسش‌ها بر اساس
/// کلمات کلیدی، استخراج داده‌ها از عامل‌های vector_search و qna، رتبه‌بندی مجدد (Reranking)
/// بر اساس امتیاز شباهت کسینوسی، فراخوانی Tavily Web Search در صورت فعال بودن به عنوان منبع زنده زاپاس،
/// و اعمال قانون طلایی عدم توهم (Non-Hallucination Refusal) را بر عهده دارد.
/// </remarks>
"""

import logging
import re
from typing import Optional
import requests
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.core.database import get_db_connection
from app.prompts.rag_prompts import RESPONDER_TEMPLATE, STANDARD_REFUSAL_MESSAGE
from app.services.retrieval.query_rewriter import rewrite_query
from app.services.retrieval.vector_search import vector_search_agent
from app.services.retrieval.qna import qna_agent
from app.services.retrieval.analyst import analyst_agent
from app.services.retrieval.investigator import investigator_agent
from app.services.retrieval.lawyer import lawyer_agent

logger = logging.getLogger("arionex.query_router")


def route_query_intent(query: str) -> str:
    """
    /// <summary>
    /// تعیین هوشمند مسیر جستجو بر اساس کلیدواژه‌های پرسش
    /// </summary>
    /// <param name="query">پرسش مستقل کاربر</param>
    /// <returns>رشته‌ای نشان‌دهنده دسته‌بندی مسیر ('analyst' یا 'rag')</returns>
    """
    query_lower = query.lower()
    
    # کلمات کلیدی محاسباتی، جداول، حسابداری و آماری مالی
    structured_keywords = [
        "بدهکار", "بستانکار", "مجموع", "میانگین", "سند", "حساب", "چک", 
        "فاکتور", "تعداد تیکت", "groupby", "جمع ستون", "تراکنش"
    ]
    
    for kw in structured_keywords:
        if kw in query_lower:
            return "analyst"
            
    return "rag"

def perform_tavily_web_search(query: str) -> list[dict]:
    """
    /// <summary>
    /// فراخوانی جستجوی وب زنده با Tavily API در صورت فعال بودن در سیستم
    /// </summary>
    /// <param name="query">پرسش کاربر</param>
    /// <returns>لیستی از نتایج وب بازیابی شده</returns>
    """
    if not settings.services.web_search or not settings.tavily_api_key or "your-tavily" in settings.tavily_api_key:
        logger.info("Tavily Web Search is disabled or API Key is missing. Skipping web search.")
        return []
        
    logger.info(f"Initiating live Tavily web search for: '{query}'...")
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False
        }
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            web_results = []
            for item in data.get("results", []):
                web_results.append({
                    "content": item.get("content", ""),
                    "label": f"Web Source: {item.get('title', 'External Page')}",
                    "file_id": 999, # شناسه ثابت برای منابع وب جهت ردیابی متادیتای فرانت‌اند
                    "sequence_id": 0,
                    "similarity": 0.65, # امتیاز شباهت ثابت برای منابع وب
                    "source_type": "web"
                })
            logger.info(f"Tavily search retrieved {len(web_results)} pages.")
            return web_results
    except Exception as e:
        logger.error(f"Tavily Web Search API request failed: {str(e)}")
        
    return []

def synthesize_rag_response(user_input: str, chat_history: list, threshold: float = 0.4, k: int = 4, file_ids: Optional[list[int]] = None) -> dict:
    """
    /// <summary>
    /// هماهنگ‌کننده نهایی زنجیره خواندن RAG: بازنویسی، روت، بازیابی، رتبه‌بندی مجدد، پیوند گراف دانش، و ممیزی انطباق قوانین
    /// </summary>
    /// <param name="user_input">پرسش جدید کاربر</param>
    /// <param name="chat_history">تاریخچه چت نشست جاری</param>
    /// <param name="threshold">آستانه شباهت بردارها</param>
    /// <param name="k">تعداد چانک‌های نهایی استنادی</param>
    /// <param name="file_ids">شناسه‌های فایل فیلترکننده (اختیاری)</param>
    /// <returns>دیکشنری شامل پاسخ نهایی، منابع استفاده‌شده و وضعیت ایمنی</returns>
    """
    logger.info(f"Synthesizer received query from chat session.")
    
    # ۱. بازنویسی پرسش بر اساس تاریخچه چت جهت رفع ابهام
    standalone_query = rewrite_query(user_input, chat_history)
    
    # ۲. روت کردن پرسش به عامل محاسباتی یا RAG اسناد
    intent = route_query_intent(standalone_query)
    logger.info(f"Routed query intent category: '{intent}'")
    
    # سناریو الف: اگر کوئری محاسباتی و مربوط به جداول پانداس باشد
    if intent == "analyst":
        analysis_result = analyst_agent.execute_analysis(standalone_query)
        
        # بررسی اینکه آیا پاسخ با شکست مواجه شده است
        if "DOUBTFUL ANSWER" in analysis_result:
            logger.warning("Analyst Agent failed to resolve the question with certainty. Falling back to document vector search.")
            # سوییچ خودکار به سرچ متنی اسناد به عنوان زاپاس
        else:
            # بررسی قانون عدم توهم
            if not analysis_result.strip() or analysis_result == "####":
                return {
                    "answer": STANDARD_REFUSAL_MESSAGE,
                    "sources": [],
                    "is_safe": True
                }
            return {
                "answer": analysis_result,
                "sources": [{"name": "accounting_data.csv", "page": "تحلیل آماری حسابداری"}],
                "is_safe": True
            }

    # سناریو ب: موتور بازیابی RAG برداری اسناد
    # بازیابی نتایج از عامل جستجوی برداری اسناد (vector_search) و عامل پرسش‌وپاسخ (qna)
    vector_results = vector_search_agent.retrieve_context(standalone_query, threshold=threshold, k=k, file_ids=file_ids)
    qna_results = qna_agent.retrieve_context(standalone_query, threshold=threshold, k=k)
    
    # تجمیع نتایج محلی
    all_results = vector_results + qna_results
    
    # مرتب‌سازی مجدد (Reranking) بر اساس امتیاز شباهت کسینوسی به صورت نزولی
    sorted_results = sorted(all_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]
    
    # ۳. در صورتی که دیتای محلی کافی نباشد، جستجوی زنده وب را به عنوان بک‌آپ فراخوانی می‌کنیم (اگر فعال باشد)
    if not sorted_results and settings.services.web_search:
        logger.info("Local knowledge base yields zero matches. Activating Tavily fallback search...")
        web_results = perform_tavily_web_search(standalone_query)
        sorted_results = sorted(web_results, key=lambda x: x.get("similarity", 0), reverse=True)[:k]

    # ۴. قانون طلایی عدم توهم: اگر هیچ دیتایی بالا نیاید، بلافاصله متن امتناع استاندارد را بازمی‌گردانیم
    if not sorted_results:
        logger.warning("Zero relevant context retrieved across all agents. Refusing to answer to prevent hallucination.")
        return {
            "answer": STANDARD_REFUSAL_MESSAGE,
            "sources": [],
            "is_safe": True
        }

    # استخراج شناسه سند جهت فیلتر و ممیزی اختصاصی قوانین و گراف دانش
    active_file_id = None
    if file_ids:
        active_file_id = file_ids[0]
    elif sorted_results:
        # استفاده از آیدی اولین قطعه بازیابی شده به عنوان فایل فعال
        active_file_id = sorted_results[0].get("file_id")
        if active_file_id == 0:
            active_file_id = None
        
    # ۵. قالب‌بندی نتایج برای ارسال به مدل Responder
    formatted_context_list = []
    sources = []
    
    # الف. الحاق کانتکست گرافی در صورت وجود (The Investigator)
    graph_context = investigator_agent.retrieve_graph_context(standalone_query, active_file_id)
    if graph_context:
        formatted_context_list.append(graph_context)
    
    for item in sorted_results:
        content = item["content"]
        label = item["label"]
        seq_id = item["sequence_id"]
        
        # اصلاح فرمت برای راحتی خواندن
        clean_content = content.replace(", Answer:", "\nAnswer:")
        formatted_context_list.append(clean_content)
        
        # جمع‌آوری منابع استنادی
        page_label = f"قطعه {seq_id}" if seq_id else "مخزن داده"
        sources.append({
            "name": label,
            "page": page_label
        })
        
    context_str = "\n\n".join(formatted_context_list)
    
    # ب. استخراج و تزریق قوانین به پرامپت جهت هدایت همزمان مدل اصلی (The Lawyer Constraint Injection)
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
    
    # بررسی mock mode: در صورت عدم وجود کلید واقعی برای provider فعال
    active_provider = settings.llm_provider
    active_key = (
        settings.openrouter_api_key if active_provider == "openrouter"
        else settings.openai_api_key
    )
    if not active_key or active_key in ("mock_key", "") or "your-" in active_key:
        logger.warning("Mock mode active in Query Router. Simulating LLM response based on context.")
        # بازگرداندن چانک بازیابی شده اول به عنوان پاسخ شبیه‌سازی شده
        mock_response = f"بر اساس گزارش موجود در {sources[0]['name']}: \n{sorted_results[0]['content'][:150]}..."
        
        # اجرای ممیزی انطباق قوانین توسط عامل Lawyer
        audit_result = lawyer_agent.audit_compliance(standalone_query, mock_response, active_file_id)
        if not audit_result.get("is_compliant", True):
            logger.warning(f"Lawyer Agent detected compliance violations in Mock response. Blocking response.")
            return {
                "answer": STANDARD_REFUSAL_MESSAGE,
                "sources": [],
                "is_safe": False
            }
            
        if audit_result.get("audit_report"):
            mock_response += f"\n\n⚖️ **گزارش انطباق قوانین (ArioNex Lawyer Audit):**\n*{audit_result['audit_report']}*"
            
        return {
            "answer": mock_response,
            "sources": sources[:2],
            "is_safe": True
        }
        
    # ۶. فراخوانی مدل نهایی Responder از طریق LLM Factory
    try:
        llm = get_llm(temperature=0.1)
        
        # تبدیل تاریخچه چت به ساختار متنی روان برای پرامپت
        from app.services.retrieval.query_rewriter import format_chat_history
        formatted_history = format_chat_history(chat_history)
        
        prompt = PromptTemplate.from_template(RESPONDER_TEMPLATE)
        chain = prompt | llm
        
        response = chain.invoke({
            "reranked_text": context_str,
            "chat_history": formatted_history,
            "user_input": user_input,
            "compliance_constraints": compliance_constraints
        })
        
        final_answer = response.content.strip()
        
        # ۷. قانون عدم توهم در خروجی مدل (بررسی مقدار ویژه ####)
        if final_answer == "####" or not final_answer:
            logger.warning("Responder LLM outputted refusal placeholder '####'. Emitting standard Persian refusal.")
            return {
                "answer": STANDARD_REFUSAL_MESSAGE,
                "sources": [],
                "is_safe": True
            }
            
        # اجرای ممیزی انطباق قوانین توسط عامل Lawyer
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
            "sources": sources[:3], # محدود کردن استناد به ۳ مورد برجسته
            "is_safe": True
        }
        
    except Exception as e:
        logger.error(f"Final LLM responder synthesis failed: {str(e)}. Emitting refusal.")
        return {
            "answer": STANDARD_REFUSAL_MESSAGE,
            "sources": [],
            "is_safe": True
        }
