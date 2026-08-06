"""
/// <summary>
/// ArioNex Upload Business Logic (ArioNex Upload Business Logic)
/// </summary>
/// <remarks>
/// This module separates the logic of receiving an uploaded file, smart routing, and sanitization from the router layer.
/// Responsibilities:
///   1. Temporarily store the file physically
///   2. PII Redaction preview for text files
///   3. Smart CSV type detection with csv_detector
///   4. Route to the appropriate processor (QnA / Structured / Unstructured)
///   5. Clean up the temporary file after processing
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
    /// Runs the full upload pipeline: temporary storage → PII → type detection → specialized processing → cleanup
    /// </summary>
    /// <param name="file">File uploaded via multipart form</param>
    /// <returns>Result dict including file_id, chunk count, archive URL, and PII stats</returns>
    /// <remarks>
    /// The temporary file is deleted in the finally block even on error, so the server disk stays free.
    /// Supported formats: PDF, DOCX, DOC, TXT, JSON, XML, MMD, CSV, JPG, JPEG, PNG
    /// </remarks>
    """
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())

    # Create a secure temporary directory on the server
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)

    try:
        # 1. Physically store the uploaded file, enforcing the file size limit (max 20 MB)
        MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
        total_size = 0
        with open(temp_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="حجم فایل آپلود شده بیش از حد مجاز (۲۰ مگابایت) است."
                    )
                buffer.write(chunk)

        file_id = get_next_file_id()

        # Convert Excel files to CSV for unified processing in the computing system
        if ext in (".xlsx", ".xls"):
            import pandas as pd
            try:
                df = pd.read_excel(temp_path)
                temp_csv_path = temp_path.replace(ext, ".csv")
                df.to_csv(temp_csv_path, index=False, encoding='utf-8')
                
                # Update the file info to the new format
                temp_path = temp_csv_path
                filename = os.path.splitext(filename)[0] + ".csv"
                ext = ".csv"
                logger.info(f"Successfully converted Excel to CSV: {filename}")
            except Exception as e:
                logger.error(f"Excel conversion failed: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to read/convert Excel file: {str(e)}")

        # 2. PII Redaction preview for text/CSV files (for the admin dashboard)
        pii_preview_text = ""
        pii_audit_counts = {}
        if ext in (".txt", ".csv"):
            try:
                with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = "".join([f.readline() for _ in range(5)])
                pii_preview_text, pii_audit_counts = redact_and_audit(sample)
            except Exception:
                pii_preview_text = "Preview unavailable."

        # 3. Smart routing to the specialized worker
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

        elif ext in (".jpg", ".jpeg", ".png"):
            result_data = unstructured_processor.process_image(temp_path, filename, file_id)
            result_data["processor_type"] = "image_ocr"

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

        # Register the file in the database for the ACL/RBAC system
        from app.core.database import get_db_connection
        pii_total_masked = result_data.get("pii_masked_count", 0) or 0
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (id, filename, file_type, min_role_required, pii_masked_count)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        file_type = EXCLUDED.file_type,
                        pii_masked_count = EXCLUDED.pii_masked_count
                    """,
                    (file_id, filename, ext[1:] if ext.startswith('.') else ext, "Analyst", pii_total_masked)
                )
                conn.commit()
        except Exception as db_err:
            logger.error(f"Failed to record document metadata in database: {str(db_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        # 4. Return the final results
        return {
            "file_id": file_id,
            "filename": filename,
            "status": "success",
            "processor": result_data.get("processor_type"),
            "chunks_indexed": result_data.get("chunks_count", 0),
            "archive_url": result_data.get("storage_url", "local"),
            "pii_audit_counts": pii_audit_counts,
            "pii_preview": pii_preview_text,
            "pii_masked_count": pii_total_masked,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload and ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(e)}")
    finally:
        # Delete the temporary directory in all cases (even on error)
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
