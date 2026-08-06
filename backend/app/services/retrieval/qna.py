"""
/// <summary>
/// عامل جستجوی الگوهای Q&A متداول و لاگ‌های پشتیبانی (ArioNex QnA Retrieval Agent)
/// </summary>
/// <remarks>
/// این ماژول بر روی الگوهای پرسش و پاسخ ثبت شده در جدول qna_query جستجوی شباهت معنایی انجام می‌دهد.
/// هدف این عامل پیدا کردن مستقیم لوپ‌های چت پرسش و پاسخ پیشین سازمانی و تیکت‌ها است.
/// </remarks>
"""

import logging
from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding_cached

logger = logging.getLogger("arionex.qna")

class QnAAgent:
    """
    /// <summary>
    /// کلاس عامل جستجوی Q&A جهت تطبیق مستقیم الگوهای پرسش‌وپاسخ سازمانی
    /// </summary>
    """
    def __init__(self):
        # بررسی روشن بودن ماژول در تنظیمات ویژگی‌ها
        self.is_enabled = settings.services.qna_processor

    def retrieve_context(self, query: str, threshold: float = 0.5, k: int = 4, file_ids: list[int] = None, filters: dict = None, embedding: list = None) -> list[dict]:
        """
        /// <summary>
        /// بازیابی معنایی و تطبیق مستقیم الگوهای Q&A از جدول qna_query
        /// </summary>
        /// <param name="query">جستار بازنویسی شده مستقل کاربر</param>
        /// <param name="threshold">حد آستانه شباهت کسینوسی (پیش‌فرض: ۰.۵)</param>
        /// <param name="k">تعداد رکوردهای بازگشتی (پیش‌فرض: ۴)</param>
        /// <param name="file_ids">شناسه‌های فایل محدودکننده RAG</param>
        /// <param name="filters">فیلترهای سفارشی‌سازی داینامیک</param>
        /// <param name="embedding">بردار از پیش محاسبه‌شده پرسش (در صورت وجود) برای حذف فراخوانی تکراری API</param>
        /// <returns>لیستی از الگوهای پرسش و پاسخ متناظر یافت شده فوق آستانه</returns>
        """
        if not self.is_enabled:
            logger.info("Support Lead Agent is disabled in config.yaml. Skipping QnA vector retrieval.")
            return []
            
        logger.info(f"Support Lead Agent starting similarity search for query: '{query}'")
        
        # ۱. استخراج امبدینگ ۳۰۷۲ تایی برای جستار ورودی (با کش در صورت عدم ارسال از بیرون)
        if embedding is None:
            embedding = get_embedding_cached(query)
        
        # ۲. فیلترینگ داینامیک بر اساس شناسه‌ها و فیلترهای سفارشی
        filter_clause = ""
        params = [embedding]
        
        if file_ids:
            placeholders = ",".join(["%s"] * len(file_ids))
            filter_clause += f" AND file_id IN ({placeholders})"
            params.extend(file_ids)
            
        if filters:
            for column, value in filters.items():
                if value:
                    if not isinstance(value, (list, tuple)):
                        value = [value]
                    if column == "content":
                        like_clauses = []
                        for val in value:
                            like_clauses.append(f"{column} ILIKE %s")
                            params.append(f"%{val}%")
                        if like_clauses:
                            filter_clause += f" AND ({' OR '.join(like_clauses)})"
                    else:
                        placeholders = ",".join(["%s"] * len(value))
                        filter_clause += f" AND {column} IN ({placeholders})"
                        params.extend(value)
            
        params.append(k)
        
        # ۳. کوئری روی جدول qna_query
        sql = f"""
        SELECT content, file_id, sequence_id,
               1 - (embedding <=> %s::vector) AS similarity
        FROM qna_query
        WHERE TRUE
        {filter_clause}
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        results = []
        conn = None
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                
            for row in rows:
                content, file_id, seq_id, similarity = row
                
                # اعمال فیلتر شباهت آستانه RAG
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": f"Support_Logs_ID_{file_id}" if file_id else "QnA_Template",
                        "file_id": file_id or 0,
                        "sequence_id": seq_id or 0,
                        "similarity": similarity,
                        "source_type": "qna"
                    })
                    
            logger.info(f"Support Lead Agent retrieved {len(results)} chunks from qna_query above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Support Lead Agent database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results


# نمونه سراسری عامل جستجوی Q&A
qna_agent = QnAAgent()
