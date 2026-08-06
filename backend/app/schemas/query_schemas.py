"""
/// <summary>
/// ArioNex RAG Query & Response Schemas (ArioNex RAG Query & Response Schemas)
/// </summary>
/// <remarks>
/// This module defines the data structures for the input and output of the RAG query endpoints.
/// Both /v1/query and /v1/widget/chat endpoints use these schemas.
///
/// QueryRequest: user query request with file filter support
/// QueryResponse: assistant answer including text, cited sources, and safety status
/// </remarks>
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    /// <summary>
    /// RAG query request model from the user
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
    /// Response model of the smart RAG assistant
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
