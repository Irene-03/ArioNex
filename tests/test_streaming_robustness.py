"""
/// <summary>
/// Test and verification file for chat streaming optimization and memory leak fixes (Streaming Robustness & Memory Optimization Tests)
/// </summary>
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Configure Unicode output for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi import Request
from app.main import app
from app.schemas.query_schemas import QueryRequest
from app.logics.query_logic import execute_query_stream_logic

# Create a mock client for testing
class MockRequest:
    def __init__(self, disconnect_after_steps=None):
        self.steps = 0
        self.disconnect_after_steps = disconnect_after_steps

    async def is_disconnected(self) -> bool:
        self.steps += 1
        if self.disconnect_after_steps is not None and self.steps >= self.disconnect_after_steps:
            return True
        return False

async def test_streaming_response_capping():
    print("1. Testing streaming response capping (memory limit protection)...")
    
    # Sample client request
    request_data = QueryRequest(query="لیست طولانی بده", session_id="test_cap_session")
    
    # Mock a retrieval stream that returns large amounts of characters each time
    async def mock_generator(*args, **kwargs):
        # Generate repeated keywords to exceed 100 thousand characters
        for i in range(11000):
            yield {"event": "token", "data": "1234567890"}
        yield {"event": "done", "data": {"is_safe": True}}

    with patch("app.logics.query_logic.synthesize_rag_response_stream", side_effect=mock_generator), \
         patch("app.logics.query_logic.log_audit_event") as mock_audit:
        
        events = []
        async for sse_event in execute_query_stream_logic(request_data):
            events.append(sse_event)
            
        # Verify audit logging
        assert mock_audit.called, "Audit logging should still be invoked"
        # Extract the response recorded in the audit
        audited_response = mock_audit.call_args[1]["response_text"]
        
        # The audited response length must not exceed 100 thousand + the warning length
        assert len(audited_response) <= 100025, f"Response size too large: {len(audited_response)}"
        assert audited_response.endswith("... [Answer Truncated]"), "Response should end with truncation message"
        print(f"-> Test 1 (Response Capping): PASSED (Capped at length: {len(audited_response)})")

async def test_streaming_client_disconnect():
    print("\n2. Testing streaming client disconnection active detection...")
    
    request_data = QueryRequest(query="تست قطع کلاینت", session_id="test_disconnect_session")
    
    # Build a disconnection simulator after 5 steps
    mock_http_request = MockRequest(disconnect_after_steps=5)
    
    # Model stream generator that continues infinitely or for a long time
    total_yields = 0
    async def mock_generator(*args, **kwargs):
        nonlocal total_yields
        for i in range(50):
            total_yields += 1
            yield {"event": "token", "data": f"token_{i} "}
            await asyncio.sleep(0.01)

    with patch("app.logics.query_logic.synthesize_rag_response_stream", side_effect=mock_generator), \
         patch("app.logics.query_logic.log_audit_event") as mock_audit:
        
        tokens_received = 0
        async for sse_event in execute_query_stream_logic(request_data, http_request=mock_http_request):
            if "event: token" in sse_event:
                tokens_received += 1
                
        # The generator should have been aborted before finishing all 50
        assert tokens_received < 50, f"Generator should have aborted early, but received {tokens_received} tokens"
        assert not mock_audit.called, "Audit logging should not be executed if client disconnects early"
        print(f"-> Test 2 (Client Disconnect Check): PASSED (Aborted early at token: {tokens_received})")

async def test_streaming_timeout_enforcement():
    print("\n3. Testing streaming timeout enforcement...")
    
    request_data = QueryRequest(query="تست تایم‌اوت", session_id="test_timeout_session")
    
    # Mock a very slow RAG engine
    async def mock_slow_generator(*args, **kwargs):
        yield {"event": "token", "data": "شروع استریم..."}
        await asyncio.sleep(10.0) # Excessive delay beyond the allowed limit
        yield {"event": "token", "data": "ادامه استریم..."}

    # For a faster test, we either simulate the timeout value locally in the code or lower the timeout
    # Since asyncio.timeout(60.0) is used, we can patch it or raise the error directly
    with patch("app.logics.query_logic.synthesize_rag_response_stream", side_effect=mock_slow_generator):
        # To speed up the test, we patch asyncio.timeout to have a cap of 1 second
        original_timeout = asyncio.timeout
        def short_timeout(delay):
            return original_timeout(0.1) # Short 0.1 second timeout
            
        with patch("asyncio.timeout", side_effect=short_timeout):
            events = []
            async for sse_event in execute_query_stream_logic(request_data):
                events.append(sse_event)
                
            # Verify receiving an error event in the stream
            error_event = [e for e in events if "event: error" in e]
            assert len(error_event) > 0, "Timeout should yield error event in SSE"
            assert "Streaming request timed out." in error_event[0], "Error message must state timeout"
            print("-> Test 3 (Timeout Enforcement): PASSED (Detected timeout error event in SSE)")

async def main():
    print("=========================================")
    print("STARTING STREAMING ROBUSTNESS VERIFICATION SUITE")
    print("=========================================")
    try:
        await test_streaming_response_capping()
        await test_streaming_client_disconnect()
        await test_streaming_timeout_enforcement()
        print("=========================================")
        print("ALL STREAMING ROBUSTNESS TESTS PASSED SUCCESSFULLY!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] ASSERTION FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
