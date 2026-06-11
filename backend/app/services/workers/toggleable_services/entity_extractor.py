import logging
from typing import Optional

from app.core.config import settings
from app.core.database import get_db_connection
from app.services.workers.toggleable_services.helpers import _clean_and_parse_json

logger = logging.getLogger("arionex.toggleable_services")


class EntityExtractorWorker:
    """
    /// <summary>
    /// کارگر استخراج‌کننده موجودیت‌ها از متون جهت تغذیه به گراف دانش (Entity Extractor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.entity_extractor

    def extract_entities(self, text: str, file_id: Optional[int] = None) -> dict:
        """
        /// <summary>
        /// استخراج خودکار موجودیت‌ها و روابط بین آن‌ها از متن با استفاده از LLM یا Fallback Mock
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Service] Entity Extractor is currently DISABLED in config.yaml. Skipping execution.")
            return {"entities": [], "relationships": []}
            
        logger.info(f"[Toggleable Service] Entity Extractor is ACTIVE. Processing text for file_id={file_id}...")

        active_provider = settings.llm_provider
        active_key = (
            settings.openrouter_api_key if active_provider == "openrouter"
            else settings.openai_api_key
        )
        is_mock_key = not active_key or active_key in ("mock_key", "") or "your-" in active_key

        extracted_data = {"entities": [], "relationships": []}

        if is_mock_key:
            logger.info("[Toggleable Service] Mock LLM mode active. Generating Persian fallback entities and relationships...")
            text_lower = text.lower()
            if "شرکت" in text_lower or "سازمان" in text_lower:
                extracted_data = {
                    "entities": [
                        {"name": "شرکت آریونکس", "type": "ORGANIZATION", "description": "سازمان اصلی فناوری اطلاعات"},
                        {"name": "مدیریت آریونکس", "type": "PERSON", "description": "مدیر اجرایی فناوری"}
                    ],
                    "relationships": [
                        {"source": "مدیریت آریونکس", "target": "شرکت آریونکس", "relationship": "EMPLOYEE_OF", "description": "استخدام در سازمان"}
                    ]
                }
            elif "قرارداد" in text_lower or "تعهد" in text_lower or "محرمانه" in text_lower:
                extracted_data = {
                    "entities": [
                        {"name": "تعهدنامه عدم افشا NDA", "type": "DOCUMENT", "description": "سند رسمی حفظ اسرار تجاری"},
                        {"name": "کارفرما", "type": "PERSON", "description": "طرف اول قرارداد متعهد"}
                    ],
                    "relationships": [
                        {"source": "کارفرما", "target": "تعهدنامه عدم افشا NDA", "relationship": "SIGNATORY_OF", "description": "امضا کننده سند تعهد"}
                    ]
                }
            elif "سامانه" in text_lower or "سایت" in text_lower:
                extracted_data = {
                    "entities": [
                        {"name": "سامانه دانش آریونکس", "type": "SOFTWARE", "description": "پلتفرم مدیریت هوشمند پایگاه دانش"},
                        {"name": "کاربران سیستم", "type": "GROUP", "description": "کاربران نهایی پلتفرم"}
                    ],
                    "relationships": [
                        {"source": "کاربران سیستم", "target": "سامانه دانش آریونکس", "relationship": "USES", "description": "استفاده روزمره از نرم‌افزار"}
                    ]
                }
            else:
                extracted_data = {
                    "entities": [
                        {"name": "سند آریونکس", "type": "DOCUMENT", "description": "مستند خام بارگذاری شده در سیستم"},
                        {"name": "مدیریت سیستم", "type": "PERSON", "description": "ایجاد کننده فایل در پلتفرم"}
                    ],
                    "relationships": [
                        {"source": "مدیریت سیستم", "target": "سند آریونکس", "relationship": "AUTHOR_OF", "description": "نویسنده سند"}
                    ]
                }
        else:
            try:
                from langchain_core.prompts import PromptTemplate
                from app.prompts.extractor_prompts import ENTITY_EXTRACTION_TEMPLATE
                from app.core.llm_factory import get_llm

                llm = get_llm(temperature=0.0)
                prompt = PromptTemplate.from_template(ENTITY_EXTRACTION_TEMPLATE)
                chain = prompt | llm
                
                response = chain.invoke({"text": text})
                raw_response = response.content.strip()
                extracted_data = _clean_and_parse_json(raw_response)
            except Exception as e:
                logger.error(f"[Toggleable Service] Entity extraction via LLM failed: {str(e)}")
                return {"entities": [], "relationships": []}

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for ent in extracted_data.get("entities", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_entities (name, type, description, file_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (file_id, name) DO UPDATE SET
                            type = EXCLUDED.type,
                            description = EXCLUDED.description
                        """,
                        (ent.get("name"), ent.get("type"), ent.get("description"), file_id)
                    )
                for rel in extracted_data.get("relationships", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_relationships (source, target, relationship, description, file_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (file_id, source, target, relationship) DO UPDATE SET
                            description = EXCLUDED.description
                        """,
                        (rel.get("source"), rel.get("target"), rel.get("relationship"), rel.get("description"), file_id)
                    )
                    
                    if settings.services.neo4j:
                        from app.services.workers.toggleable_services.neo4j_manager import neo4j_manager
                        neo4j_manager.insert_relationship(
                            rel.get("source"), rel.get("relationship"), rel.get("target")
                        )
                conn.commit()
                logger.info(
                    f"[Toggleable Service] Successfully saved {len(extracted_data.get('entities', []))} entities "
                    f"and {len(extracted_data.get('relationships', []))} relationships for file_id={file_id}."
                )
        except Exception as db_err:
            logger.error(f"[Toggleable Service] Failed to save extracted entities/relationships to Postgres: {str(db_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return extracted_data
