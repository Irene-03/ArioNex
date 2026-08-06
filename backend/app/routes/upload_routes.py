"""
/// <summary>
/// ArioNex Document Upload Router — POST /v1/upload (ArioNex Document Upload Router)
/// </summary>
/// <remarks>
/// This module defines the document upload and processing endpoint.
/// The full processing pipeline logic lives in upload_logic.py.
///
/// Endpoints:
///   POST /v1/upload  — upload a file with smart routing to the appropriate processor
/// </remarks>
"""

from fastapi import APIRouter, File, UploadFile
from app.logics.upload_logic import execute_upload_logic

router = APIRouter(prefix="/v1", tags=["Upload — Document Ingestion"])


@router.post(
    "/upload",
    summary="آپلود و پردازش سند با مسیریابی هوشمند",
    description="فایل آپلود شده را بر اساس نوع (PDF, DOCX, CSV, TXT, JPG, PNG) به پردازشگر مناسب هدایت کرده و در پایگاه داده ایندکس می‌کند. تصاویر (JPG/PNG) از طریق موتور OCR استخراج و وارد RAG می‌شوند.",
)
async def upload_and_ingest_file(file: UploadFile = File(...)):
    """
    /// <summary>
    /// Document upload endpoint with the Safety Airlock system and smart routing
    /// </summary>
    /// <param name="file">The physical uploaded file (PDF, DOCX, CSV, TXT, JPG, PNG)</param>
    /// <returns>File ID, number of indexed chunks, archive URL, and PII stats</returns>
    """
    return await execute_upload_logic(file)
