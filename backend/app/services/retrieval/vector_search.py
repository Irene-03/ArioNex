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

    def retrieve_categorical(self, query: str, threshold: float = 0.3, k: int = 5, file_ids: list[int] = None) -> list[dict]:
        """
        /// <summary>
        /// بازیابی معنایی قطعات از جدول pg_supervisor با فیلتر دسته‌بندی / شناسه فایل
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("Librarian Agent is disabled. Skipping document vector retrieval.")
            return []
            
        logger.info(f"Librarian Agent starting categorical search for query: '{query}'")
        
        try:
            embedding = get_embedding(query)
        except Exception as emb_err:
            logger.error(f"Librarian Agent failed to generate query embedding: {str(emb_err)}")
            return []
            
        filter_clause = ""
        params = [embedding]
        
        if file_ids:
            placeholders = ",".join(["%s"] * len(file_ids))
            filter_clause = f"AND file_id IN ({placeholders})"
            params.extend(file_ids)
            
        params.append(k)
        
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
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": label or "unnamed_document",
                        "file_id": file_id or 0,
                        "sequence_id": seq_id or 0,
                        "similarity": similarity,
                        "source_type": "document"
                    })
            logger.info(f"Librarian Agent categorical search retrieved {len(results)} chunks above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Librarian Agent categorical search database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results

    def retrieve_general(self, query: str, threshold: float = 0.3, k: int = 5) -> list[dict]:
        """
        /// <summary>
        /// بازیابی معنایی قطعات عمومی از جدول pg_dummy
        /// </summary>
        """
        if not self.is_enabled:
            return []
            
        logger.info(f"Librarian Agent starting general search for query: '{query}'")
        
        try:
            embedding = get_embedding(query)
        except Exception as emb_err:
            logger.error(f"Librarian Agent failed to generate query embedding: {str(emb_err)}")
            return []
            
        sql = """
        SELECT content, 
               1 - (embedding <=> %s::vector) AS similarity
        FROM pg_dummy
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        results = []
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, [embedding, k])
                rows = cur.fetchall()
                
            for row in rows:
                content, similarity = row
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": "dummy_general",
                        "file_id": 0,
                        "sequence_id": 0,
                        "similarity": similarity,
                        "source_type": "general"
                    })
            logger.info(f"Librarian Agent general search retrieved {len(results)} chunks above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Librarian Agent general search database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results

    def retrieve_context(self, query: str, threshold: float = 0.5, k: int = 4, file_ids: list[int] = None) -> list[dict]:
        """
        /// <summary>
        /// بازیابی ترکیبی (سازگاری عقب‌رو)
        /// </summary>
        """
        categorical = self.retrieve_categorical(query, threshold=threshold, k=k, file_ids=file_ids)
        if len(categorical) >= k:
            return categorical[:k]
            
        remaining = k - len(categorical)
        general = self.retrieve_general(query, threshold=threshold, k=remaining)
        return categorical + general

# نمونه سراسری عامل جستجوی برداری اسناد
vector_search_agent = VectorSearchAgent()

