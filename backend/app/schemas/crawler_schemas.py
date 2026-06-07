"""
/// <summary>
/// اسکیمای درخواست و پاسخ ماژول کرالر وب آریونکس (ArioNex Web Crawler Schemas)
/// </summary>
/// <remarks>
/// این ماژول مدل‌های Pydantic برای اعتبارسنجی ورودی و خروجی اندپوینت‌های کرالر را تعریف می‌کند.
/// </remarks>
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class CrawlStartRequest(BaseModel):
    """
    /// <summary>
    /// مدل درخواست شروع یک job کرال جدید
    /// </summary>
    /// <remarks>
    /// تمامی پارامترها به جز url اختیاری هستند و مقادیر پیش‌فرض از config.yaml خوانده می‌شوند.
    /// </remarks>
    """
    url: str = Field(
        ...,
        description="آدرس URL ریشه برای شروع کرال (مثال: https://example.com)",
        examples=["https://example.com"]
    )
    max_pages: int = Field(
        default=50,
        ge=1,
        le=500,
        description="حداکثر تعداد صفحاتی که کرال می‌شوند"
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="حداکثر عمق لینک از URL ریشه"
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="تعداد درخواست‌های HTTP همزمان"
    )
    js_render: bool = Field(
        default=False,
        description="رندر صفحات JavaScript (React/Vue/Angular) با Playwright — نیاز به نصب playwright"
    )
    follow_external_domains: bool = Field(
        default=False,
        description="دنبال کردن لینک‌های خارجی (خارج از دامنه اصلی) با سختگیری زیاد"
    )
    respect_robots: bool = Field(
        default=True,
        description="رعایت دستورالعمل‌های robots.txt سایت هدف"
    )
    widget_id: Optional[int] = Field(
        default=None,
        description="شناسه ابزارک وب‌سایت مرتبط (اتصال اختیاری برای popup widget)"
    )
    label: Optional[str] = Field(
        default=None,
        max_length=255,
        description="لیبل سفارشی برای chunk‌ها در دیتابیس (پیش‌فرض: crawled:{domain})"
    )


class CrawlJobResponse(BaseModel):
    """
    /// <summary>
    /// مدل پاسخ وضعیت یک job کرال
    /// </summary>
    """
    job_id: str
    url: str
    status: str
    pages_crawled: int
    chunks_indexed: int
    pages_failed: int
    max_pages: int
    max_depth: int
    js_render: bool
    follow_external_domains: bool
    label: Optional[str]
    widget_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlStartResponse(BaseModel):
    """
    /// <summary>
    /// پاسخ فوری پس از شروع یک job کرال — شامل job_id برای polling وضعیت
    /// </summary>
    """
    job_id: str
    status: str
    message: str
    url: str
