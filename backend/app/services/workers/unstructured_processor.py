"""
/// <summary>
/// پردازشگر اسناد عمومی و بدون ساختار (Unstructured Document Ingestion Worker)
/// </summary>
/// <remarks>
/// این ماژول وظیفه لود کردن فایل‌های PDF، Word و متنی خام، استخراج محتوا، اعمال ایرلاک امنیتی،
/// چانک‌سازی هوشمند، و در نهایت تولید وکتورها و ذخیره‌سازی قطعات در دیتابیس PostgreSQL را بر عهده دارد.
/// </remarks>
"""

import os
import logging
from pypdf import PdfReader
from docx import Document as Doc

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text

logger = logging.getLogger("arionex.unstructured_processor")

class UnstructuredDocumentProcessor:
    """
    /// <summary>
    /// کلاس پردازشگر ارشد اسناد متنی، پی‌دی‌اف و مایکروسافت ورد
    /// </summary>
    """
    def __init__(self):
        # بررسی روشن بودن پردازشگر در فیچر تاگل سیستم
        self.is_enabled = settings.services.unstructured_document_processor

    def parse_pdf(self, file_path: str) -> str:
        """
        /// <summary>
        /// استخراج تمام متون درون فایل PDF با استفاده از کتابخانه pypdf
        /// </summary>
        """
        text_content = []
        try:
            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"Failed to parse PDF file at {file_path}. Error: {str(e)}")
            raise e

    def parse_docx(self, file_path: str) -> str:
        """
        /// <summary>
        /// استخراج تمام متون درون فایل مایکروسافت ورد (DOCX)
        /// </summary>
        """
        try:
            doc = Doc(file_path)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        except Exception as e:
            logger.error(f"Failed to parse DOCX file at {file_path}. Error: {str(e)}")
            raise e

    def parse_txt(self, file_path: str) -> str:
        """
        /// <summary>
        /// خواندن فایل متنی خام معمولی (TXT)
        /// </summary>
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # تلاش با انکودینگ‌های متداول در صورت وجود اشکال یونیکد
            try:
                with open(file_path, "r", encoding="windows-1256") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read TXT file with windows-1256 encoding: {str(e)}")
                raise e
        except Exception as e:
            logger.error(f"Failed to read TXT file at {file_path}. Error: {str(e)}")
            raise e

    def process_document(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// فرآیند اصلی بارگذاری سند: لود فیزیکی، نرمال‌سازی، قفل حریم شخصی، امبدینگ‌سازی و ایندکس برداری
        /// </summary>
        /// <param name="temp_file_path">مسیر فایل فیزیکی موقت روی سرور</param>
        /// <param name="original_filename">نام اصلی فایل آپلود شده</param>
        /// <param name="file_id">شناسه عددی اختصاص یافته به فایل جهت ردیابی منابع در چت</param>
        /// <returns>یک دیکشنری شامل وضعیت موفقیت و تعداد چانک‌های تولید شده</returns>
        """
        if not self.is_enabled:
            logger.warning(f"Unstructured Document Processor is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "chunks_count": 0}
            
        logger.info(f"Starting pipeline ingestion for unstructured file: {original_filename} (ID: {file_id})")
        
        # ۱. استخراج محتوا بر اساس پسوند فایل
        _, ext = os.path.splitext(original_filename.lower())
        raw_text = ""
        
        if ext == ".pdf":
            raw_text = self.parse_pdf(temp_file_path)
        elif ext in [".docx", ".doc"]:
            raw_text = self.parse_docx(temp_file_path)
        elif ext in [".txt", ".json", ".xml", ".mmd"]:
            raw_text = self.parse_txt(temp_file_path)
        else:
            logger.error(f"Unsupported file format: {ext}")
            raise ValueError(f"Unsupported file extension: {ext}")
            
        if not raw_text.strip():
            logger.warning(f"Extracted empty text content from document: {original_filename}")
            return {"status": "empty", "chunks_count": 0}
            
        # ۲. لایه نرمال‌سازی متون فارسی
        normalized_text = normalize_text(raw_text)
        
        # ۳. لایه ایرلاک امنیتی (PII Redaction) در صورت فعال بودن در سیستم
        if settings.security.pii_redaction:
            redacted_text = redact_text(normalized_text)
        else:
            redacted_text = normalized_text
            
        # ۴. شکستن متن به قطعات هم‌پوشان (Chunking)
        chunks = chunk_text(redacted_text, chunk_size=350, overlap=75)
        
        # ۵. آپلود همزمان فایل اصلی به MinIO جهت نگهداری نسخه بایگانی
        try:
            object_name = f"unstructured/{file_id}/{original_filename}"
            # حدس نوع فایل برای هدرها
            content_type = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "text/plain"
            
            archive_url = storage_manager.upload_file(object_name, temp_file_path, content_type)
            logger.info(f"File uploaded and archived at storage endpoint: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving raw file failed: {str(e)}. Continuing chunk indexing anyway.")
            archive_url = "fallback_local"

        # ۶. تولید بردارها و ایندکس در پایگاه داده PostgreSQL + pgvector
        conn = None
        chunks_indexed = 0
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for idx, chunk in enumerate(chunks):
                    sequence_id = idx + 1
                    embedding = get_embedding(chunk)
                    
                    query = """
                        INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s, %s)
                    """
                    cur.execute(query, (chunk, embedding, original_filename, file_id, sequence_id))
                    chunks_indexed += 1
                
                conn.commit()
            logger.info(f"Successfully processed and indexed {chunks_indexed} chunks for file '{original_filename}'.")
            return {
                "status": "success",
                "chunks_count": chunks_indexed,
                "storage_url": archive_url
            }
        except Exception as e:
            logger.error(f"Failed to insert chunks into database: {str(e)}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

# آبجکت سراسری پردازشگر اسناد عمومی
unstructured_processor = UnstructuredDocumentProcessor()
