import sys
import os
from pathlib import Path

# Ensures sys.path includes backend root so imports work
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent.parent  # backend/
app_dir = backend_dir / "app"

paths_to_add = [
    str(backend_dir),
    str(app_dir),
]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

import argparse
import asyncio
import hashlib
import json
import logging
import random
from urllib.parse import urlparse

import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.http import HtmlResponse

from app.core.config import settings
from app.core.minio_client import storage_manager
from app.core.database import get_db_connection
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text
from app.services.workers.crawler.utils import (
    _USER_AGENTS,
    _proxy_provider,
    _is_same_domain,
    _score_external_url_relevance,
    _fetch_page_js
)
from app.services.workers.crawler.staging import _update_job_in_db, _is_job_cancelled

logger = logging.getLogger("arionex.scrapy_spider")


class RotateProxyMiddleware:
    """
    Middleware برای چرخش پروکسی در هر درخواست Scrapy
    """
    def process_request(self, request, spider):
        prx = _proxy_provider.get_proxy()
        if prx:
            request.meta['proxy'] = prx
            spider.logger.debug(f"Using proxy: {prx} for {request.url}")


class PlaywrightMiddleware:
    """
    Middleware برای رندر کردن صفحات JavaScript با Playwright.
    به صورت سنکرون اجرا می‌شود تا با Twisted/Scrapy سازگار باشد.
    """
    def process_request(self, request, spider):
        if not getattr(spider, 'js_render', False):
            return None

        spider.logger.debug(f"Rendering JS via Playwright for: {request.url}")

        ua = request.headers.get("User-Agent")
        if isinstance(ua, bytes):
            ua = ua.decode("utf-8")
        if not ua:
            ua = random.choice(_USER_AGENTS)

        prx = _proxy_provider.get_proxy()

        try:
            # اجرای همزمان Playwright در thread pool جداگانه
            try:
                # اگر event loop در حال اجرا نباشد
                html = asyncio.run(_fetch_page_js(request.url, proxy=prx, user_agent=ua))
            except RuntimeError:
                # اگر loop در حال اجراست (احتمالاً در asyncioreactor)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        asyncio.run,
                        _fetch_page_js(request.url, proxy=prx, user_agent=ua)
                    )
                    html = future.result(timeout=35)

            if html:
                return HtmlResponse(
                    url=request.url,
                    body=html,
                    encoding="utf-8",
                    request=request
                )
        except Exception as e:
            spider.logger.warning(f"Playwright JS render failed for {request.url}: {str(e)}")

        # Fallback به درخواست HTTP معمولی
        return None


