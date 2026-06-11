"""
/// <summary>
/// منطق کسب‌وکار ماژول کرالر وب آریونکس (ArioNex Web Crawler Business Logic)
/// </summary>
/// <remarks>
/// این ماژول لایه business logic کرالر را از لایه روتر جدا می‌کند.
/// مسئولیت‌ها:
///   ۱. ایجاد job کرال در دیتابیس و دریافت job_id یکتا
///   ۲. شروع اجرای async CrawlerService به عنوان BackgroundTask
///   ۳. خواندن وضعیت job برای polling
///   ۴. لیست تمام job‌ها با مرتب‌سازی
///   ۵. لغو job در حال اجرا
/// </remarks>
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.database import get_db_connection
from app.schemas.crawler_schemas import CrawlStartRequest, CrawlStartResponse, CrawlJobResponse
from app.tasks.crawler_task import run_crawler_task

logger = logging.getLogger("arionex.crawler_logic")


def _create_job_in_db(
    job_id: str,
    url: str,
    max_pages: int,
    max_depth: int,
    concurrency: int,
    js_render: bool,
    follow_external: bool,
    label: Optional[str],
    widget_id: Optional[int],
) -> None:
    """
    /// <summary>
    /// درج رکورد job کرال جدید در جدول crawler_jobs
    /// </summary>
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO crawler_jobs
                    (job_id, url, status, max_pages, max_depth, concurrency,
                     js_render, follow_external, label, widget_id)
                VALUES (%s, %s, 'queued', %s, %s, %s, %s, %s, %s, %s)
                """,
                (job_id, url, max_pages, max_depth, concurrency,
                 js_render, follow_external, label, widget_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to create crawler job record: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create crawler job: {str(e)}")
    finally:
        if conn:
            conn.close()


def _row_to_job_response(row: dict) -> CrawlJobResponse:
    """
    /// <summary>
    /// تبدیل رکورد دیتابیس به مدل پاسخ Pydantic
    /// </summary>
    """
    return CrawlJobResponse(
        job_id=row["job_id"],
        url=row["url"],
        status=row["status"],
        pages_crawled=row["pages_crawled"],
        chunks_indexed=row["chunks_indexed"],
        pages_failed=row["pages_failed"],
        max_pages=row["max_pages"],
        max_depth=row["max_depth"],
        js_render=row["js_render"],
        follow_external_domains=row["follow_external"],
        label=row.get("label"),
        widget_id=row.get("widget_id"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def execute_start_crawl(
    request: CrawlStartRequest,
) -> CrawlStartResponse:
    """
    /// <summary>
    /// اجرای منطق شروع job کرال: ایجاد رکورد در DB و راه‌اندازی task پس‌زمینه
    /// </summary>
    /// <param name="request">درخواست شروع کرال از کاربر</param>
    /// <returns>job_id و وضعیت اولیه</returns>
    """
    if not settings.services.web_crawler:
        raise HTTPException(
            status_code=503,
            detail="Web crawler service is currently disabled. Enable it in config.yaml under services.web_crawler."
        )

    # اعتبارسنجی URL
    url = str(request.url).strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    # جمع‌آوری تنظیمات با fallback به config.yaml defaults
    max_pages = request.max_pages or settings.crawler.default_max_pages
    max_depth = request.max_depth or settings.crawler.default_max_depth
    concurrency = request.concurrency or settings.crawler.default_concurrency
    js_render = request.js_render or settings.crawler.js_render
    follow_external = request.follow_external_domains or settings.crawler.follow_external_domains

    # ایجاد job_id یکتا
    job_id = str(uuid.uuid4())

    logger.info(
        f"Creating new crawler job [{job_id}] for URL: {url} "
        f"(pages={max_pages}, depth={max_depth}, js={js_render}, external={follow_external})"
    )

    # ثبت job در دیتابیس
    _create_job_in_db(
        job_id=job_id,
        url=url,
        max_pages=max_pages,
        max_depth=max_depth,
        concurrency=concurrency,
        js_render=js_render,
        follow_external=follow_external,
        label=request.label,
        widget_id=request.widget_id,
    )

    # شروع Celery Task در پس‌زمینه
    run_crawler_task.delay(
        job_id=job_id,
        url=url,
        max_pages=max_pages,
        max_depth=max_depth,
        concurrency=concurrency,
        js_render=js_render,
        follow_external=follow_external,
        respect_robots=request.respect_robots,
        label=request.label or "",
        widget_id=request.widget_id or 0
    )


    return CrawlStartResponse(
        job_id=job_id,
        status="queued",
        message=f"Crawler job created and queued. Poll GET /v1/crawl/{job_id} for real-time status.",
        url=url,
    )


async def execute_get_crawl_status(job_id: str) -> CrawlJobResponse:
    """
    /// <summary>
    /// دریافت وضعیت real-time یک job کرال
    /// </summary>
    /// <param name="job_id">شناسه یکتای job</param>
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM crawler_jobs WHERE job_id = %s",
                (job_id,)
            )
            row = cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to query crawler job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to query crawler job status")
    finally:
        if conn:
            conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Crawler job '{job_id}' not found")

    return _row_to_job_response(row)


async def execute_list_crawl_jobs(
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None
) -> list[CrawlJobResponse]:
    """
    /// <summary>
    /// لیست تمام job‌های کرال با مرتب‌سازی از جدیدترین به قدیمی‌ترین
    /// </summary>
    /// <param name="limit">تعداد رکوردها در هر صفحه</param>
    /// <param name="offset">تعداد رکوردهای skip شده (برای pagination)</param>
    /// <param name="status_filter">فیلتر بر اساس وضعیت (queued/running/completed/failed)</param>
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if status_filter:
                cur.execute(
                    "SELECT * FROM crawler_jobs WHERE status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (status_filter, limit, offset)
                )
            else:
                cur.execute(
                    "SELECT * FROM crawler_jobs ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to list crawler jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crawler jobs")
    finally:
        if conn:
            conn.close()

    return [_row_to_job_response(row) for row in rows]


async def execute_cancel_crawl_job(job_id: str) -> dict:
    """
    /// <summary>
    /// لغو یک job کرال در حال اجرا
    /// </summary>
    /// <remarks>
    /// این متد وضعیت job را در دیتابیس به 'cancelled' تغییر می‌دهد.
    /// از آنجایی که task پس‌زمینه هر iteration وضعیت را چک نمی‌کند،
    /// لغو واقعی در نسخه بعدی با asyncio.Event پیاده‌سازی می‌شود.
    /// </remarks>
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT status FROM crawler_jobs WHERE job_id = %s",
                (job_id,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"Crawler job '{job_id}' not found")

            current_status = row["status"]
            if current_status in ("completed", "failed", "cancelled"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot cancel job in status '{current_status}'"
                )

            cur.execute(
                "UPDATE crawler_jobs SET status = 'cancelled', updated_at = %s WHERE job_id = %s",
                (datetime.utcnow(), job_id)
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel crawler job {job_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel crawler job")
    finally:
        if conn:
            conn.close()

    logger.info(f"Crawler job {job_id} marked as cancelled.")
    return {"message": f"Job '{job_id}' has been marked as cancelled", "job_id": job_id}
