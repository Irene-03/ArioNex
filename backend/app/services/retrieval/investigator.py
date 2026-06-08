"""
/// <summary>
/// عامل بازپرس گراف (The Investigator - Graph RAG Retrieval Agent)
/// </summary>
/// <remarks>
/// این عامل وظیفه استخراج موجودیت‌های کلیدی از پرسش کاربر، انطباق آن‌ها با جداول رابطه گرافی Postgres
/// و Neo4j، بازیابی گره‌ها و یال‌های مرتبط، و رندر کردن آن‌ها به فرمت متنی ساختاریافته شبه‌کد جهت تزریق به RAG را دارد.
/// </remarks>
"""

import logging
import re
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.database import get_db_connection
from app.services.workers.toggleable_services import neo4j_manager

logger = logging.getLogger("arionex.investigator")

class InvestigatorAgent:
    """
    /// <summary>
    /// کلاس عامل بازپرس گراف جهت بازیابی هوشمند کانتکست ساختاریافته گرافی
    /// </summary>
    """
    def __init__(self):
        # این عامل بر اساس فعال بودن ماژول استخراج موجودیت کار می‌کند
        self.is_enabled = settings.services.entity_extractor

    def retrieve_graph_context(self, query: str, file_id: Optional[int] = None, max_entities: int = 5) -> str:
        """
        /// <summary>
        /// بازیابی موجودیت‌ها و روابط گرافی مرتبط با پرسش از دیتابیس و فرمت‌دهی آن‌ها
        /// </summary>
        /// <param name="query">پرسش مستقل کاربر</param>
        /// <param name="file_id">شناسه عددی فایل جهت فیلتر نتایج (اختیاری)</param>
        /// <param name="max_entities">حداکثر تعداد موجودیت‌های انتخابی</param>
        /// <returns>رشته کانتکست ساختاریافته گرافی به زبان فارسی</returns>
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[The Investigator] Graph search is disabled. Skipping.")
            return ""

        logger.info(f"[The Investigator] Extracting graph context for query: '{query}' (file_id={file_id})")

        # ۱. استخراج کلمات و توکن‌های پرسش جهت انطباق
        words = [w.strip() for w in re.split(r"[\s،,.;()?!]+", query) if len(w.strip()) > 2]
        if not words:
            return ""

        entities = []
        relationships = []

        # ۲. بازیابی موجودیت‌های منطبق از PostgreSQL
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # جستجو برای موجودیت‌هایی که نام آن‌ها در پرسش آمده است یا پرسش شامل آن‌هاست
                # از OR برای پوشش هر دو جهت انطباق استفاده می‌کنیم
                query_param = f"%{query}%"
                cur.execute(
                    """
                    SELECT name, type, description FROM extracted_entities
                    WHERE (file_id = %s OR %s IS NULL)
                      AND (
                           name ILIKE ANY(%s)
                           OR %s ILIKE '%' || name || '%'
                      )
                    LIMIT %s
                    """,
                    (file_id, file_id, [f"%{w}%" for w in words], query, max_entities)
                )
                rows = cur.fetchall()
                for row in rows:
                    entities.append({
                        "name": row[0],
                        "type": row[1],
                        "description": row[2] or ""
                    })

                if entities:
                    entity_names = [ent["name"] for ent in entities]
                    
                    # بازیابی روابط مربوط به موجودیت‌های منطبق شده
                    cur.execute(
                        """
                        SELECT source, target, relationship, description FROM extracted_relationships
                        WHERE (file_id = %s OR %s IS NULL)
                          AND (source = ANY(%s) OR target = ANY(%s))
                        LIMIT 10
                        """,
                        (file_id, file_id, entity_names, entity_names)
                    )
                    rel_rows = cur.fetchall()
                    for rel in rel_rows:
                        relationships.append({
                            "source": rel[0],
                            "target": rel[1],
                            "relationship": rel[2],
                            "description": rel[3] or ""
                        })
        except Exception as e:
            logger.error(f"[The Investigator] Database error during graph context retrieval: {str(e)}")
        finally:
            if conn:
                conn.close()

        # ۳. بازیابی موازی از Neo4j در صورت فعال بودن
        if settings.services.neo4j:
            logger.info("[The Investigator] Neo4j is enabled. Querying mock neo4j graph database...")
            # در نسخه واقعی، کوئری Cypher برای استخراج زیرگراف‌ها از neo4j_manager اجرا می‌شود
            for ent in entities:
                neo4j_manager.insert_relationship(ent["name"], "QUERY_MATCHED", "USER_QUESTION")

        # ۴. فرمت‌دهی ساختاریافته خروجی گرافی به صورت گزاره‌های کوتاه (شبه‌کد)
        if not entities and not relationships:
            return ""

        formatted_lines = ["[اطلاعات ساختاریافته گراف دانش]:"]
        
        # موجودیت‌ها
        for ent in entities:
            desc_part = f" (توضیحات: {ent['description']})" if ent["description"] else ""
            formatted_lines.append(f'- موجودیت "{ent["name"]}" از نوع "{ent["type"]}" است.{desc_part}')

        # روابط
        for rel in relationships:
            desc_part = f" (توضیحات: {rel['description']})" if rel['description'] else ""
            formatted_lines.append(f'- "{rel["source"]}" رابطه "{rel["relationship"]}" دارد با "{rel["target"]}".{desc_part}')

        return "\n".join(formatted_lines)

# نمونه سراسری جهت ایمپورت و استفاده در زنجیره RAG
investigator_agent = InvestigatorAgent()
