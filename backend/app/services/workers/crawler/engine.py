import asyncio
import hashlib
import json
import logging
import random
from collections import deque
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.minio_client import storage_manager
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text

from app.services.workers.crawler.utils import (
    _USER_AGENTS,
    _proxy_provider,
    _normalize_url,
    _is_same_domain,
    _is_skippable_url,
    _score_external_url_relevance,
    _fetch_page_plain,
    _fetch_page_js,
    _extract_page_content,
    _check_robots_txt_sync
)
from app.services.workers.crawler.staging import (
    _update_job_in_db,
    _is_job_cancelled,
    _commit_staged_data
)

logger = logging.getLogger("arionex.crawler_service")


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

        # بررسی سیگنال لغو کار
        if _is_job_cancelled(job_id):
            logger.info(f"[CrawlerJob:{job_id}] Job cancelled before starting BFS.")
            return

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
            # بررسی سیگنال لغو در آغاز هر لوپ BFS
            if _is_job_cancelled(job_id):
                logger.info(f"[CrawlerJob:{job_id}] Cancellation signal detected in BFS loop. Terminating gracefully...")
                try:
                    storage_manager.delete_objects_in_prefix(f"crawl-staging/{job_id}/")
                except Exception as clean_err:
                    logger.warning(f"[CrawlerJob:{job_id}] Failed to clean up staged files: {str(clean_err)}")
                return

            batch = []
            while queue and len(batch) < concurrency:
                batch.append(queue.popleft())

            async def process_page(page_url: str, depth: int):
                nonlocal pages_crawled, chunks_total, pages_failed

                async with semaphore:
                    if _is_job_cancelled(job_id):
                        return

                    await asyncio.sleep(delay_s)

                    ua = random.choice(_USER_AGENTS)
                    prx = _proxy_provider.get_proxy()

                    logger.debug(f"[CrawlerJob:{job_id}] Fetching (depth={depth}, proxy={prx}): {page_url}")

                    html = None
                    if js_render:
                        html = await _fetch_page_js(page_url, proxy=prx, user_agent=ua)
                    if html is None:
                        html = await _fetch_page_plain(page_url, proxy=prx, user_agent=ua)

                    if not html:
                        pages_failed += 1
                        return

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

                    normalized = normalize_text(raw_text)
                    if settings.security.pii_redaction:
                        normalized = redact_text(normalized)

                    chunks = chunk_text(normalized, chunk_size=350, overlap=75)
                    if not chunks:
                        pages_failed += 1
                        return

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

                            if respect_robots and not _check_robots_txt_sync(url, normalized_link, proxy=prx):
                                continue

                            visited.add(normalized_link)
                            queue.append((normalized_link, depth + 1))

            await asyncio.gather(*[process_page(pu, d) for pu, d in batch])

        if _is_job_cancelled(job_id):
            logger.info(f"[CrawlerJob:{job_id}] Cancellation detected post-BFS. Skipping commit.")
            try:
                storage_manager.delete_objects_in_prefix(f"crawl-staging/{job_id}/")
            except Exception as clean_err:
                logger.warning(f"[CrawlerJob:{job_id}] Failed to clean up staged files: {str(clean_err)}")
            return

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
