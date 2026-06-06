"""
/// <summary>
/// روتر آپلود اسناد آریونکس — POST /v1/upload (ArioNex Document Upload Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت آپلود و پردازش اسناد را تعریف می‌کند.
/// منطق کامل pipeline پردازش در upload_logic.py قرار دارد.
///
/// اندپوینت‌ها:
///   POST /v1/upload  — آپلود فایل با مسیریابی هوشمند به پردازشگر مناسب
/// </remarks>
"""

from fastapi import APIRouter, File, UploadFile
from app.logics.upload_logic import execute_upload_logic

router = APIRouter(prefix="/v1", tags=["Upload — Document Ingestion"])


@router.post(
    "/upload",
    summary="آپلود و پردازش سند با مسیریابی هوشمند",
    description="فایل آپلود شده را بر اساس نوع (PDF, DOCX, CSV, TXT) به پردازشگر مناسب هدایت کرده و در پایگاه داده ایندکس می‌کند.",
)
async def upload_and_ingest_file(file: UploadFile = File(...)):
    """
    /// <summary>
    /// اندپوینت آپلود سند با سیستم Safety Airlock و مسیریابی هوشمند
    /// </summary>
    /// <param name="file">فایل فیزیکی آپلود شده (PDF, DOCX, CSV, TXT)</param>
    /// <returns>شناسه فایل، تعداد chunks ایندکس شده، آدرس آرشیو و آمار PII</returns>
    """
    return await execute_upload_logic(file)
