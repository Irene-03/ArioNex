"""
/// <summary>
/// مدل‌های Pydantic پرسش و پاسخ RAG آریونکس (ArioNex RAG Query & Response Schemas)
/// </summary>
/// <remarks>
/// این ماژول ساختار داده‌ای ورودی و خروجی اندپوینت‌های پرسش RAG را تعریف می‌کند.
/// هر دو اندپوینت /v1/query و /v1/widget/chat از این schema‌ها استفاده می‌کنند.
///
/// QueryRequest: درخواست پرسش کاربر با پشتیبانی از فیلتر فایل
/// QueryResponse: پاسخ دستیار شامل متن، منابع استنادی و وضعیت ایمنی
/// </remarks>
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    /// <summary>
    /// مدل درخواست پرسش RAG از کاربر
    /// </summary>
    """
    query: str = Field(
        ...,
        description="متن پرسش کاربر",
        min_length=1,
        max_length=2000
    )
    session_id: str = Field(
        default="default_session",
        description="شناسه منحصربه‌فرد نشست چت — برای حفظ تاریخچه مکالمه"
    )
    file_ids: Optional[List[int]] = Field(
        default=None,
        description="لیست شناسه‌های فایل جهت محدود کردن جستجوی RAG به اسناد مشخص"
    )


class QueryResponse(BaseModel):
    """
    /// <summary>
    /// مدل پاسخ دستیار هوشمند RAG
    /// </summary>
    """
    answer: str = Field(
        ...,
        description="متن پاسخ نهایی دستیار به فارسی"
    )
    sources: List[dict] = Field(
        default_factory=list,
        description="لیست منابع استنادی استفاده شده در تولید پاسخ"
    )
    is_safe: bool = Field(
        default=True,
        description="وضعیت ایمنی پاسخ — False در صورت تشخیص محتوای نامناسب"
    )
