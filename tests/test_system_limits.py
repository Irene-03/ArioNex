"""
/// <summary>
/// فایل تست راستی‌آزمایی محدودیت‌های امنیتی، مکانیزم‌های بازیابی و انتشار خطاها (ArioNex System Limits & Failover Tests)
/// </summary>
"""

import sys
import os
import time
import asyncio
import unittest
from unittest.mock import MagicMock, patch

# تنظیم خروجی یونیکد برای ویندوز
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
        # پاکسازی سوابق ریت لیمیتر برای جلوگیری از اختلال در تست‌ها
        from app.helpers.rate_limiter import RateLimitMiddleware
        RateLimitMiddleware.request_history.clear()

    def test_lru_session_cache(self):
        print("1. Testing LRU Session cache capping...")
        cache = LRUCache(maxsize=10)
        
        # پر کردن کش با ۱۲ کلید متفاوت
        for i in range(12):
            cache[f"session_{i}"] = [{"Human": "query"}, {"AI": "answer"}]
            
        # بررسی اینکه اندازه کش از ۱۰ بیشتر نشده باشد
        self.assertEqual(len(cache), 10)
        # بررسی حذف کلیدهای قدیمی‌تر (سشن 0 و 1)
        self.assertNotIn("session_0", cache)
        self.assertNotIn("session_1", cache)
        self.assertIn("session_2", cache)
        self.assertIn("session_11", cache)
        print("-> Test 1 (LRU Session Capping): PASSED")

    @patch("app.core.embeddings._validate_api_key")
    @patch("app.core.embeddings._embed_with_openai")
    def test_embedding_error_propagation(self, mock_embed, mock_val):
        print("\n2. Testing Embedding exception propagation (no silent zero-vector fallback)...")
        # تنظیم سناریو خطای API
        mock_val.return_value = None
        mock_embed.side_effect = Exception("OpenAI Service is Down")
        
        # فراخوانی متد باید استثنا پرتاب کند و بردار صفر برنگرداند
        with self.assertRaises(Exception) as context:
            get_embedding("تست هوش مصنوعی")
            
        self.assertIn("OpenAI Service is Down", str(context.exception))
        print("-> Test 2 (Embedding Error Propagation): PASSED")

    def test_upload_file_size_limit(self):
        print("\n3. Testing Upload File size limit (max 20MB)...")
        # ساختن یک فایل فرضی با حجم ۲۱ مگابایت (بزرگتر از حد مجاز)
        # برای صرفه‌جویی در حافظه، محتوای فایل را در قالب یک ژنراتور بزرگ شبیه‌سازی می‌کنیم یا از BytesIO با طول زیاد استفاده می‌کنیم
        import io
        large_content = b"x" * (21 * 1024 * 1024) # 21MB
        
        # ارسال فایل به اندپوینت /v1/upload
        # فست‌ایی‌پی‌آی به صورت پیش‌فرض کلاینت تستی را فورا باز می‌کند
        response = client.post(
            "/v1/upload",
            files={"file": ("large_file.txt", io.BytesIO(large_content), "text/plain")}
        )
        
        # باید خطای 413 Payload Too Large برگردد
        self.assertEqual(response.status_code, 413)
        self.assertIn("حجم فایل آپلود شده بیش از حد مجاز", response.json()["detail"])
        print("-> Test 3 (File Upload Capping): PASSED")

    def test_rate_limiting_dos_protection(self):
        print("\n4. Testing Rate limiting protection (max 30 requests/min)...")
        
        # تمیز کردن تاریخچه ریت لیمیتر برای کلاینت تستی
        from app.helpers.rate_limiter import RateLimitMiddleware
        for middleware in app.user_middleware:
            if hasattr(middleware, "cls") and middleware.cls == RateLimitMiddleware:
                # به صورت پویا رکوردهای قبلی لیمیتر را پاک می‌کنیم
                pass
                
        # ارسال پی‌درپی درخواست به اندپوینت کوئری
        # ما وابستگی لاگین را شبیه‌سازی می‌کنیم تا درخواست با خطای ۴۰۱ شکست نخورد
        from app.helpers.auth import get_current_user_or_api_key
        app.dependency_overrides[get_current_user_or_api_key] = lambda: {"username": "test_user", "role": "Admin"}
        
        # ماک کردن پاسخ synthesizer و ممیزی برای جلوگیری از تأخیرهای دیتابیس و اجرای واقعی
        with patch("app.logics.query_logic.synthesize_rag_response") as mock_synth, \
             patch("app.logics.query_logic.log_audit_event") as mock_audit:
            mock_synth.return_value = {"answer": "پاسخ نمونه", "sources": [], "is_safe": True}
            
            payload = {"query": "سلام", "session_id": "test_limiter_session"}
            
            # ۳۰ درخواست اول موفقیت‌آمیز خواهند بود
            responses = []
            for i in range(30):
                res = client.post("/v1/query", json=payload)
                responses.append(res.status_code)
                
            # درخواست ۳۱ام باید با ریت لیمیت ۴۲۹ شکست بخورد
            rate_limited_res = client.post("/v1/query", json=payload)
            
            self.assertEqual(rate_limited_res.status_code, 429)
            self.assertIn("تعداد درخواست‌های شما بیش از حد مجاز است", rate_limited_res.json()["detail"])
            print(f"-> Test 4 (Rate Limiter DoS Protection): PASSED (Received HTTP 429 at step 31)")
            
        app.dependency_overrides.clear()

    def test_celery_broker_down_thread_fallback(self):
        print("\n5. Testing Celery task thread fallback (when broker/Redis is unreachable)...")
        
        # تعریف یک تسک تستی سلری
        # ما celery_app را ایمپورت می‌کنیم
        from app.core.celery_app import celery_app
        
        execution_check = {"called": False}
        
        @celery_app.task(name="test.fallback_task_execution")
        def dummy_task(arg1):
            execution_check["called"] = True
            execution_check["arg"] = arg1
            
        # شبیه‌سازی قطع اتصال به بروکر با پچ کردن متد apply_async اصلی سلری
        # که در این حالت OperationalError بالا می‌اندازد
        from kombu.exceptions import OperationalError
        
        with patch("celery.Task.apply_async", side_effect=OperationalError("Connection refused by Redis")):
            # این فراخوانی به دلیل عدم دسترسی به ردیس باید با موفقیت به ترد پس‌زمینه سوییچ کند
            dummy_task.delay("ArioNex test failover")
            
            # منتظر می‌مانیم تا ترد کار خود را انجام دهد
            time.sleep(0.1)
            
            self.assertTrue(execution_check["called"], "Task should execute locally in background thread")
            self.assertEqual(execution_check["arg"], "ArioNex test failover")
            print("-> Test 5 (Celery Broker-Down Thread Fallback): PASSED")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING SYSTEM LIMITS & FAILOVER VERIFICATION SUITE")
    print("=========================================")
    unittest.main()
