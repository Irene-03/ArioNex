"""
/// <summary>
/// موتور اصلی کرالر وب آریونکس — Async BFS Website Crawler Engine (Production-Grade)
/// </summary>
/// <remarks>
/// این سرویس وظیفه کرال کردن سایت‌ها را با معماری async Breadth-First Search بر عهده دارد.
/// تغییرات جدید سطح تجاری:
///   ۱. چرخش پروکسی و User-Agent برای عبور از سدهای ضد بات
///   ۲. پایپ‌لاین موقت Transactional Staging: ذخیره چانک‌ها به عنوان فایل JSON در MinIO
///   ۳. ثبت تراکنشی نهایی (Atomic Bulk Index) به دیتابیس پستگرس برای جلوگیری از باقی ماندن داده‌های ناقص
/// </remarks>
"""

import asyncio
import hashlib
import logging
import re
import uuid
import json
import random
from collections import deque
from datetime import datetime
from typing import Optional, List
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text
from app.core.minio_client import storage_manager
from app.helpers.proxy_helper import StaticListProxyProvider

logger = logging.getLogger("arionex.crawler_service")

# -------------------------------------------------------
# ثابت‌های کرالر
# -------------------------------------------------------
_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa,en;q=0.9",
}

# لیستی از User-Agent‌های واقعی برای چرخش و دور زدن ضدبات‌ها
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
]

# تگ‌های HTML که محتوای اصلی و معنایی دارند
_SEMANTIC_TAGS = [
    "article", "main", "section", "p", "h1", "h2", "h3",
    "h4", "h5", "h6", "li", "td", "th", "blockquote", "figcaption"
]

# دامنه‌هایی که به طور پیش‌فرض کرال نمی‌شوند
_BLOCKED_DOMAINS = {
    "google.com", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "linkedin.com", "t.me", "telegram.org",
    "gstatic.com", "googleapis.com", "cloudflare.com",
    "jquery.com", "bootstrap.com", "cdnjs.cloudflare.com",
}

# پسوندهایی که محتوای متنی ندارند
_SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".zip", ".rar", ".tar", ".gz", ".exe", ".dmg",
    ".mp4", ".mp3", ".avi", ".mov", ".wav", ".ogg",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

# نمونه‌سازی از کلاس کمکی پروکسی بر اساس کانفیگ فعال
_proxy_provider = StaticListProxyProvider(settings.crawler.proxy_pool)


def _normalize_url(url: str) -> str:
    """
    /// <summary>
    /// نرمال‌سازی URL برای deduplicate کردن لینک‌های تکراری
    /// </summary>
    """
    parsed = urlparse(url)
    normalized = parsed._replace(fragment="", query="")
    return urlunparse(normalized).rstrip("/")


def _is_same_domain(base_url: str, target_url: str) -> bool:
    """
    /// <summary>
    /// بررسی می‌کند که آیا target_url با دامنه اصلی base_url یکسان است
    /// </summary>
    """
    base_domain = urlparse(base_url).netloc.lower().lstrip("www.")
    target_domain = urlparse(target_url).netloc.lower().lstrip("www.")
    return target_domain == base_domain or target_domain.endswith(f".{base_domain}")


def _is_skippable_url(url: str) -> bool:
    """
    /// <summary>
    /// بررسی می‌کند آیا URL باید skip شود
    /// </summary>
    """
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in _SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True
    if parsed.scheme in ("mailto", "tel", "javascript", "data"):
        return True
    return False


def _is_blocked_domain(url: str) -> bool:
    """
    /// <summary>
    /// بررسی می‌کند آیا دامنه در لیست سیاه کرالر قرار دارد
    /// </summary>
    """
    domain = urlparse(url).netloc.lower().lstrip("www.")
    for blocked in _BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def _score_external_url_relevance(base_domain: str, target_url: str) -> float:
    """
    /// <summary>
    /// امتیازدهی به لینک‌های خارجی بر اساس احتمال مرتبط‌بودن با سازمان اصلی
    /// </summary>
    """
    if _is_blocked_domain(target_url):
        return 0.0

    target_domain = urlparse(target_url).netloc.lower().lstrip("www.")
    base_root = ".".join(base_domain.rsplit(".", 2)[-2:])
    target_root = ".".join(target_domain.rsplit(".", 2)[-2:])

    if target_root == base_root:
        return 0.9

    return 0.3


