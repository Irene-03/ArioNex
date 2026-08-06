"""
/// <summary>
/// Automated test and verification file for LLM factory errors and the propagation of unconfigured keys (LLM Factory Error Handling Tests)
/// </summary>
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.retrieval.query_router import synthesize_rag_response

client = TestClient(app)

def test_synthesizer_propagates_value_error():
    print("1. Testing synthesizer propagates ValueErrors from LLM Factory...")
    
    # Save active settings
    original_provider = settings.llm_provider
    original_key = settings.openai_api_key
    
    try:
        # Force provider to openai and unset key to trigger ValueError inside get_llm
        settings.llm_provider = "openai"
        settings.openai_api_key = ""  # Empty API key triggers ValueError in _warn_if_mock
        
        # We mock vector search and qna agents to return mock document retrieval
        mock_retrieval = [
            {"content": "محتوای سند مرخصی کارمندان.", "label": "leave_policy.pdf", "sequence_id": 1, "similarity": 0.8, "file_id": 1}
        ]
        
        with patch("app.services.retrieval.query_router.synthesizer.vector_search_agent.retrieve_context", return_value=mock_retrieval), \
             patch("app.services.retrieval.query_router.synthesizer.qna_agent.retrieve_context", return_value=[]), \
             patch("app.services.retrieval.query_router.synthesizer.investigator_agent.retrieve_graph_context", return_value=None):
            
            try:
                synthesize_rag_response(
                    user_input="قوانین مرخصی چیست؟",
                    chat_history=[],
                    threshold=0.4,
                    k=1
                )
                assert False, "Synthesizer must raise ValueError when API key is missing instead of swallowing it!"
            except ValueError as ve:
                assert "کلید API برای پروایدر" in str(ve), "Should propagate the specific get_llm ValueError message"
                print(f"-> Test 1 (ValueError Propagation): PASSED (Caught: {str(ve)})")
                
    finally:
        settings.llm_provider = original_provider
        settings.openai_api_key = original_key

def test_fastapi_query_returns_400_on_value_error():
    print("\n2. Testing FastAPI POST /v1/query returns HTTP 400 Bad Request on ValueError...")
    
    # Setup mock user auth dependency override
    from app.helpers.auth import get_current_user_or_api_key
    app.dependency_overrides[get_current_user_or_api_key] = lambda: {"username": "test_user", "role": "Admin"}
    
    original_provider = settings.llm_provider
    original_key = settings.openai_api_key
    
    try:
        settings.llm_provider = "openai"
        settings.openai_api_key = "your-openai-api-key" # triggers ValueError due to 'your-' placeholder
        
        mock_retrieval = [
            {"content": "سند تراکنش‌های بانکی", "label": "accounting.csv", "sequence_id": 1, "similarity": 0.9, "file_id": 2}
        ]
        
        with patch("app.logics.query_logic.synthesize_rag_response") as mock_synth:
            # Emulate the ValueError raised by synthesize_rag_response
            mock_synth.side_effect = ValueError("کلید API برای پروایدر 'OpenAI' تنظیم نشده است.")
            
            payload = {
                "query": "ترازنامه مالی شرکت چقدر است؟",
                "session_id": "test_error_session"
            }
            
            response = client.post("/v1/query", json=payload)
            
            # Assert response code is 400 Bad Request and contains clear Persian error message
            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "کلید API برای پروایدر" in error_data["detail"]
            print(f"-> Test 2 (HTTP 400 Response): PASSED (Response detail: {error_data['detail']})")
            
    finally:
        app.dependency_overrides.clear()
        settings.llm_provider = original_provider
        settings.openai_api_key = original_key

def test_fastapi_query_stream_returns_error_event_on_value_error():
    print("\n3. Testing FastAPI POST /v1/query/stream returns error event on ValueError...")
    
    # Setup mock user auth dependency override
    from app.helpers.auth import get_current_user_or_api_key
    app.dependency_overrides[get_current_user_or_api_key] = lambda: {"username": "test_user", "role": "Admin"}
    
    original_provider = settings.llm_provider
    original_key = settings.openai_api_key
    
    try:
        settings.llm_provider = "openai"
        settings.openai_api_key = "your-openai-api-key" # triggers ValueError
        
        # We mock synthesize_rag_response_stream to raise ValueError
        with patch("app.logics.query_logic.synthesize_rag_response_stream") as mock_synth_stream:
            async def mock_generator(*args, **kwargs):
                raise ValueError("کلید API برای پروایدر 'OpenAI' تنظیم نشده است.")
                # We need a yield to make it an async generator
                if False:
                    yield {}
                
            mock_synth_stream.side_effect = mock_generator
            
            payload = {
                "query": "ترازنامه مالی شرکت چقدر است؟",
                "session_id": "test_stream_error_session"
            }
            
            response = client.post("/v1/query/stream", json=payload)
            assert response.status_code == 200
            
            # Read SSE stream content
            sse_content = response.text
            assert "event: error" in sse_content
            assert "کلید API برای پروایدر" in sse_content
            print("-> Test 3 (HTTP Stream Error Event): PASSED (SSE Event contains expected error event)")
            
    finally:
        app.dependency_overrides.clear()
        settings.llm_provider = original_provider
        settings.openai_api_key = original_key

def main():
    print("=========================================")
    print("STARTING LLM FACTORY ERROR HANDLING VERIFICATION SUITE")
    print("=========================================")
    try:
        test_synthesizer_propagates_value_error()
        test_fastapi_query_returns_400_on_value_error()
        test_fastapi_query_stream_returns_error_event_on_value_error()
        print("=========================================")
        print("ALL LLM FACTORY ERROR TESTS PASSED SUCCESSFULLY!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
