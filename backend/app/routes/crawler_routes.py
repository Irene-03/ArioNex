"""
/// <summary>
/// روتر ماژول کرالر وب آریونکس (ArioNex Web Crawler Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت‌های مدیریت job‌های کرال را تعریف می‌کند.
/// منطق کامل در crawler_logic.py قرار دارد.
///
/// اندپوینت‌ها:
///   POST   /v1/crawl/start          — شروع job کرال جدید با URL و تنظیمات
///   GET    /v1/crawl/jobs           — لیست تمام job‌ها با pagination
///   GET    /v1/crawl/{job_id}       — وضعیت real-time یک job خاص
///   DELETE /v1/crawl/{job_id}       — لغو یک job در حال اجرا
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
    /// اندپوینت شروع یک job کرال — فوری پاسخ می‌دهد و کرال را در پس‌زمینه اجرا می‌کند
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
    /// اندپوینت لیست job‌های کرال با پشتیبانی از pagination و فیلتر وضعیت
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
    /// اندپوینت وضعیت job — برای polling real-time از فرانت‌اند استفاده می‌شود
    /// </summary>
    /// <param name="job_id">شناسه یکتای job</param>
    """
    return await execute_get_crawl_status(job_id)


@router.delete(
    "/{job_id}",
    summary="لغو یک job کرال",
    description="یک job در حال اجرا یا در صف را لغو می‌کند.",
)
async def cancel_crawl_job(job_id: str) -> dict:
    """
    /// <summary>
    /// اندپوینت لغو job کرال
    /// </summary>
    /// <param name="job_id">شناسه یکتای job</param>
    """
    return await execute_cancel_crawl_job(job_id)


@router.post(
    "/{job_id}/resume",
    response_model=CrawlStartResponse,
    summary="رزومه کردن یک job کرال",
    description="یک job کرال قبلاً متوقف یا ناموفق شده را با استفاده از jobdir رزومه می‌کند.",
)
async def resume_crawl_job(job_id: str) -> CrawlStartResponse:
    """
    /// <summary>
    /// اندپوینت رزومه کردن job کرال
    /// </summary>
    /// <param name="job_id">شناسه یکتای job</param>
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
    /// اندپوینت حذف پوشه حالت کرال
    /// </summary>
    /// <param name="job_id">شناسه یکتای job</param>
    """
    return await execute_delete_jobdir(job_id)
