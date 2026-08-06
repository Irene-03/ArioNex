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
import io
import logging

import fitz
from docx import Document as Doc
from PIL import Image

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_and_audit

logger = logging.getLogger("arionex.unstructured_processor")

# ------------------------------------------------------------------
# Lazy-loaded PaddleOCR (single global instance)
# ------------------------------------------------------------------
_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(use_angle_cls=True, lang='fa', use_gpu=False)
            logger.info("PaddleOCR initialised (lang=fa, use_gpu=False)")
        except ImportError:
            logger.error("PaddleOCR not installed. Run: pip install paddleocr")
            raise
    return _ocr_instance


def _reshape_persian(text: str) -> str:
    """Reshape Arabic/Persian characters and apply BiDi algorithm.
    WARNING: get_display() reverses the string logically which breaks vector embeddings and LLMs!
    We should rely on logical text ordering.
    """
    return text


def _page_has_meaningful_text(text: str, min_chars: int = 15) -> bool:
    """Return True if extracted text is long enough to be real (not scanned/garbled)."""
    text = text.strip()
    if len(text) < min_chars:
        return False
    alpha = sum(1 for ch in text if ch.isalpha() or ch.isspace())
    return alpha > len(text) * 0.3


def _extract_page_fitz(page) -> str:
    """Stage 1: fast text extraction via PyMuPDF."""
    text = page.get_text()
    return _reshape_persian(text) if text.strip() else ""


def _extract_page_ocr(page, dpi: int = 300) -> str:
    """Stage 2: OCR fallback via PaddleOCR for scanned pages."""
    try:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    except Exception:
        return ""

    ocr = _get_ocr()
    try:
        result = ocr.ocr(img, cls=True)
    except Exception:
        return ""

    if not result or not result[0]:
        return ""

    lines = []
    for line_info in result[0]:
        text, conf = line_info[1]
        if conf and conf > 0.3:
            lines.append(text)
    return "\n".join(lines)


def split_into_semantic_windows(text: str, window_size: int = 3000, overlap: int = 500) -> list:
    """
    /// <summary>
    /// تقسیم متون بزرگ به پنجره‌های معنایی با اندازه و همپوشانی مشخص
    /// </summary>
    """
    if len(text) <= window_size:
        return [text]
        
    windows = []
    start = 0
    while start < len(text):
        end = start + window_size
        chunk = text[start:end]
        windows.append(chunk)
        start += (window_size - overlap)
        if start >= len(text) - overlap:
            break
            
    if start < len(text):
        windows.append(text[start:])
        
    return windows


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
        /// پایپ‌لاین دو مرحله‌ای استخراج متن از PDF:
        ///   1. PyMuPDF (fitz) — استخراج سریع متن در صورت وجود لایه متنی
        ///   2. PaddleOCR    — تشخیص حروف تصویری برای صفحات اسکن‌شده
        /// </summary>
        """
        text_content = []
        try:
            doc = fitz.open(file_path)
            total = len(doc)
            logger.info(f"PDF opened via PyMuPDF: {total} page(s)")

            for i in range(total):
                page = doc[i]

                # مرحله ۱: استخراج سریع با PyMuPDF
                page_text = _extract_page_fitz(page)

                if _page_has_meaningful_text(page_text):
                    text_content.append(page_text)
                else:
                    # مرحله ۲: برگشت به PaddleOCR برای صفحه اسکن‌شده
                    logger.info(f"Page {i+1}/{total}: low-quality text → PaddleOCR fallback")
                    ocr_text = _extract_page_ocr(page)
                    text_content.append(ocr_text if ocr_text.strip() else page_text)

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
        pii_masked_count = 0
        if settings.security.pii_redaction:
            redacted_text, pii_audit = redact_and_audit(normalized_text)
            pii_masked_count = sum(pii_audit.values())
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
            
            # ۷. راه‌اندازی فرآیند استخراج دانش (موجودیت‌ها و قوانین) به صورت ناهمزمان در پس‌زمینه (Celery Tasks)
            if settings.services.entity_extractor or settings.services.rule_extractor:
                logger.info(f"Dispatching background consolidated knowledge extraction task for file_id={file_id}...")
                from app.tasks.extractor_tasks import run_knowledge_extraction_pipeline_task
                run_knowledge_extraction_pipeline_task.delay(
                    text=redacted_text,
                    file_id=file_id,
                    run_entities=settings.services.entity_extractor,
                    run_rules=settings.services.rule_extractor
                )
            
            return {
                "status": "success",
                "chunks_count": chunks_indexed,
                "storage_url": archive_url,
                "pii_masked_count": pii_masked_count
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
