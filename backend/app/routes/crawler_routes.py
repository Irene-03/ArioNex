"""
/// <summary>
/// ArioNex Web Crawler Router (ArioNex Web Crawler Router)
/// </summary>
/// <remarks>
/// This module defines the endpoints for managing crawl jobs.
/// The full logic lives in crawler_logic.py.
///
/// Endpoints:
///   POST   /v1/crawl/start          — start a new crawl job with a URL and settings
///   GET    /v1/crawl/jobs           — list all jobs with pagination
///   GET    /v1/crawl/{job_id}       — real-time status of a specific job
///   DELETE /v1/crawl/{job_id}       — cancel a running job
/// </remarks>
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.logics.crawler_logic import (
    execute_cancel_crawl_job,
    execute_get_crawl_status,
    execute_list_crawl_jobs,
    execute_start_crawl,
    execute_resume_crawl,
    execute_delete_jobdir,
)
from app.schemas.crawler_schemas import (
    CrawlJobResponse,
    CrawlStartRequest,
    CrawlStartResponse,
)

router = APIRouter(prefix="/v1/crawl", tags=["Crawler — Website Knowledge Ingestion"])


@router.post(
    "/start",
    response_model=CrawlStartResponse,
    summary="شروع job کرال وب‌سایت",
    description=(
        "یک job کرال async جدید برای وب‌سایت داده شده ایجاد می‌کند. "
        "job_id برمی‌گرداند که برای polling وضعیت استفاده می‌شود. "
        "محتوای صفحات به صورت خودکار chunk و ایندکس می‌شوند."
    ),
)
async def start_crawl_job(
    request: CrawlStartRequest,
) -> CrawlStartResponse:
    """
    /// <summary>
    /// Endpoint to start a crawl job — responds immediately and runs the crawl in the background
    /// </summary>
    """
    return await execute_start_crawl(request)


@router.get(
    "/jobs",
    response_model=list[CrawlJobResponse],
    summary="لیست تمام job‌های کرال",
    description="تمام job‌های کرال را با مرتب‌سازی از جدیدترین به قدیمی‌ترین برمی‌گرداند.",
)
async def list_crawl_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="تعداد رکورد در هر صفحه"),
    offset: int = Query(default=0, ge=0, description="تعداد رکوردهای skip شده"),
    status: Optional[str] = Query(
        default=None,
        description="فیلتر بر اساس وضعیت: queued / running / completed / failed / cancelled",
    ),
) -> list[CrawlJobResponse]:
    """
    /// <summary>
    /// Endpoint to list crawl jobs with pagination and status filter support
    /// </summary>
    """
    return await execute_list_crawl_jobs(limit=limit, offset=offset, status_filter=status)


@router.get(
    "/{job_id}",
    response_model=CrawlJobResponse,
    summary="وضعیت یک job کرال",
    description="وضعیت real-time یک job کرال را برمی‌گرداند. برای monitoring مناسب است.",
)
async def get_crawl_job_status(job_id: str) -> CrawlJobResponse:
    """
    /// <summary>
    /// Job status endpoint — used for real-time polling from the frontend
    /// </summary>
    /// <param name="job_id">Unique job ID</param>
    """
    return await execute_get_crawl_status(job_id)


@router.delete(
    "/{job_id}",
    summary="لغو یا حذف کامل یک job کرال",
    description="یک job در حال اجرا را لغو می‌کند، یا در صورت ارسال hard_delete، تاریخچه آن را کاملاً حذف می‌کند.",
)
async def cancel_crawl_job(
    job_id: str,
    hard_delete: bool = Query(default=False, description="آیا تاریخچه کاملا پاک شود؟")
) -> dict:
    """
    /// <summary>
    /// Endpoint to cancel a crawl job or delete its history
    /// </summary>
    /// <param name="job_id">Unique job ID</param>
    """
    return await execute_cancel_crawl_job(job_id, hard_delete=hard_delete)


@router.post(
    "/{job_id}/resume",
    response_model=CrawlStartResponse,
    summary="رزومه کردن یک job کرال",
    description="یک job کرال قبلاً متوقف یا ناموفق شده را با استفاده از jobdir رزومه می‌کند.",
)
async def resume_crawl_job(job_id: str) -> CrawlStartResponse:
    """
    /// <summary>
    /// Endpoint to resume a crawl job
    /// </summary>
    /// <param name="job_id">Unique job ID</param>
    """
    return await execute_resume_crawl(job_id)


@router.delete(
    "/{job_id}/jobdir",
    summary="حذف حالت و فایل‌های موقت job کرال",
    description="پوشه حالت (jobdir) و فایل‌های موقت MinIO مربوط به یک job کرال را حذف می‌کند تا دیگر قابل رزومه نباشد.",
)
async def delete_crawl_jobdir(job_id: str) -> dict:
    """
    /// <summary>
    /// Endpoint to delete the crawl state folder
    /// </summary>
    /// <param name="job_id">Unique job ID</param>
    """
    return await execute_delete_jobdir(job_id)
