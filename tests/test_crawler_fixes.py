"""
/// <summary>
/// فایل راستی‌آزمایی تغییرات و اصلاحات موتور کرالر وب (Web Crawler Fixes Verification Script)
/// </summary>
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# اضافه کردن مسیر پروژه جهت شناسایی پکیج app
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.services.workers.crawler.engine import CrawlerService
from app.core.config import settings

async def test_crawler_service():
    print("1. Testing CrawlerService initialization...")
    service = CrawlerService()
    assert service.is_enabled is not None
    print(f"CrawlerService is_enabled: {service.is_enabled}")
    
    print("\n2. Testing run_crawl_job validation and subprocess logic...")
    
    # Test 1: Disabled service check
    with patch("app.services.workers.crawler.engine._update_job_in_db") as mock_update:
        service.is_enabled = False
        await service.run_crawl_job(
            job_id="test_job_1",
            url="http://example.com",
            max_pages=5,
            max_depth=1,
            concurrency=2,
            js_render=False,
            follow_external=False,
            respect_robots=False,
            label="test",
            widget_id=None
        )
        mock_update.assert_any_call("test_job_1", status="failed", error_message="Web crawler service is disabled in config.yaml")
        print("-> Test 1 (Disabled Service Check): PASSED")

    # Restore is_enabled
    service.is_enabled = True

    # Test 2: Pre-execution Playwright validation (simulate ImportError)
    with patch("app.services.workers.crawler.engine._update_job_in_db") as mock_update, \
         patch("app.services.workers.crawler.engine._is_job_cancelled", return_value=False):
        
        original_modules = sys.modules.copy()
        try:
            sys.modules['playwright'] = None  # Force ImportError on import playwright
            await service.run_crawl_job(
                job_id="test_job_2",
                url="http://example.com",
                max_pages=5,
                max_depth=1,
                concurrency=2,
                js_render=True, # js_render is True
                follow_external=False,
                respect_robots=False,
                label="test",
                widget_id=None
            )
            mock_update.assert_any_call(
                "test_job_2", 
                status="failed", 
                error_message="Playwright is not installed in the python environment. Run 'pip install playwright'."
            )
            print("-> Test 2 (Playwright ImportError Check): PASSED")
        finally:
            sys.modules = original_modules

    # Test 3: Subprocess non-zero return code
    mock_process = MagicMock()
    async def mock_wait():
        return 0
    mock_process.wait = mock_wait
    mock_process.returncode = 1
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec, \
         patch("app.services.workers.crawler.engine._update_job_in_db") as mock_update, \
         patch("app.services.workers.crawler.engine._is_job_cancelled", return_value=False):
        
        await service.run_crawl_job(
            job_id="test_job_3",
            url="http://example.com",
            max_pages=5,
            max_depth=1,
            concurrency=2,
            js_render=False,
            follow_external=False,
            respect_robots=False,
            label="test",
            widget_id=None
        )
        mock_update.assert_any_call(
            "test_job_3",
            status="failed",
            error_message="Scrapy subprocess exited with error code 1. Please check server/worker logs."
        )
        print("-> Test 3 (Subprocess Exit Code Validation): PASSED")

    # Test 4: Subprocess Timeout validation
    async def delayed_wait():
        await asyncio.sleep(5)
        return 0
    
    mock_process_timeout = MagicMock()
    mock_process_timeout.wait = delayed_wait
    mock_process_timeout.terminate = MagicMock()
    mock_process_timeout.kill = MagicMock()
    mock_process_timeout.returncode = None
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_timeout) as mock_exec, \
         patch("app.services.workers.crawler.engine._update_job_in_db") as mock_update, \
         patch("app.services.workers.crawler.engine._is_job_cancelled", return_value=False), \
         patch.object(settings.crawler, "job_timeout_seconds", 1):
        
        await service.run_crawl_job(
            job_id="test_job_4",
            url="http://example.com",
            max_pages=5,
            max_depth=1,
            concurrency=2,
            js_render=False,
            follow_external=False,
            respect_robots=False,
            label="test",
            widget_id=None
        )
        mock_process_timeout.terminate.assert_called_once()
        mock_update.assert_any_call(
            "test_job_4",
            status="failed",
            error_message="Crawl job timed out after 1 seconds."
        )
        print("-> Test 4 (Subprocess Timeout and Cleanup Check): PASSED")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING CRAWLER FIXES VERIFICATION SUITE")
    print("=========================================")
    try:
        asyncio.run(test_crawler_service())
        print("=========================================")
        print("ALL CRAWLER FIXES TESTS PASSED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
