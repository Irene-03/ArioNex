"""
/// <summary>
/// ArioNex query router and synthesizer facade file (ArioNex Query Router Facade)
/// </summary>
/// <remarks>
/// This module exists for backward compatibility and forwards imports to the organized query_router package.
/// </remarks>
"""

from app.services.retrieval.query_router import (
    route_query_intent,
    perform_tavily_web_search,
    synthesize_rag_response,
    synthesize_rag_response_stream
)
