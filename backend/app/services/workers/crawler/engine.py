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
        /// اجرای کامل یک job کرال به صورت تراکنشی و با استفاده از لایه میانی MinIO و فریمورک Scrapy
        /// </summary>
        """
        import sys
        import os
        import shutil
        from app.core.database import get_db_connection
        from psycopg2.extras import RealDictCursor

        if not self.is_enabled:
            _update_job_in_db(job_id, status="failed", error_message="Web crawler service is disabled in config.yaml")
            logger.warning(f"[CrawlerJob:{job_id}] Web crawler is disabled. Aborting.")
            return

        # Check if the job was already cancelled before starting
        if _is_job_cancelled(job_id):
            logger.info(f"[CrawlerJob:{job_id}] Job cancelled before starting.")
            return

        logger.info(f"[CrawlerJob:{job_id}] Starting Scrapy crawl for: {url} (max_pages={max_pages}, depth={max_depth}, js={js_render})")
        _update_job_in_db(job_id, status="running")

        base_domain = urlparse(url).netloc.lower().lstrip("www.")
        effective_label = label or f"crawled:{base_domain}"

        # Resolve jobs directory at backend/jobs
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        app_dir = backend_dir / "app"
        jobs_dir = str(backend_dir / "jobs")
        os.makedirs(jobs_dir, exist_ok=True)
        jobdir_path = os.path.join(jobs_dir, job_id)

        # Build path to the run_spider.py script
        run_spider_script = str(Path(__file__).resolve().parent / "run_spider.py")

        if not os.path.exists(run_spider_script):
            error_msg = f"run_spider.py not found at {run_spider_script}"
            logger.error(f"[CrawlerJob:{job_id}] {error_msg}")
            _update_job_in_db(job_id, status="failed", error_message=error_msg)
            return

        # تنظیم PYTHONPATH برای اینکه subprocess بتواند ماژول‌های پروژه را import کند
        env = os.environ.copy()
        pythonpath = f"{backend_dir}{os.pathsep}{app_dir}"
        if 'PYTHONPATH' in env and env['PYTHONPATH']:
            env['PYTHONPATH'] = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = pythonpath

        # در محیط داکر، ریشه با /app هم ارجاع می‌شود
        if os.path.exists("/app") and "/app" not in env['PYTHONPATH']:
            env['PYTHONPATH'] = f"/app{os.pathsep}{env['PYTHONPATH']}"

        # Pre-execution validation for JS render dependencies (Playwright & Chromium)
        if js_render:
            try:
                import playwright
            except ImportError:
                logger.error(f"[CrawlerJob:{job_id}] Playwright is not installed in the python environment.")
                _update_job_in_db(
                    job_id,
                    status="failed",
                    error_message="Playwright is not installed in the python environment. Run 'pip install playwright'."
                )
                return

            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    executable = p.chromium.executable_path
                    if not os.path.exists(executable):
                        logger.warning(f"[CrawlerJob:{job_id}] Playwright Chromium executable not found at {executable}. Attempting auto-installation...")
                        install_proc = await asyncio.create_subprocess_exec(
                            sys.executable, "-m", "playwright", "install", "chromium"
                        )
                        await install_proc.wait()
                        if install_proc.returncode != 0:
                            raise RuntimeError(f"Playwright installation exited with non-zero code {install_proc.returncode}")
            except Exception as e:
                logger.error(f"[CrawlerJob:{job_id}] Playwright Chromium check/installation failed: {str(e)}")
                _update_job_in_db(
                    job_id,
                    status="failed",
                    error_message=f"Playwright Chromium browser is not installed and auto-installation failed: {str(e)}. Run 'playwright install chromium' on the server."
                )
                return

        # Launch the Scrapy crawler in a separate Python process
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                run_spider_script,
                "--job-id", job_id,
                "--url", url,
                "--max-pages", str(max_pages),
                "--max-depth", str(max_depth),
                "--concurrency", str(concurrency),
                "--js-render", str(js_render),
                "--follow-external", str(follow_external),
                "--respect-robots", str(respect_robots),
                "--label", label or "",
                "--widget-id", str(widget_id or 0),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(backend_dir),
            )

            # Wait for Scrapy process to complete with timeout
            timeout_seconds = getattr(settings.crawler, "job_timeout_seconds", 3600)
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(), timeout=float(timeout_seconds)
                )
            except asyncio.TimeoutError:
                logger.warning(f"[CrawlerJob:{job_id}] Job exceeded timeout of {timeout_seconds} seconds. Terminating subprocess...")
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"[CrawlerJob:{job_id}] Subprocess did not terminate. Killing...")
                        process.kill()
                        await process.wait()
                except Exception as kill_err:
                    logger.error(f"[CrawlerJob:{job_id}] Error while terminating/killing subprocess: {str(kill_err)}")

                _update_job_in_db(
                    job_id,
                    status="failed",
                    error_message=f"Crawl job timed out after {timeout_seconds} seconds."
                )
                return

            # ========== لاگ کامل خروجی ==========
            if stdout_data:
                stdout_str = stdout_data.decode('utf-8', errors='replace')
                logger.info(f"[CrawlerJob:{job_id}] ===== Spider STDOUT =====\n{stdout_str[:5000]}")
                
            if stderr_data:
                stderr_str = stderr_data.decode('utf-8', errors='replace')
                logger.error(f"[CrawlerJob:{job_id}] ===== Spider STDERR =====\n{stderr_str[:5000]}")

            # Check return code
            if process.returncode != 0:
                if not _is_job_cancelled(job_id):
                    error_output = stderr_data.decode('utf-8', errors='replace') if stderr_data else "No error output captured"
                    logger.error(
                        f"[CrawlerJob:{job_id}] Subprocess exited with non-zero code {process.returncode}."
                    )
                    _update_job_in_db(
                        job_id,
                        status="failed",
                        error_message=f"Scrapy subprocess error (code {process.returncode}): {error_output[:500]}"
                    )
                    return
        except Exception as proc_err:
            logger.error(f"[CrawlerJob:{job_id}] Subprocess execution failed: {str(proc_err)}")
            _update_job_in_db(job_id, status="failed", error_message=f"Subprocess start failure: {str(proc_err)}")
            return

        # Read final stats and status from DB
        pages_crawled = 0
        pages_failed = 0
        db_status = "running"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT status, pages_crawled, pages_failed FROM crawler_jobs WHERE job_id = %s", (job_id,))
                row = cur.fetchone()
                if row:
                    db_status = row["status"]
                    pages_crawled = row["pages_crawled"] or 0
                    pages_failed = row["pages_failed"] or 0
        except Exception as e:
            logger.error(f"[CrawlerJob:{job_id}] Failed to read final job state from database: {str(e)}")
        finally:
            if conn:
                conn.close()

        # Handle cancellation: keep jobdir and exit gracefully
        if db_status == "cancelled" or _is_job_cancelled(job_id):
            logger.info(f"[CrawlerJob:{job_id}] Crawl job was cancelled. Keeping state directory for potential resumption.")
            _update_job_in_db(job_id, status="cancelled")
            return

        committed_chunks = 0
        if pages_crawled > 0:
            try:
                logger.info(f"[CrawlerJob:{job_id}] Scrapy crawl complete. Committing staged data atomically...")
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
                error_message="No pages were crawled successfully."
            )

        # Clean up jobdir on success or total failure (not cancelled)
        if final_status == "completed" or (final_status == "failed" and pages_crawled == 0):
            try:
                if os.path.exists(jobdir_path):
                    shutil.rmtree(jobdir_path, ignore_errors=True)
                    logger.info(f"[CrawlerJob:{job_id}] Cleaned up job state directory: {jobdir_path}")
            except Exception as clean_err:
                logger.warning(f"[CrawlerJob:{job_id}] Failed to clean up job directory: {str(clean_err)}")

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
