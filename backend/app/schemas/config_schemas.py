"""
/// <summary>
/// مدل‌های Pydantic مدیریت پیکربندی سیستم (ArioNex Configuration Schemas)
/// </summary>
/// <remarks>
/// این ماژول ساختار داده‌ای درخواست‌های تغییر پیکربندی زنده سیستم را تعریف می‌کند.
/// ادمین از طریق اندپوینت POST /v1/config با استفاده از این schema، Feature Toggle‌ها را تغییر می‌دهد.
///
/// تمامی فیلدها Optional هستند — فقط بخش‌هایی که باید تغییر کنند ارسال می‌شوند.
/// </remarks>
"""

from typing import Optional
from pydantic import BaseModel, Field


class ConfigUpdateRequest(BaseModel):
    """
    /// <summary>
    /// مدل درخواست به‌روزرسانی زنده پیکربندی سرویس‌ها، ادغام‌ها و امنیت سیستم
    /// </summary>
    /// <remarks>
    /// هر فیلد یک دیکشنری از نام ویژگی → مقدار boolean است.
    /// مثال: {"services": {"web_search": true, "qna_processor": false}}
    /// </remarks>
    """
    services: Optional[dict] = Field(
        default=None,
        description="تنظیمات Feature Toggle سرویس‌های پردازشی — کلید: نام سرویس، مقدار: bool"
    )
    integrations: Optional[dict] = Field(
        default=None,
        description="تنظیمات روشن/خاموش بودن کانال‌های ارتباطی — Telegram, Widget, REST API"
    )
    security: Optional[dict] = Field(
        default=None,
        description="تنظیمات امنیتی — PII Redaction، Non-Hallucination و..."
    )
    providers: Optional[dict] = Field(
        default=None,
        description="تنظیمات روشن/خاموش بودن پروایدرهای هوش مصنوعی"
    )
