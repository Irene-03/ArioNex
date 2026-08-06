"""
/// <summary>
/// Module for rewriting questions as standalone based on chat history (Standalone Query Rewriter Chain)
/// </summary>
/// <remarks>
/// This module reads the past chat history and, combined with the user's new question, produces a standalone
/// question to resolve referential ambiguities in consecutive chats (such as the pronoun words "it", "this", etc.).
/// If the OpenAI API key is invalid, the system falls back to returning the user's question verbatim.
/// </remarks>
"""

import logging
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from app.core.llm_factory import get_llm
from app.services.retrieval.query_router.web_search import _get_active_api_key

logger = logging.getLogger("arionex.query_rewriter")

# Standalone rewriting prompt template based on the prompts.py demo
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
    /// Format the conversation history into a text string suitable for the language model
    /// </summary>
    /// <param name="history">List of messages as dicts or class instances</param>
    /// <returns>A structured text string</returns>
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
    /// Intelligently rewrite the user's question based on past conversation history
    /// </summary>
    /// <param name="user_input">User's new question</param>
    /// <param name="chat_history">List of past messages</param>
    /// <returns>Final rewritten standalone question</returns>
    """
    if not chat_history:
        return user_input

    # Check the API key for the system's active provider (not just OpenAI)
    active_provider = settings.llm_provider
    active_key = _get_active_api_key(active_provider)
    if not active_key or active_key.strip() == "" or "your-" in active_key:
        logger.info(
            f"Active LLM provider '{active_provider}' has no valid API key. "
            "Skipping query rewriting and returning original user query."
        )
        return user_input

    try:
        # Use the get_llm factory — supports any active provider
        llm = get_llm(temperature=0)

        prompt = PromptTemplate.from_template(STANDALONE_TEMPLATE)
        chain = prompt | llm

        formatted_history = format_chat_history(chat_history)
        response = chain.invoke({
            "chat_history": formatted_history,
            "user_input": user_input
        })

        rewritten = response.content.strip()
        logger.info(f"Query rewritten successfully via '{active_provider}'. Original: '{user_input}' -> Rewritten: '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.error(f"Failed to rewrite query via '{active_provider}': {str(e)}. Using original query as fallback.")
        return user_input
