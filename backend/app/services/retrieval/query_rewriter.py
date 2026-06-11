"""
/// <summary>
/// ماژول بازنویسی مستقل پرسش‌ها بر اساس تاریخچه چت (Standalone Query Rewriter Chain)
/// </summary>
/// <remarks>
/// این ماژول تاریخچه چت گذشته را خوانده و با ترکیب پرسش جدید کاربر، یک پرسش مستقل (Standalone)
/// تولید می‌کند تا ابهامات ارجاعی در چت‌های متوالی (مانند کلمات ضمیر "آن"، "این" و...) مرتفع گردند.
/// در صورت نامعتبر بودن کلید OpenAI API، سیستم به عنوان زاپاس عین پرسش کاربر را برمی‌گرداند.
/// </remarks>
"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings

logger = logging.getLogger("arionex.query_rewriter")

# الگو پرامپت بازنویسی مستقل بر اساس دموی prompts.py
STANDALONE_TEMPLATE = """You are an assistant that rewrite the **User Input** to be independent of any prior chat history.

Given the following chat history and the latest **User Input**, rewrite the question while preserving its context.

**Chat History:**
{chat_history}

**User Input:**:
{user_input}

Rewritten standalone question:
"""

def format_chat_history(history: list) -> str:
    """
    /// <summary>
    /// قالب‌بندی تاریخچه مکالمه به رشته متنی مناسب برای مدل هوشمند
    /// </summary>
    /// <param name="history">لیستی از پیام‌ها به صورت دیکشنری یا نمونه کلاس‌ها</param>
    /// <returns>یک رشته متنی ساختاریافته</returns>
    """
    if not history:
        return "No prior history."
        
    formatted = []
    for msg in history:
        if isinstance(msg, dict):
            for role, content in msg.items():
                formatted.append(f"{role}: {content}")
        elif hasattr(msg, 'type') and hasattr(msg, 'content'):
            role = "AI" if msg.type == "ai" else "Human"
            formatted.append(f"{role}: {msg.content}")
        else:
            formatted.append(f"Message: {str(msg)}")
            
    return "\n".join(formatted)

def rewrite_query(user_input: str, chat_history: list) -> str:
    """
    /// <summary>
    /// بازنویسی هوشمند پرسش کاربر بر اساس تاریخچه مکالمات گذشته
    /// </summary>
    /// <param name="user_input">پرسش جدید کاربر</param>
    /// <param name="chat_history">لیست پیام‌های گذشته</param>
    /// <returns>پرسش مستقل و بازنویسی شده نهایی</returns>
    """
    if not chat_history:
        return user_input
        
    # در صورت عدم وجود کلید واقعی، برای ممانعت از کرش از بازنویسی صرف نظر کرده و خود ورودی را برمی‌گردانیم
    if not settings.openai_api_key:
        logger.info("OpenAI API key is not configured. Skipping query rewriting and returning original user query.")
        return user_input
        
    try:
        llm = ChatOpenAI(
            model_name=settings.model_name,
            temperature=0,
            openai_api_key=settings.openai_api_key
        )
        
        prompt = PromptTemplate.from_template(STANDALONE_TEMPLATE)
        chain = prompt | llm
        
        formatted_history = format_chat_history(chat_history)
        response = chain.invoke({
            "chat_history": formatted_history,
            "user_input": user_input
        })
        
        rewritten = response.content.strip()
        logger.info(f"Query rewritten successfully. Original: '{user_input}' -> Rewritten: '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.error(f"Failed to rewrite query via OpenAI: {str(e)}. Using original query as fallback.")
        return user_input
