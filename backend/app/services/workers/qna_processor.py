"""
/// <summary>
/// پردازشگر فایل‌های سوال و جواب متداول و لاگ‌های پشتیبانی (FAQ & Support Logs Ingestion Worker)
/// </summary>
/// <remarks>
/// این ماژول فایل‌های صفحات گسترده (CSV) حاوی پرسش‌ها و پاسخ‌ها را لود کرده، آن‌ها را نرمال‌سازی
/// و ایمن می‌کند، و هر لوپ Q&A را به عنوان یک شناسه مجزا امبد کرده و در جدول qna_query دیتابیس برداری ایندکس می‌کند.
/// </remarks>
"""

import os
import logging
import pandas as pd

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text
from app.services.safety.pii_redactor import redact_text

logger = logging.getLogger("arionex.qna_processor")

class QnaDocumentProcessor:
    """
    /// <summary>
    /// کلاس پردازشگر ارشد فایل‌های اکسل/سی‌اس‌وی حاوی الگوهای پرسش و پاسخ سازمان
    /// </summary>
    """
    def __init__(self):
        # بررسی روشن بودن ماژول در فایل تنظیمات
        self.is_enabled = settings.services.qna_processor

    def process_qna_csv(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// پردازش فایل CSV پرسش و پاسخ: لود ردیف‌ها، قالب‌بندی متون، ماسک اطلاعات و ذخیره در جدول qna_query
        /// </summary>
        /// <param name="temp_file_path">مسیر فایل موقت آپلود شده در سرور</param>
        /// <param name="original_filename">نام اصلی فایل ورودی</param>
        /// <param name="file_id">شناسه منحصر به فرد فایل</param>
        /// <returns>دیکشینری وضعیت اجرا و تعداد لوپ‌های ثبت شده</returns>
        """
        if not self.is_enabled:
            logger.warning(f"QnA Processor is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "chunks_count": 0}
            
        logger.info(f"Starting QnA ingestion pipeline for file: {original_filename} (ID: {file_id})")
        
        # ۱. لود فایل سی‌اس‌وی با استفاده از پانداس
        try:
            # خواندن فایل با تلاش برای انکودینگ‌های متداول
            try:
                df = pd.read_csv(temp_file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding="windows-1256")
                
            # یکدست‌سازی نام ستون‌ها (حذف فواصل خالی)
            df.columns = [col.strip() for col in df.columns]
            
            # بررسی وجود ستون‌های حیاتی پرسش و پاسخ
            question_col = None
            answer_col = None
            
            # تطابق هوشمند با زبان‌های فارسی و انگلیسی ستون‌ها
            for col in df.columns:
                col_lower = col.lower()
                if "question" in col_lower or col == "سوال" or col == "پرسش":
                    question_col = col
                if "answer" in col_lower or col == "جواب" or col == "پاسخ":
                    answer_col = col
                    
            if not question_col or not answer_col:
                # تلاش برای انتخاب ستون اول و دوم به عنوان پیش‌فرض در صورت عدم تطابق نامی
                if len(df.columns) >= 2:
                    question_col = df.columns[0]
                    answer_col = df.columns[1]
                    logger.warning(f"QnA columns not matched. Guessing defaults: Question='{question_col}', Answer='{answer_col}'")
                else:
                    raise ValueError("CSV must contain at least two columns for Question and Answer.")
                    
        except Exception as e:
            logger.error(f"Failed to read or parse QnA CSV file: {str(e)}")
            raise e

        # ۲. آپلود فایل اصلی خام به MinIO جهت مستندسازی و بایگانی
        try:
            object_name = f"qna/{file_id}/{original_filename}"
            archive_url = storage_manager.upload_file(object_name, temp_file_path, "text/csv")
            logger.info(f"QnA raw file archived successfully: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving QnA raw file failed: {str(e)}. Continuing database ingestion.")
            archive_url = "fallback_local"

        # ۳. چرخیدن روی تک‌تک سطرها، تولید چانک‌های پرسش و پاسخ و ذخیره‌سازی وکتورها
        conn = None
        records_indexed = 0
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for idx, row in df.iterrows():
                    q = str(row[question_col]).strip()
                    a = str(row[answer_col]).strip()
                    
                    if not q or q.lower() == "nan" or not a or a.lower() == "nan":
                        continue  # نادیده‌گیری ردیف‌های خالی
                        
                    # قالب‌بندی متون لوپ پرسش و پاسخ
                    formatted_chunk = f"Question: {q}, Answer: {a}"
                    
                    # نرمال‌سازی متون فارسی
                    normalized_chunk = normalize_text(formatted_chunk)
                    
                    # اعمال فیلتر قفل حریم شخصی در صورت روشن بودن
                    if settings.security.pii_redaction:
                        final_chunk = redact_text(normalized_chunk)
                    else:
                        final_chunk = normalized_chunk
                        
                    # تولید امبدینگ ۳۰۷۲ تایی با استفاده از OpenAI
                    embedding = get_embedding(final_chunk)
                    sequence_id = idx + 1
                    
                    query = """
                        INSERT INTO qna_query (content, embedding, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s)
                    """
                    cur.execute(query, (final_chunk, embedding, file_id, sequence_id))
                    records_indexed += 1
                    
                conn.commit()
                
            logger.info(f"Successfully processed and indexed {records_indexed} Q&A records in qna_query.")
            return {
                "status": "success",
                "chunks_count": records_indexed,
                "total_rows": len(df),
                "question_column": question_col,
                "answer_column": answer_col,
                "storage_url": archive_url,
                "pii_masked_count": pii_masked_count
            }
        except Exception as e:
            logger.error(f"Failed to insert QnA records into database: {str(e)}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

# شیء سراسری پردازشگر پرسش و پاسخ‌های سازمان
qna_processor = QnaDocumentProcessor()
