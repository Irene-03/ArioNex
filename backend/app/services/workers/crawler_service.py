"""
/// <summary>
/// موتور اصلی کرالر وب آریونکس — Async BFS Website Crawler Engine
/// </summary>
/// <remarks>
/// این سرویس وظیفه کرال کردن سایت‌ها را با معماری async Breadth-First Search بر عهده دارد.
/// قابلیت‌های کلیدی:
///   ۱. رعایت robots.txt — پشتیبانی از استاندارد بین‌المللی crawl delay و Disallow
///   ۲. Async BFS با محدودیت عمق و تعداد صفحه
///   ۳. استخراج هوشمند محتوا — فقط متن معنایی (بدون ناوبری، footer، تبلیغات)
///   ۴. پشتیبانی از JS-rendered pages با Playwright (قابل تنظیم)
///   ۵. فیلتر هوشمند لینک‌های خارجی با scoring مرتبط‌بودن
///   ۶. آپدیت real-time وضعیت job در PostgreSQL
///   ۷. normalize → chunk → embed → index مثل pipeline سند معمولی
///   ۸. Rate limiting و تاخیر مودبانه بین درخواست‌ها
/// </remarks>
"""

import asyncio
import hashlib
import logging
import re
import uuid
from collections import deque
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text

logger = logging.getLogger("arionex.crawler_service")

# -------------------------------------------------------
# ثابت‌های کرالر
# -------------------------------------------------------
_DEFAULT_HEADERS = {
    "User-Agent": (
        "ArioNexBot/1.0 (+https://arionex.ai/bot; "
        "Enterprise Knowledge Crawler — respectful and rate-limited)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa,en;q=0.9",
}

# تگ‌های HTML که محتوای اصلی و معنایی دارند
_SEMANTIC_TAGS = [
    "article", "main", "section", "p", "h1", "h2", "h3",
    "h4", "h5", "h6", "li", "td", "th", "blockquote", "figcaption"
]

# دامنه‌هایی که به طور پیش‌فرض کرال نمی‌شوند (اجتناب از خزیدن در CDN‌ها و...)
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


def _normalize_url(url: str) -> str:
    """
    /// <summary>
    /// نرمال‌سازی URL برای deduplicate کردن لینک‌های تکراری
    /// </summary>
    /// <remarks>
    /// fragment (#...) را حذف می‌کند، query string را مرتب می‌کند
    /// </remarks>
    """
    parsed = urlparse(url)
    # حذف fragment (مثل #section1) که به محتوای جدیدی اشاره نمی‌کند
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
    /// بررسی می‌کند آیا URL باید skip شود (پسوند مدیا، جاوا اسکریپت و...)
    /// </summary>
    """
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in _SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True
    # حذف لینک‌های mailto: و tel: و javascript:
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
    /// <remarks>
    /// امتیاز ۰ تا ۱:
    ///   - ۰.۹+: subdomain همان سازمان (blog.company.com)
    ///   - ۰.۷+: زیردامنه دوم یکسان
    ///   - ۰.۳: هر دامنه خارجی دیگری
    ///   - ۰.۰: دامنه بلاک‌شده
    /// </remarks>
    """
    if _is_blocked_domain(target_url):
        return 0.0

    target_domain = urlparse(target_url).netloc.lower().lstrip("www.")

    # آیا subdomain همان شرکت است؟ (blog.example.com در حالی که base = example.com)
    base_root = ".".join(base_domain.rsplit(".", 2)[-2:])  # برداشت root domain
    target_root = ".".join(target_domain.rsplit(".", 2)[-2:])

    if target_root == base_root:
        return 0.9  # بسیار مرتبط — subdomain همان شرکت

    return 0.3  # خارجی — امتیاز پایین


async def _fetch_page_plain(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """
    /// <summary>
    /// دریافت HTML صفحه با httpx (برای صفحات Static)
    /// </summary>
    /// <returns>محتوای HTML یا None در صورت خطا</returns>
    """
    try:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
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
        logger.warning(f"Failed to fetch page {url}: {str(e)}")
        return None


async def _fetch_page_js(url: str) -> Optional[str]:
    """
    /// <summary>
    /// دریافت HTML صفحه با Playwright برای JS-rendered pages (React/Vue/Angular)
    /// </summary>
    /// <remarks>
    /// این متد فقط در صورتی که js_render=True در تنظیمات باشد فراخوانی می‌شود.
    /// نیاز به نصب playwright و chromium دارد.
    /// </remarks>
    /// <returns>HTML پس از رندر کامل JavaScript یا None در صورت خطا</returns>
    """
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=_DEFAULT_HEADERS["User-Agent"],
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
        logger.warning(f"Playwright failed to render {url}: {str(e)}")
        return None


def _extract_page_content(html: str, url: str) -> dict:
    """
    /// <summary>
    /// استخراج هوشمند محتوای معنایی از HTML — فقط متن، نه منو و footer و تبلیغات
    /// </summary>
    /// <returns>دیکشنری شامل title، description، headings، body_text، و outgoing_links</returns>
    """
    soup = BeautifulSoup(html, "lxml")

    # حذف تگ‌های غیرمفید
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "noscript", "iframe", "form",
                     "button", "input", "select", "textarea"]):
        tag.decompose()

    # استخراج title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # استخراج meta description
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    # استخراج og:description
    if not description:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = og_desc["content"].strip()

    # استخراج headings به عنوان ساختار معنایی
    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        h_text = h.get_text(separator=" ", strip=True)
        if h_text:
            headings.append(h_text)

    # استخراج متن معنایی از تگ‌های اصلی
    body_parts = []
    for tag in soup.find_all(_SEMANTIC_TAGS):
        text = tag.get_text(separator=" ", strip=True)
        if text and len(text) > 30:  # حداقل ۳۰ کاراکتر برای فیلتر کردن متون کوتاه زائد
            body_parts.append(text)

    # حذف تکراری‌ها و ادغام
    seen = set()
    unique_parts = []
    for part in body_parts:
        part_hash = hashlib.md5(part.encode()).hexdigest()
        if part_hash not in seen:
            seen.add(part_hash)
            unique_parts.append(part)

    body_text = "\n".join(unique_parts)

    # ترکیب محتوا با ساختار معنایی
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

    # استخراج لینک‌های خروجی
    outgoing_links = set()
    base_parsed = urlparse(url)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        try:
            absolute_url = urljoin(url, href)
            # فقط http و https
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


