"""
/// <summary>
/// موتور متمرکز تجمیع، رتبه‌بندی مجدد و پاسخ‌دهی امن - ترکیب‌کننده (The Central Retrieval Synthesizer & Reranker)
/// </summary>
/// <remarks>
/// این ماژول قلب تپنده خواندن (Read Path) سیستم RAG است. وظیفه روت کردن پرسش‌ها بر اساس
/// کلمات کلیدی، استخراج داده‌ها از عامل‌های Librarian و Support Lead، رتبه‌بندی مجدد (Reranking)
/// بر اساس امتیاز شباهت کسینوسی، فراخوانی Tavily Web Search در صورت فعال بودن به عنوان منبع زنده زاپاس،
/// و اعمال قانون طلایی عدم توهم (Non-Hallucination Refusal) را بر عهده دارد.
/// </remarks>
"""

import logging
import re
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.services.retrieval.query_rewriter import rewrite_query
from app.services.retrieval.librarian import librarian_agent
from app.services.retrieval.support_lead import support_lead_agent
from app.services.retrieval.analyst import analyst_agent

logger = logging.getLogger("arionex.synthesizer")

# پرامپت پاسخ‌دهنده نهایی با استناد به منابع بر اساس دموی prompts.py
RESPONDER_TEMPLATE = """You're a responder assistant designed to provide professional answers using the CONTEXT below.

Key instructions for the AI assistant:
    1. Use the below CONTEXT (delimited with XML tags) to answer the QUESTION.
    2. If CONTEXT does not provide enough information to answer the QUESTION, the output must be exactly the four characters: "####"
    3. Don't try to make up an answer.
    4. Respond in Persian.

<CONTEXT>
{reranked_text}
</CONTEXT>

Conversation history (retain a concise summary of context to avoid repetition or contradictions):
{chat_history}

QUESTION:
{user_input}

AI Assistant Response:
"""

# متن امتناع استاندارد طلایی فارسی برای جلوگیری از توهم RAG
STANDARD_REFUSAL_MESSAGE = "منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند."

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

def synthesize_rag_response(user_input: str, chat_history: list, threshold: float = 0.4, k: int = 4) -> dict:
    """
    /// <summary>
    /// هماهنگ‌کننده نهایی زنجیره خواندن RAG: بازنویسی، روت، بازیابی، رتبه‌بندی مجدد و قانون عدم توهم
    /// </summary>
    /// <param name="user_input">پرسش جدید کاربر</param>
    /// <param name="chat_history">تاریخچه چت نشست جاری</param>
    /// <param name="threshold">آستانه شباهت بردارها</param>
    /// <param name="k">تعداد چانک‌های نهایی استنادی</param>
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
    # بازیابی نتایج از عامل‌های کتابدار (Librarian) و سرپرست پشتیبانی (Support Lead)
    librarian_results = librarian_agent.retrieve_context(standalone_query, threshold=threshold, k=k)
    support_results = support_lead_agent.retrieve_context(standalone_query, threshold=threshold, k=k)
    
    # تجمیع نتایج محلی
    all_results = librarian_results + support_results
    
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
        
    # ۵. قالب‌بندی نتایج برای ارسال به مدل Responder
    formatted_context_list = []
    sources = []
    
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
    
    # در صورت عدم وجود کلید واقعی OpenAI، شبیه‌سازی RAG محلی می‌کنیم تا برنامه برای تست کار کند
    if not settings.openai_api_key or settings.openai_api_key == "mock_key" or "your-openai-key" in settings.openai_api_key:
        logger.warning("Mock mode active in Synthesizer. Simulating LLM response based on context.")
        # بازگرداندن چانک بازیابی شده اول به عنوان پاسخ شبیه‌سازی شده
        mock_response = f"بر اساس گزارش موجود در {sources[0]['name']}: \n{formatted_context_list[0][:150]}..."
        return {
            "answer": mock_response,
            "sources": sources[:2],
            "is_safe": True
        }
        
    # ۶. فراخوانی مدل نهایی Responder
    try:
        llm = ChatOpenAI(
            model_name=settings.model_name,
            temperature=0.1, # لتنسی کم و تمایل بسیار کم به توهم
            openai_api_key=settings.openai_api_key
        )
        
        # تبدیل تاریخچه چت به ساختار متنی روان برای پرامپت
        from app.services.retrieval.query_rewriter import format_chat_history
        formatted_history = format_chat_history(chat_history)
        
        prompt = PromptTemplate.from_template(RESPONDER_TEMPLATE)
        chain = prompt | llm
        
        response = chain.invoke({
            "reranked_text": context_str,
            "chat_history": formatted_history,
            "user_input": user_input
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
