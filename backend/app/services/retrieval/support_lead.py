"""
/// <summary>
/// Support lead agent backward compatibility layer (ArioNex Support Lead Agent Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// This file was created to preserve compatibility with the test suites of previous phases
/// and forwards requests to the new qna module.
/// </remarks>
"""

from app.services.retrieval.qna import qna_agent as support_lead_agent
