"""
/// <summary>
/// Librarian agent backward compatibility layer (ArioNex Librarian Agent Backward Compatibility Layer)
/// </summary>
/// <remarks>
/// This file was created to preserve compatibility with the test suites of previous phases
/// and forwards requests to the new vector_search module.
/// </remarks>
"""

from app.services.retrieval.vector_search import vector_search_agent as librarian_agent
