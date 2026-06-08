"""
/// <summary>
/// منطق کسب‌وکار اندپوینت آپلود و پردازش اسناد (ArioNex Upload Business Logic)
/// </summary>
/// <remarks>
/// این ماژول منطق دریافت فایل آپلود شده، مسیریابی هوشمند و ایمن‌سازی آن را از لایه روتر جدا می‌کند.
/// مسئولیت‌ها:
///   ۱. ذخیره موقت فیزیکی فایل
///   ۲. پیش‌نمایش PII Redaction برای فایل‌های متنی
///   ۳. تشخیص هوشمند نوع CSV با csv_detector
///   ۴. مسیریابی به پردازشگر مناسب (QnA / Structured / Unstructured)
///   ۵. پاکسازی فایل موقت پس از پردازش
/// </remarks>
"""

import os
import shutil
import logging
import tempfile

from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.services.workers.unstructured_processor import unstructured_processor
from app.services.workers.qna_processor import qna_processor
from app.services.workers.structured_processor import structured_processor
from app.services.safety.pii_redactor import redact_and_audit
from app.helpers.file_id_generator import get_next_file_id
from app.helpers.csv_detector import detect_csv_type

logger = logging.getLogger("arionex.upload_logic")


async def execute_upload_logic(file: UploadFile) -> dict:
    """
    /// <summary>
    /// اجرای کامل pipeline آپلود: ذخیره موقت → PII → تشخیص نوع → پردازش تخصصی → پاکسازی
    /// </summary>
    /// <param name="file">فایل آپلود شده از طریق multipart form</param>
    /// <returns>دیکشنری نتایج شامل file_id، تعداد chunks، آدرس آرشیو و آمار PII</returns>
    /// <remarks>
    /// فایل موقت در finally block حتی در صورت خطا حذف می‌شود تا هارد سرور خالی بماند.
    /// فرمت‌های پشتیبانی‌شده: PDF, DOCX, DOC, TXT, JSON, XML, MMD, CSV
    /// </remarks>
    """
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())

    # ساخت دایرکتوری موقت امن روی سرور
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)

    try:
        # ۱. ذخیره فیزیکی فایل آپلود شده
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_id = get_next_file_id()

        # ۲. پیش‌نمایش PII Redaction برای فایل‌های متنی/CSV (جهت ادمین داشبورد)
        pii_preview_text = ""
        pii_audit_counts = {}
        if ext in (".txt", ".csv"):
            try:
                with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = "".join([f.readline() for _ in range(5)])
                pii_preview_text, pii_audit_counts = redact_and_audit(sample)
            except Exception:
                pii_preview_text = "Preview unavailable."

        # ۳. مسیریابی هوشمند به کارگر تخصصی
        result_data = {}

        if ext == ".csv":
            csv_type = detect_csv_type(temp_path)
            if csv_type == "qna":
                result_data = qna_processor.process_qna_csv(temp_path, filename, file_id)
                result_data["processor_type"] = "qna_processor"
            else:
                result_data = structured_processor.process_structured_csv(temp_path, filename, file_id)
                result_data["processor_type"] = "structured_analytics"

        elif ext in (".pdf", ".docx", ".doc", ".txt", ".json", ".xml", ".mmd"):
            result_data = unstructured_processor.process_document(temp_path, filename, file_id)
            result_data["processor_type"] = "unstructured_document"

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

        # ثبت فایل در دیتابیس برای سیستم ACL/RBAC
        from app.core.database import get_db_connection
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (id, filename, file_type, min_role_required)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        file_type = EXCLUDED.file_type
                    """,
                    (file_id, filename, ext[1:] if ext.startswith('.') else ext, "Analyst")
                )
                conn.commit()
        except Exception as db_err:
            logger.error(f"Failed to record document metadata in database: {str(db_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        # ۴. بازگرداندن نتایج نهایی
        return {
            "file_id": file_id,
            "filename": filename,
            "status": "success",
            "processor": result_data.get("processor_type"),
            "chunks_indexed": result_data.get("chunks_count", 0),
            "archive_url": result_data.get("storage_url", "local"),
            "pii_audit_counts": pii_audit_counts,
            "pii_preview": pii_preview_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload and ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(e)}")
    finally:
        # حذف دایرکتوری موقت در هر حال (حتی در صورت خطا)
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
