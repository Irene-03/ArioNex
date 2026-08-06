"""
/// <summary>
/// Response synthesizer backward compatibility layer (ArioNex Synthesizer Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// This file was created to preserve compatibility with previous-phase code and system tests
/// and forwards requests to the new query_router module.
/// </remarks>
"""

from app.services.retrieval.query_router import route_query_intent, synthesize_rag_response
from app.prompts.rag_prompts import STANDARD_REFUSAL_MESSAGE
