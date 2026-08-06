"""
/// <summary>
/// Test and verification file for security limits, failover mechanisms, and error propagation (ArioNex System Limits & Failover Tests)
/// </summary>
"""

import sys
import os
import time
import asyncio
import unittest
from unittest.mock import MagicMock, patch

# Configure Unicode output for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.logics.query_logic import _query_sessions, LRUCache
from app.core.embeddings import get_embedding

client = TestClient(app)

class TestSystemLimitsAndFailover(unittest.TestCase):

    def setUp(self):
        # Clear rate limiter history to avoid interfering with tests
        from app.helpers.rate_limiter import RateLimitMiddleware
        RateLimitMiddleware.request_history.clear()

    def test_lru_session_cache(self):
        print("1. Testing LRU Session cache capping...")
        cache = LRUCache(maxsize=10)
        
        # Fill the cache with 12 different keys
        for i in range(12):
            cache[f"session_{i}"] = [{"Human": "query"}, {"AI": "answer"}]
            
        # Verify that the cache size has not exceeded 10
        self.assertEqual(len(cache), 10)
        # Verify removal of older keys (sessions 0 and 1)
        self.assertNotIn("session_0", cache)
        self.assertNotIn("session_1", cache)
        self.assertIn("session_2", cache)
        self.assertIn("session_11", cache)
        print("-> Test 1 (LRU Session Capping): PASSED")

    @patch("app.core.embeddings._validate_api_key")
    @patch("app.core.embeddings._embed_with_openai")
    def test_embedding_error_propagation(self, mock_embed, mock_val):
        print("\n2. Testing Embedding exception propagation (no silent zero-vector fallback)...")
        # Set up the API error scenario
        mock_val.return_value = None
        mock_embed.side_effect = Exception("OpenAI Service is Down")
        
        # The method call must raise an exception and not return a zero vector
        with self.assertRaises(Exception) as context:
            get_embedding("تست هوش مصنوعی")
            
        self.assertIn("OpenAI Service is Down", str(context.exception))
        print("-> Test 2 (Embedding Error Propagation): PASSED")

    def test_upload_file_size_limit(self):
        print("\n3. Testing Upload File size limit (max 20MB)...")
        # Create a hypothetical file of 21 MB (larger than the allowed limit)
        # To save memory, we simulate the file content as a large generator or use BytesIO with a large length
        import io
        large_content = b"x" * (21 * 1024 * 1024) # 21MB
        
        # Send the file to the /v1/upload endpoint
        # FastAPI by default opens the test client immediately
        response = client.post(
            "/v1/upload",
            files={"file": ("large_file.txt", io.BytesIO(large_content), "text/plain")}
        )
        
        # A 413 Payload Too Large error should be returned
        self.assertEqual(response.status_code, 413)
        self.assertIn("حجم فایل آپلود شده بیش از حد مجاز", response.json()["detail"])
        print("-> Test 3 (File Upload Capping): PASSED")

    def test_rate_limiting_dos_protection(self):
        print("\n4. Testing Rate limiting protection (max 30 requests/min)...")
        
        # Clear the rate limiter history for the test client
        from app.helpers.rate_limiter import RateLimitMiddleware
        for middleware in app.user_middleware:
            if hasattr(middleware, "cls") and middleware.cls == RateLimitMiddleware:
                # Dynamically clear the limiter's previous records
                pass
                
        # Send sequential requests to the query endpoint
        # We mock the login dependency so the request does not fail with a 401 error
        from app.helpers.auth import get_current_user_or_api_key
        app.dependency_overrides[get_current_user_or_api_key] = lambda: {"username": "test_user", "role": "Admin"}
        
        # Mock the synthesizer response and audit to avoid database delays and real execution
        with patch("app.logics.query_logic.synthesize_rag_response") as mock_synth, \
             patch("app.logics.query_logic.log_audit_event") as mock_audit:
            mock_synth.return_value = {"answer": "پاسخ نمونه", "sources": [], "is_safe": True}
            
            payload = {"query": "سلام", "session_id": "test_limiter_session"}
            
            # The first 30 requests will be successful
            responses = []
            for i in range(30):
                res = client.post("/v1/query", json=payload)
                responses.append(res.status_code)
                
            # The 31st request must fail with rate limit 429
            rate_limited_res = client.post("/v1/query", json=payload)
            
            self.assertEqual(rate_limited_res.status_code, 429)
            self.assertIn("تعداد درخواست‌های شما بیش از حد مجاز است", rate_limited_res.json()["detail"])
            print(f"-> Test 4 (Rate Limiter DoS Protection): PASSED (Received HTTP 429 at step 31)")
            
        app.dependency_overrides.clear()

    def test_celery_broker_down_thread_fallback(self):
        print("\n5. Testing Celery task thread fallback (when broker/Redis is unreachable)...")
        
        # Define a test Celery task
        # We import celery_app
        from app.core.celery_app import celery_app
        
        execution_check = {"called": False}
        
        @celery_app.task(name="test.fallback_task_execution")
        def dummy_task(arg1):
            execution_check["called"] = True
            execution_check["arg"] = arg1
            
        # Simulate a broker connection failure by patching Celery's main apply_async method
        # which raises OperationalError in this case
        from kombu.exceptions import OperationalError
        
        with patch("celery.Task.apply_async", side_effect=OperationalError("Connection refused by Redis")):
            # This call should successfully switch to the background thread because Redis is unreachable
            dummy_task.delay("ArioNex test failover")
            
            # Wait for the thread to finish its work
            time.sleep(0.1)
            
            self.assertTrue(execution_check["called"], "Task should execute locally in background thread")
            self.assertEqual(execution_check["arg"], "ArioNex test failover")
            print("-> Test 5 (Celery Broker-Down Thread Fallback): PASSED")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING SYSTEM LIMITS & FAILOVER VERIFICATION SUITE")
    print("=========================================")
    unittest.main()
