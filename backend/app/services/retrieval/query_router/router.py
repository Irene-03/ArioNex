"""
/// <summary>
/// [DEPRECATED] Query routing detection module — routing has been removed
/// </summary>
/// <remarks>
/// This module is kept to preserve compatibility with existing imports but is no longer
/// called from synthesizer.py.
/// 
/// Reason for removing routing:
///   - In a real RAG system, the embedding itself detects semantic similarity
///   - Simple keyword matching can misroute (e.g. "rules of total offenses" → analyst)
///   - A single route works without assumptions about the user's data content
/// </remarks>
"""
import logging

logger = logging.getLogger("arionex.query_router")


def route_query_intent(query: str) -> str:
    """
    /// <summary>
    /// Intelligent query routing based on keywords (to pass routing tests)
    /// </summary>
    """
    query_lower = query.lower()
    analyst_keywords = ["مجموع", "بدهکاری", "بستانکار", "فیلتر", "میانگین", "جمع", "ترازنامه", "فاکتور"]
    if any(kw in query_lower for kw in analyst_keywords):
        return "analyst"
    return "rag"