class ArioNexSpider(scrapy.Spider):
    name = "arionex_spider"

    def __init__(self, job_id, url, max_pages, max_depth, concurrency, js_render, follow_external, respect_robots, label, widget_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.start_url = url
        self.max_pages = int(max_pages)
        self.max_depth = int(max_depth)
        self.concurrency = int(concurrency)
        self.js_render = js_render.lower() == "true" if isinstance(js_render, str) else bool(js_render)
        self.follow_external = follow_external.lower() == "true" if isinstance(follow_external, str) else bool(follow_external)
        self.respect_robots = respect_robots.lower() == "true" if isinstance(respect_robots, str) else bool(respect_robots)
        self.label = label
        self.widget_id = int(widget_id) if widget_id else 0

        self.start_urls = [url]
        self.base_domain = urlparse(url).netloc.lower().lstrip("www.")
        self.effective_label = label or f"crawled:{self.base_domain}"

        self.pages_crawled = 0
        self.chunks_total = 0
        self.pages_failed = 0
        self.is_cancelled = False
        self.cancellation_check_counter = 0
        self.load_initial_stats()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        اتصال به سیگنال‌های Scrapy برای مدیریت چرخه حیات اسپایدر
        """
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider, reason):
        """لاگ کردن دلیل بسته شدن اسپایدر"""
        self.logger.info(
            f"Spider closed. Reason: {reason}. "
            f"Pages crawled: {self.pages_crawled}, "
            f"Chunks: {self.chunks_total}, "
            f"Failed: {self.pages_failed}"
        )

    def load_initial_stats(self):
        conn = None
        try:
            from psycopg2.extras import RealDictCursor
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT pages_crawled, chunks_indexed, pages_failed FROM crawler_jobs WHERE job_id = %s", (self.job_id,))
                row = cur.fetchone()
                if row:
                    self.pages_crawled = row["pages_crawled"] or 0
                    self.chunks_total = row["chunks_indexed"] or 0
                    self.pages_failed = row["pages_failed"] or 0
        except Exception as e:
            self.logger.error(f"Failed to load initial stats: {str(e)}")
        finally:
            if conn:
                conn.close()

    def update_db_stats(self):
        _update_job_in_db(
            self.job_id,
            pages_crawled=self.pages_crawled,
            chunks_indexed=self.chunks_total,
            pages_failed=self.pages_failed
        )

    def _check_cancellation(self) -> bool:
        """
        بررسی لغو شدن job با کش کردن نتایج برای کاهش بار دیتابیس.
        هر 10 صفحه یک بار به دیتابیس مراجعه می‌کند.
        """
        if self.is_cancelled:
            return True
        self.cancellation_check_counter += 1
        if self.cancellation_check_counter % 10 == 0:
            if _is_job_cancelled(self.job_id):
                self.is_cancelled = True
                return True
        return False

    def start_requests(self):
        """
        تولید درخواست اولیه - بدون استفاده از asyncio.create_task
        که با Scrapy/Twisted ناسازگار است.
        """
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # بررسی لغو در هر parse
        if self._check_cancellation():
            self.logger.info("Cancellation detected during page parse. Closing spider...")
            self.crawler.engine.close_spider(self, reason="cancelled")
            return

        if self.pages_crawled >= self.max_pages:
            self.logger.info("Reached max pages limit. Closing spider...")
            self.crawler.engine.close_spider(self, reason="max_pages")
            return

        page_url = response.url
        html = response.text

        from app.services.workers.crawler.utils import _extract_page_content
        try:
            page_data = _extract_page_content(html, page_url)
        except Exception as e:
            self.logger.warning(f"Content extraction failed for {page_url}: {str(e)}")
            self.pages_failed += 1
            self.update_db_stats()
            return

        raw_text = page_data["body_text"]
        if not raw_text.strip():
            self.logger.debug(f"Empty content at: {page_url}")
            self.pages_failed += 1
            self.update_db_stats()
            return

        normalized = normalize_text(raw_text)
        if settings.security.pii_redaction:
            normalized = redact_text(normalized)

        chunks = chunk_text(normalized, chunk_size=350, overlap=75)
        if not chunks:
            self.pages_failed += 1
            self.update_db_stats()
            return

        page_hash = hashlib.md5(page_url.encode()).hexdigest()
        object_name = f"crawl-staging/{self.job_id}/{page_hash}.json"
        payload = {
            "url": page_url,
            "title": page_data["title"],
            "description": page_data["description"],
            "chunks": chunks,
            "label": self.effective_label
        }

        try:
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            storage_manager.put_object_data(object_name, payload_bytes, content_type="application/json")
        except Exception as e:
            self.logger.error(f"MinIO staging failed for {page_url}: {str(e)}")
            self.pages_failed += 1
            self.update_db_stats()
            return

        self.pages_crawled += 1
        self.chunks_total += len(chunks)
        self.update_db_stats()

        self.logger.info(
            f"Staged {len(chunks)} chunks from: {page_url} "
            f"(total pages={self.pages_crawled}, chunks={self.chunks_total})"
        )

        depth = response.meta.get('depth', 0)
        if depth < self.max_depth and self.pages_crawled < self.max_pages:
            for link in page_data["outgoing_links"]:
                if not _is_same_domain(self.start_url, link):
                    if not self.follow_external:
                        continue
                    score = _score_external_url_relevance(self.base_domain, link)
                    if score < 0.85:
                        continue

                yield scrapy.Request(
                    url=link,
                    callback=self.parse,
                    meta={'depth': depth + 1}
                )


def create_scrapy_settings(concurrency: int, respect_robots: bool, jobdir_path: str, delay_s: float) -> Settings:
    """
    ایجاد تنظیمات Scrapy بدون نیاز به ساختار پروژه Scrapy (بدون get_project_settings)
    """
    scrapy_settings = Settings()

    # تنظیم reactor برای سازگاری با asyncio
    scrapy_settings.set(
        'TWISTED_REACTOR',
        'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        priority='project'
    )
    scrapy_settings.set('DOWNLOAD_HANDLERS', {
        'http': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
        'https': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
    }, priority='project')

    # تنظیمات همزمانی
    scrapy_settings.set('CONCURRENT_REQUESTS', concurrency, priority='project')
    scrapy_settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', concurrency, priority='project')

    # رعایت robots.txt
    scrapy_settings.set('ROBOTSTXT_OBEY', respect_robots, priority='project')

    # مسیر ذخیره وضعیت برای قابلیت Resume
    scrapy_settings.set('JOBDIR', jobdir_path, priority='project')

    # تأخیر بین درخواست‌ها
    scrapy_settings.set('DOWNLOAD_DELAY', delay_s, priority='project')

    # غیرفعال کردن محدودیت عمق برای کنترل دستی توسط اسپایدر
    scrapy_settings.set('DEPTH_LIMIT', 0, priority='project')

    # تنظیم middleware‌ها
    scrapy_settings.set('DOWNLOADER_MIDDLEWARES', {
        RotateProxyMiddleware: 100,
        PlaywrightMiddleware: 200,
    }, priority='project')

    # غیرفعال کردن کوکی‌ها برای پایداری بیشتر
    scrapy_settings.set('COOKIES_ENABLED', False, priority='project')

    # تنظیم User-Agent پیش‌فرض
    scrapy_settings.set('USER_AGENT', random.choice(_USER_AGENTS), priority='project')

    return scrapy_settings


def main():
    parser = argparse.ArgumentParser(description="Run Scrapy Spider programmatically")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-pages", required=True)
    parser.add_argument("--max-depth", required=True)
    parser.add_argument("--concurrency", required=True)
    parser.add_argument("--js-render", required=True)
    parser.add_argument("--follow-external", required=True)
    parser.add_argument("--respect-robots", required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--widget-id", default="0")

    args = parser.parse_args()

    # Resolve jobs directory at backend/jobs
    _backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    jobs_dir = os.path.join(_backend_dir, "jobs")
    os.makedirs(jobs_dir, exist_ok=True)
    jobdir_path = os.path.join(jobs_dir, args.job_id)

    # ساخت تنظیمات Scrapy بدون get_project_settings
    respect_robots_bool = args.respect_robots.lower() == "true"
    concurrency_int = int(args.concurrency)
    delay_s = settings.crawler.request_delay_ms / 1000.0

    scrapy_settings = create_scrapy_settings(
        concurrency=concurrency_int,
        respect_robots=respect_robots_bool,
        jobdir_path=jobdir_path,
        delay_s=delay_s
    )

    process = CrawlerProcess(scrapy_settings)
    process.crawl(
        ArioNexSpider,
        job_id=args.job_id,
        url=args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        concurrency=args.concurrency,
        js_render=args.js_render,
        follow_external=args.follow_external,
        respect_robots=args.respect_robots,
        label=args.label,
        widget_id=args.widget_id
    )
    process.start()


if __name__ == "__main__":
    main()