async def _fetch_page_plain(url: str, proxy: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
    """
    /// <summary>
    /// دریافت HTML صفحه با httpx با پشتیبانی از چرخش پروکسی و User-Agent
    /// </summary>
    """
    headers = _DEFAULT_HEADERS.copy()
    headers["User-Agent"] = user_agent or random.choice(_USER_AGENTS)

    try:
        # ساخت کلاینت مجزا برای تغییر موفقیت‌آمیز IP پروکسی و عدم اشتراک‌گذاری Sessionها
        async with httpx.AsyncClient(headers=headers, proxy=proxy, verify=True, timeout=15.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    return response.text
            logger.debug(f"Skipping non-HTML response from {url} (status={response.status_code})")
            return None
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching page: {url}")
        return None
    except httpx.TooManyRedirects:
        logger.warning(f"Too many redirects: {url}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch page {url} (proxy={proxy}): {str(e)}")
        if proxy:
            _proxy_provider.report_failure(proxy)
        return None


async def _fetch_page_js(url: str, proxy: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
    """
    /// <summary>
    /// دریافت HTML صفحه با Playwright برای صفحات رندر شونده با JS با پشتیبانی از پروکسی و UA
    /// </summary>
    """
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            playwright_proxy = None
            if proxy:
                playwright_proxy = {"server": proxy}

            browser = await p.chromium.launch(headless=True, proxy=playwright_proxy)
            context = await browser.new_context(
                user_agent=user_agent or random.choice(_USER_AGENTS),
                locale="fa-IR"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            await browser.close()
            return html
    except ImportError:
        logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        logger.warning(f"Playwright failed to render {url} (proxy={proxy}): {str(e)}")
        if proxy:
            _proxy_provider.report_failure(proxy)
        return None


def _extract_page_content(html: str, url: str) -> dict:
    """
    /// <summary>
    /// استخراج هوشمند محتوای معنایی از HTML
    /// </summary>
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "noscript", "iframe", "form",
                     "button", "input", "select", "textarea"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    if not description:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = og_desc["content"].strip()

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        h_text = h.get_text(separator=" ", strip=True)
        if h_text:
            headings.append(h_text)

    body_parts = []
    for tag in soup.find_all(_SEMANTIC_TAGS):
        text = tag.get_text(separator=" ", strip=True)
        if text and len(text) > 30:
            body_parts.append(text)

    seen = set()
    unique_parts = []
    for part in body_parts:
        part_hash = hashlib.md5(part.encode()).hexdigest()
        if part_hash not in seen:
            seen.add(part_hash)
            unique_parts.append(part)

    body_text = "\n".join(unique_parts)

    full_content_parts = []
    if title:
        full_content_parts.append(f"عنوان صفحه: {title}")
    if description:
        full_content_parts.append(f"توضیح: {description}")
    if headings:
        full_content_parts.append("سرفصل‌ها: " + " | ".join(headings[:10]))
    if body_text:
        full_content_parts.append(body_text)

    full_text = "\n\n".join(full_content_parts)

    outgoing_links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        try:
            absolute_url = urljoin(url, href)
            if urlparse(absolute_url).scheme in ("http", "https"):
                normalized = _normalize_url(absolute_url)
                outgoing_links.add(normalized)
        except Exception:
            continue

    return {
        "title": title,
        "description": description,
        "body_text": full_text,
        "outgoing_links": outgoing_links,
    }


def _check_robots_txt_sync(base_url: str, target_url: str, proxy: Optional[str] = None) -> bool:
    """
    /// <summary>
    /// بررسی اجازه کرال بر اساس robots.txt با پشتیبانی از پروکسی
    /// </summary>
    """
    try:
        from robotexclusionrulesparser import RobotExclusionRulesParser
        import requests as sync_requests
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        resp = sync_requests.get(
            robots_url,
            timeout=5,
            headers={"User-Agent": random.choice(_USER_AGENTS)},
            proxies=proxies
        )
        if resp.status_code == 200:
            rerp = RobotExclusionRulesParser()
            rerp.parse(resp.text)
            return rerp.is_allowed("ArioNexBot/1.0", target_url)
        return True
    except Exception as e:
        logger.debug(f"robots.txt check failed for {base_url}: {str(e)}")
        return True


def _update_job_in_db(job_id: str, **fields) -> None:
    """
    /// <summary>
    /// آپدیت real-time وضعیت job در دیتابیس
    /// </summary>
    """
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow()
    set_clauses = ", ".join([f"{k} = %s" for k in fields.keys()])
    values = list(fields.values()) + [job_id]
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE crawler_jobs SET {set_clauses} WHERE job_id = %s",
                values
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update crawler job {job_id}: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def _index_chunks_in_db(chunks: list, label: str, source_url: str, job_id: str) -> int:
    """
    /// <summary>
    /// تابع ایندکس مجزای چانک‌ها (برای سازگاری عقب‌رو)
    /// </summary>
    """
    conn = None
    indexed = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for idx, chunk in enumerate(chunks):
                embedding = get_embedding(chunk)
                cur.execute(
                    """
                    INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                    VALUES (%s, %s::vector, %s, %s, %s)
                    """,
                    (chunk, embedding, label, 0, idx + 1)
                )
                indexed += 1
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to index chunks for job {job_id}, url {source_url}: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return indexed


def _commit_staged_data(job_id: str, label: str) -> int:
    """
    /// <summary>
    /// تراکنش نهایی انتقال داده‌های موقت کرال شده از MinIO به جدول نهایی در Postgres
    /// </summary>
    /// <returns>تعداد چانک‌های با موفقیت ایندکس شده</returns>
    """
    prefix = f"crawl-staging/{job_id}/"
    staged_files = storage_manager.list_objects(prefix)
    if not staged_files:
        logger.warning(f"[CrawlerJob:{job_id}] No staged files found to commit.")
        return 0

    logger.info(f"[CrawlerJob:{job_id}] Found {len(staged_files)} staged files. Beginning bulk commit...")

    chunks_to_insert = []

    # خواندن تمام داده‌ها از MinIO/Local
    for file_path in staged_files:
        try:
            content_bytes = storage_manager.get_object_data(file_path)
            data = json.loads(content_bytes.decode("utf-8"))
            for idx, chunk in enumerate(data.get("chunks", [])):
                chunks_to_insert.append({
                    "content": chunk,
                    "url": data.get("url"),
                    "sequence_id": idx + 1
                })
        except Exception as e:
            logger.error(f"[CrawlerJob:{job_id}] Failed to read staging file {file_path}: {str(e)}")
            raise e

    if not chunks_to_insert:
        logger.warning(f"[CrawlerJob:{job_id}] No chunks found in staged files.")
        return 0

    logger.info(f"[CrawlerJob:{job_id}] Generating embeddings for {len(chunks_to_insert)} chunks...")

    # محاسبه امبدینگ‌ها خارج از تراکنش دیتابیس جهت ممانعت از ایجاد قفل طولانی‌مدت
    embeddings_data = []
    for item in chunks_to_insert:
        try:
            emb = get_embedding(item["content"])
            embeddings_data.append((item["content"], emb, label, 0, item["sequence_id"]))
        except Exception as e:
            logger.error(f"[CrawlerJob:{job_id}] Embedding generation failed for chunk: {str(e)}")
            raise e

    # درج اتمیک و اتمیک حذف داده‌های قدیمی
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            logger.info(f"[CrawlerJob:{job_id}] Deleting old chunks with label '{label}'")
            cur.execute("DELETE FROM pg_supervisor WHERE label = %s", (label,))

            logger.info(f"[CrawlerJob:{job_id}] Bulk inserting {len(embeddings_data)} new chunks...")
            cur.executemany(
                """
                INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                VALUES (%s, %s::vector, %s, %s, %s)
                """,
                embeddings_data
            )
            conn.commit()
            logger.info(f"[CrawlerJob:{job_id}] Successfully committed all chunks to Postgres.")
    except Exception as e:
        logger.error(f"[CrawlerJob:{job_id}] Database transaction failed, rolling back. Error: {str(e)}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

    # پاکسازی فایل‌های موقت در MinIO
    try:
        storage_manager.delete_objects_in_prefix(prefix)
        logger.info(f"[CrawlerJob:{job_id}] Cleaned up MinIO staging prefix: {prefix}")
    except Exception as e:
        logger.warning(f"[CrawlerJob:{job_id}] Staging cleanup failed: {str(e)}")

    return len(embeddings_data)


class CrawlerService:
    """
    /// <summary>
    /// سرویس مدیریت موتور کرالر وب
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.web_crawler

    async def run_crawl_job(
        self,
        job_id: str,
        url: str,
        max_pages: int,
        max_depth: int,
        concurrency: int,
        js_render: bool,
        follow_external: bool,
        respect_robots: bool,
        label: Optional[str],
        widget_id: Optional[int],
    ) -> None:
        """
        /// <summary>
        /// اجرای کامل یک job کرال به صورت تراکنشی و با استفاده از لایه میانی MinIO
        /// </summary>
        """
        if not self.is_enabled:
            _update_job_in_db(job_id, status="failed", error_message="Web crawler service is disabled in config.yaml")
            logger.warning(f"[CrawlerJob:{job_id}] Web crawler is disabled. Aborting.")
            return

        logger.info(f"[CrawlerJob:{job_id}] Starting crawl for: {url} (max_pages={max_pages}, depth={max_depth}, js={js_render})")
        _update_job_in_db(job_id, status="running")

        base_domain = urlparse(url).netloc.lower().lstrip("www.")
        effective_label = label or f"crawled:{base_domain}"

        # بررسی robots.txt ریشه با پروکسی تصادفی اولیه
        initial_proxy = _proxy_provider.get_proxy()
        if respect_robots and not _check_robots_txt_sync(url, url, proxy=initial_proxy):
            msg = f"robots.txt disallows crawling root URL: {url}"
            logger.warning(f"[CrawlerJob:{job_id}] {msg}")
            _update_job_in_db(job_id, status="failed", error_message=msg)
            return

        visited: set = set()
        pages_crawled = 0
        chunks_total = 0
        pages_failed = 0

        # صف BFS: (url, depth)
        queue: deque = deque()
        queue.append((_normalize_url(url), 0))
        visited.add(_normalize_url(url))

        semaphore = asyncio.Semaphore(concurrency)
        delay_s = settings.crawler.request_delay_ms / 1000.0

        while queue and pages_crawled < max_pages:
            batch = []
            while queue and len(batch) < concurrency:
                batch.append(queue.popleft())

            async def process_page(page_url: str, depth: int):
                nonlocal pages_crawled, chunks_total, pages_failed

                async with semaphore:
                    await asyncio.sleep(delay_s)

                    # انتخاب تصادفی User-Agent و پروکسی مجزا برای این درخواست
                    ua = random.choice(_USER_AGENTS)
                    prx = _proxy_provider.get_proxy()

                    logger.debug(f"[CrawlerJob:{job_id}] Fetching (depth={depth}, proxy={prx}): {page_url}")

                    # دریافت HTML صفحه
                    html = None
                    if js_render:
                        html = await _fetch_page_js(page_url, proxy=prx, user_agent=ua)
                    if html is None:
                        html = await _fetch_page_plain(page_url, proxy=prx, user_agent=ua)

                    if not html:
                        pages_failed += 1
                        return

                    # استخراج محتوا
                    try:
                        page_data = _extract_page_content(html, page_url)
                    except Exception as e:
                        logger.warning(f"[CrawlerJob:{job_id}] Content extraction failed for {page_url}: {str(e)}")
                        pages_failed += 1
                        return

                    raw_text = page_data["body_text"]
                    if not raw_text.strip():
                        logger.debug(f"[CrawlerJob:{job_id}] Empty content at: {page_url}")
                        pages_failed += 1
                        return

                    # نرمال‌سازی و فیلتر اطلاعات شخصی
                    normalized = normalize_text(raw_text)
                    if settings.security.pii_redaction:
                        normalized = redact_text(normalized)

                    # قطعه‌بندی متن (Chunking)
                    chunks = chunk_text(normalized, chunk_size=350, overlap=75)
                    if not chunks:
                        pages_failed += 1
                        return

                    # ذخیره داده‌های صفحه و قطعات به صورت موقت در MinIO (Transactional Staging)
                    page_hash = hashlib.md5(page_url.encode()).hexdigest()
                    object_name = f"crawl-staging/{job_id}/{page_hash}.json"
                    payload = {
                        "url": page_url,
                        "title": page_data["title"],
                        "description": page_data["description"],
                        "chunks": chunks,
                        "label": effective_label
                    }

                    try:
                        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        storage_manager.put_object_data(object_name, payload_bytes, content_type="application/json")
                    except Exception as e:
                        logger.error(f"[CrawlerJob:{job_id}] MinIO staging failed for {page_url}: {str(e)}")
                        pages_failed += 1
                        return

                    pages_crawled += 1
                    chunks_total += len(chunks)

                    # آپدیت موقت پیشرفت کار برای اطلاع فرانت‌اند
                    _update_job_in_db(
                        job_id,
                        pages_crawled=pages_crawled,
                        chunks_indexed=chunks_total,
                        pages_failed=pages_failed
                    )

                    logger.info(
                        f"[CrawlerJob:{job_id}] Staged {len(chunks)} chunks from: {page_url} "
                        f"(total pages={pages_crawled}, chunks={chunks_total})"
                    )

                    # کشف لینک‌های جدید برای BFS
                    if depth < max_depth and pages_crawled < max_pages:
                        for link in page_data["outgoing_links"]:
                            normalized_link = _normalize_url(link)
                            if normalized_link in visited:
                                continue
                            if _is_skippable_url(normalized_link):
                                continue

                            if not _is_same_domain(url, normalized_link):
                                if not follow_external:
                                    continue
                                score = _score_external_url_relevance(base_domain, normalized_link)
                                if score < 0.85:
                                    continue

                            # بررسی robots.txt با پروکسی چرخشی
                            if respect_robots and not _check_robots_txt_sync(url, normalized_link, proxy=prx):
                                continue

                            visited.add(normalized_link)
                            queue.append((normalized_link, depth + 1))

            # اجرای همزمان بچ
            await asyncio.gather(*[process_page(pu, d) for pu, d in batch])

        # انجام تراکنش نهایی انتقال اطلاعات از MinIO به Postgres
        committed_chunks = 0
        if pages_crawled > 0:
            try:
                logger.info(f"[CrawlerJob:{job_id}] BFS complete. Committing staged data atomically...")
                committed_chunks = _commit_staged_data(job_id, effective_label)
                final_status = "completed"
            except Exception as e:
                logger.error(f"[CrawlerJob:{job_id}] Atomic commit transaction failed: {str(e)}")
                final_status = "failed"
                _update_job_in_db(
                    job_id,
                    status=final_status,
                    error_message=f"Transactional commit failed: {str(e)}"
                )
                return
        else:
            final_status = "failed"

        # به‌روزرسانی نهایی وضعیت کار در دیتابیس
        _update_job_in_db(
            job_id,
            status=final_status,
            pages_crawled=pages_crawled,
            chunks_indexed=committed_chunks,
            pages_failed=pages_failed,
        )

        logger.info(
            f"[CrawlerJob:{job_id}] Finished crawl job for {url}. "
            f"Status={final_status}, Pages={pages_crawled}, Committed Chunks={committed_chunks}, Failed={pages_failed}"
        )


crawler_service = CrawlerService()