def _check_robots_txt_sync(base_url: str, target_url: str) -> bool:
    """
    /// <summary>
    /// بررسی اجازه کرال بر اساس robots.txt (نسخه synchronous)
    /// </summary>
    /// <returns>True اگر کرال مجاز باشد، False اگر Disallow باشد</returns>
    """
    try:
        from robotexclusionrulesparser import RobotExclusionRulesParser
        import requests as sync_requests
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        resp = sync_requests.get(robots_url, timeout=5, headers={"User-Agent": _DEFAULT_HEADERS["User-Agent"]})
        if resp.status_code == 200:
            rerp = RobotExclusionRulesParser()
            rerp.parse(resp.text)
            return rerp.is_allowed(_DEFAULT_HEADERS["User-Agent"], target_url)
        return True  # اگر robots.txt نبود، کرال مجاز است
    except Exception as e:
        logger.debug(f"robots.txt check failed for {base_url}: {str(e)}")
        return True  # در صورت خطا، با احتیاط اجازه می‌دهیم


def _update_job_in_db(job_id: str, **fields) -> None:
    """
    /// <summary>
    /// آپدیت real-time وضعیت job در جدول crawler_jobs
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
    /// ایندکس chunk‌های استخراج شده در جدول pg_supervisor — مثل pipeline سند
    /// </summary>
    /// <returns>تعداد chunk‌هایی که با موفقیت ایندکس شدند</returns>
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


class CrawlerService:
    """
    /// <summary>
    /// سرویس اصلی کرالر وب — Async BFS Engine
    /// </summary>
    /// <remarks>
    /// این کلاس کل فرایند کرال را مدیریت می‌کند:
    ///   ۱. ایجاد و آپدیت job در دیتابیس
    ///   ۲. BFS crawl با کنترل همزمانی
    ///   ۳. استخراج و ایندکس محتوا
    ///   ۴. گزارش‌دهی real-time
    /// </remarks>
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
        /// اجرای کامل یک job کرال — برای اجرا به عنوان BackgroundTask ساخته شده
        /// </summary>
        /// <param name="job_id">شناسه یکتای job</param>
        /// <param name="url">URL ریشه برای شروع کرال</param>
        /// <param name="max_pages">حداکثر صفحات</param>
        /// <param name="max_depth">حداکثر عمق</param>
        /// <param name="concurrency">تعداد fetch‌های همزمان</param>
        /// <param name="js_render">رندر JavaScript با Playwright</param>
        /// <param name="follow_external">دنبال کردن لینک‌های خارجی</param>
        /// <param name="respect_robots">رعایت robots.txt</param>
        /// <param name="label">لیبل سفارشی برای chunk‌ها</param>
        /// <param name="widget_id">شناسه ابزارک وب‌سایت (اختیاری)</param>
        """
        if not self.is_enabled:
            _update_job_in_db(job_id, status="failed", error_message="Web crawler service is disabled in config.yaml")
            logger.warning(f"[CrawlerJob:{job_id}] Web crawler is disabled. Aborting.")
            return

        logger.info(f"[CrawlerJob:{job_id}] Starting crawl for: {url} (max_pages={max_pages}, depth={max_depth}, js={js_render})")
        _update_job_in_db(job_id, status="running")

        # تنظیم لیبل پیش‌فرض
        base_domain = urlparse(url).netloc.lower().lstrip("www.")
        effective_label = label or f"crawled:{base_domain}"

        # بررسی robots.txt برای URL ریشه
        if respect_robots and not _check_robots_txt_sync(url, url):
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

        # سمافور برای کنترل همزمانی
        semaphore = asyncio.Semaphore(concurrency)
        delay_s = settings.crawler.request_delay_ms / 1000.0

        async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client:
            while queue and pages_crawled < max_pages:
                # پردازش batch از صف
                batch = []
                while queue and len(batch) < concurrency:
                    batch.append(queue.popleft())

                # ایجاد task‌های همزمان برای هر batch
                async def process_page(page_url: str, depth: int):
                    nonlocal pages_crawled, chunks_total, pages_failed

                    async with semaphore:
                        # تاخیر مودبانه بین درخواست‌ها
                        await asyncio.sleep(delay_s)

                        logger.debug(f"[CrawlerJob:{job_id}] Fetching (depth={depth}): {page_url}")

                        # دریافت HTML
                        html = None
                        if js_render:
                            html = await _fetch_page_js(page_url)
                        if html is None:
                            html = await _fetch_page_plain(client, page_url)

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

                        # پردازش متن: normalize → PII redact → chunk → embed → index
                        normalized = normalize_text(raw_text)
                        if settings.security.pii_redaction:
                            normalized = redact_text(normalized)

                        chunks = chunk_text(normalized, chunk_size=350, overlap=75)
                        indexed = _index_chunks_in_db(chunks, effective_label, page_url, job_id)

                        pages_crawled += 1
                        chunks_total += indexed

                        # آپدیت progress در دیتابیس
                        _update_job_in_db(
                            job_id,
                            pages_crawled=pages_crawled,
                            chunks_indexed=chunks_total,
                            pages_failed=pages_failed
                        )

                        logger.info(
                            f"[CrawlerJob:{job_id}] Indexed {indexed} chunks from: {page_url} "
                            f"(total pages={pages_crawled}, chunks={chunks_total})"
                        )

                        # کشف لینک‌های جدید برای depth بعدی
                        if depth < max_depth and pages_crawled < max_pages:
                            for link in page_data["outgoing_links"]:
                                normalized_link = _normalize_url(link)
                                if normalized_link in visited:
                                    continue
                                if _is_skippable_url(normalized_link):
                                    continue

                                # تصمیم‌گیری درباره لینک‌های خارجی
                                if not _is_same_domain(url, normalized_link):
                                    if not follow_external:
                                        continue
                                    # بررسی سختگیرانه دامنه‌های خارجی
                                    score = _score_external_url_relevance(base_domain, normalized_link)
                                    if score < 0.85:  # فقط subdomain‌های همان سازمان
                                        continue

                                # بررسی robots.txt برای هر لینک
                                if respect_robots and not _check_robots_txt_sync(url, normalized_link):
                                    continue

                                visited.add(normalized_link)
                                queue.append((normalized_link, depth + 1))

                # اجرای همزمان batch
                await asyncio.gather(*[process_page(pu, d) for pu, d in batch])

        # پایان job
        final_status = "completed" if pages_failed == 0 or pages_crawled > 0 else "failed"
        _update_job_in_db(
            job_id,
            status=final_status,
            pages_crawled=pages_crawled,
            chunks_indexed=chunks_total,
            pages_failed=pages_failed,
        )

        logger.info(
            f"[CrawlerJob:{job_id}] Finished crawl for {url}. "
            f"Status={final_status}, Pages={pages_crawled}, Chunks={chunks_total}, Failed={pages_failed}"
        )


# نمونه سراسری سرویس کرالر
crawler_service = CrawlerService()
