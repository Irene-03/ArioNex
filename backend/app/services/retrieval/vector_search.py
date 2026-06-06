"""
/// <summary>
/// عامل جستجوی برداری اسناد عمومی (ArioNex Vector Search Agent)
/// </summary>
/// <remarks>
/// این ماژول جستجوی شباهت کسینوسی (Cosine Similarity Search) را روی امبدینگ‌های ۳۰۷۲ بعدی
/// در جدول pg_supervisor و pg_dummy انجام می‌دهد و نتایج با فیلترهای داینامیک را استخراج می‌کند.
/// این ماژول متادیتاهای فایل (مانند نام سند، آیدی فایل و شماره سکانس) را همراه با متن بازمی‌گرداند تا
/// در بخش فرانت‌اند چت‌بات به صورت تگ‌های استناد دقیق (Source Tags) نمایش داده شوند.
/// </remarks>
"""

import logging
from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding

logger = logging.getLogger("arionex.vector_search")

class VectorSearchAgent:
    """
    /// <summary>
    /// کلاس عامل جستجوی برداری اسناد جهت بازیابی معنایی از pg_supervisor
    /// </summary>
    """
    def __init__(self):
        # بررسی روشن بودن کارگر اسناد در تنظیمات ویژگی‌ها
        self.is_enabled = settings.services.unstructured_document_processor

    def retrieve_context(self, query: str, threshold: float = 0.5, k: int = 4, file_ids: list[int] = None) -> list[dict]:
        """
        /// <summary>
        /// بازیابی معنایی قطعات متنی مرتبط با جستار کاربر از جداول pg_supervisor و pg_dummy
        /// </summary>
        /// <param name="query">جستار بازنویسی شده مستقل کاربر</param>
        /// <param name="threshold">حد آستانه شباهت کسینوسی کسینوسی (پیش‌فرض: ۰.۵)</param>
        /// <param name="k">حداکثر تعداد چانک‌های بازیابی شده (پیش‌فرض: ۴)</param>
        /// <param name="file_ids">لیست شناسه‌های فایل محدودکننده برای سرور RAG فیلتر شده</param>
        /// <returns>لیستی از دیکشنری‌های چانک‌های بازیابی شده به همراه متادیتا</returns>
        """
        if not self.is_enabled:
            logger.info("Librarian Agent is disabled in config.yaml. Skipping document vector retrieval.")
            return []
            
        logger.info(f"Librarian Agent starting similarity search for query: '{query}'")
        
        # ۱. استخراج بردار امبدینگ ۳۰۷۲ بعدی برای جستار جدید
        embedding = get_embedding(query)
        
        # در صورت تست محلی و عدم وجود API واقعی OpenAI، بردار صفر بازمی‌گردد که جستجو نتیجه کاذب خواهد داد
        # برای پیشگیری از کرش، کوئری را اجرا می‌کنیم
        
        # ۲. ساخت بند فیلتر بر اساس شناسه اسناد در صورت وجود
        filter_clause = ""
        params = [embedding]
        
        if file_ids:
            placeholders = ",".join(["%s"] * len(file_ids))
            filter_clause = f"AND file_id IN ({placeholders})"
            params.extend(file_ids)
            
        params.append(k)
        
        # ۳. اجرای پرس‌وجو روی جدول pg_supervisor با محاسبه فاصله کسینوسی (<=>)
        sql = f"""
        SELECT content, label, file_id, sequence_id,
               1 - (embedding <=> %s::vector) AS similarity
        FROM pg_supervisor
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
                content, label, file_id, seq_id, similarity = row
                
                # اعمال حد آستانه شباهت جهت جلوگیری از ورود اطلاعات نامربوط
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": label or "unnamed_document",
                        "file_id": file_id or 0,
                        "sequence_id": seq_id or 0,
                        "similarity": similarity,
                        "source_type": "document"
                    })
                    
            logger.info(f"Librarian Agent retrieved {len(results)} chunks from pg_supervisor above threshold {threshold}.")
            
            # ۴. در صورت نیاز به نتایج بیشتر و خالی بودن نتایج، جدول pg_dummy را نیز بررسی می‌کنیم
            if len(results) < k:
                remaining_k = k - len(results)
                dummy_sql = """
                SELECT content, 
                       1 - (embedding <=> %s::vector) AS similarity
                FROM pg_dummy
                ORDER BY similarity DESC
                LIMIT %s
                """
                with conn.cursor() as cur:
                    cur.execute(dummy_sql, [embedding, remaining_k])
                    dummy_rows = cur.fetchall()
                    
                for d_row in dummy_rows:
                    content, similarity = d_row
                    if similarity >= threshold:
                        results.append({
                            "content": content,
                            "label": "dummy_general",
                            "file_id": 0,
                            "sequence_id": 0,
                            "similarity": similarity,
                            "source_type": "general"
                        })
                        
        except Exception as e:
            logger.error(f"Librarian Agent database operation failed: {str(e)}")
            # اجازه می‌دهیم سیستم بدون کرش آرایه خالی برگرداند
        finally:
            if conn:
                conn.close()
                
        return results

# نمونه سراسری عامل جستجوی برداری اسناد
vector_search_agent = VectorSearchAgent()
