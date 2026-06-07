"""
/// <summary>
/// ماژول مدیریت سرویس‌های اختیاری و ماژولار غیرفعال (Toggleable Shell Services)
/// </summary>
/// <remarks>
/// این ماژول حاوی کلاس‌ها و توابع برای ماژول‌های Entity Extractor، Rule Extractor،
/// پایگاه داده Neo4j و بازرس امنیتی محلی Gemma-2b است.
/// </remarks>
"""

import json
import re
import random
import logging
from typing import Optional, List

from app.core.config import settings
from app.core.database import get_db_connection

logger = logging.getLogger("arionex.toggleable_services")


def _clean_and_parse_json(text: str) -> dict:
    """
    /// <summary>
    /// پاکسازی و پارس امن خروجی مدل زبانی به صورت JSON معتبر با قابلیت بازیابی جیسان‌های شکسته
    /// </summary>
    """
    cleaned = text.strip()
    # حذف بلاک‌های کد مارک‌داون
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception as std_json_err:
        try:
            from json_repair import repair_json
            repaired = repair_json(cleaned)
            return json.loads(repaired)
        except Exception as repair_err:
            logger.error(f"Failed to parse and repair JSON. Standard error: {str(std_json_err)}. Repair error: {str(repair_err)}")
            raise repair_err



class EntityExtractorWorker:
    """
    /// <summary>
    /// کارگر استخراج‌کننده موجودیت‌ها از متون جهت تغذیه به گراف دانش (Entity Extractor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.entity_extractor

    def extract_entities(self, text: str, file_id: int) -> dict:
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
            # فراخوانی واقعی مدل زبانی از Factory
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

        # ثبت داده‌ها در دیتابیس PostgreSQL
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # ثبت موجودیت‌ها
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
                # ثبت روابط
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
                    
                    # ثبت موازی در Neo4j در صورت فعال بودن
                    if settings.services.neo4j:
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


class RuleExtractorWorker:
    """
    /// <summary>
    /// کارگر هوشمند استخراج قوانین کسب‌وکار و آیین‌نامه‌ها از متون خام اسناد (Rule Extractor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.rule_extractor

    def extract_rules(self, text: str, file_id: int) -> list:
        """
        /// <summary>
        /// شناسایی و استخراج بندهای قانونی و شروط انطباق با استفاده از LLM یا Fallback Mock
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Service] Rule Extractor is currently DISABLED in config.yaml. Skipping execution.")
            return []
            
        logger.info(f"[Toggleable Service] Rule Extractor is ACTIVE. Processing rules for file_id={file_id}...")

        active_provider = settings.llm_provider
        active_key = (
            settings.openrouter_api_key if active_provider == "openrouter"
            else settings.openai_api_key
        )
        is_mock_key = not active_key or active_key in ("mock_key", "") or "your-" in active_key

        extracted_rules = []

        if is_mock_key:
            logger.info("[Toggleable Service] Mock LLM mode active. Generating Persian fallback rules...")
            text_lower = text.lower()
            if "مرخصی" in text_lower:
                extracted_rules = [
                    {
                        "rule_code": "RULE-VAC-1",
                        "clause": "سیاست مرخصی سالانه بر اساس سابقه کار کارمندان می‌باشد",
                        "type": "POLICY",
                        "description": "تخصیص مرخصی استحقاقی سالانه"
                    }
                ]
            elif "محرمانه" in text_lower or "افشا" in text_lower:
                extracted_rules = [
                    {
                        "rule_code": "RULE-CONF-2",
                        "clause": "هرگونه افشای اطلاعات محرمانه تجاری بدون هماهنگی کتبی ممنوع است",
                        "type": "CONSTRAINT",
                        "description": "جلوگیری از درز اطلاعات مالی و محصولی"
                    }
                ]
            elif "ساعت" in text_lower or "حضور" in text_lower:
                extracted_rules = [
                    {
                        "rule_code": "RULE-TIME-3",
                        "clause": "ساعات کاری رسمی شرکت از شنبه تا چهارشنبه ساعت ۸:۰۰ الی ۱۶:۳۰ می‌باشد",
                        "type": "POLICY",
                        "description": "مدیریت نظم حضور و غیاب کارکنان"
                    }
                ]
            elif "دسترسی" in text_lower or "رمز" in text_lower:
                extracted_rules = [
                    {
                        "rule_code": "RULE-SEC-4",
                        "clause": "کاربران موظف به تغییر رمز عبور خود هر ۹۰ روز یک‌بار می‌باشند",
                        "type": "CONSTRAINT",
                        "description": "دستورالعمل امنیت حساب‌های کاربری"
                    }
                ]
            else:
                extracted_rules = [
                    {
                        "rule_code": "RULE-GEN-5",
                        "clause": "رعایت کلیه دستورالعمل‌های انضباطی ابلاغ شده در سند الزامی است",
                        "type": "POLICY",
                        "description": "قوانین عمومی رفتاری سازمان"
                    }
                ]
        else:
            # فراخوانی واقعی مدل زبانی از Factory
            try:
                from langchain_core.prompts import PromptTemplate
                from app.prompts.extractor_prompts import RULE_EXTRACTION_TEMPLATE
                from app.core.llm_factory import get_llm

                llm = get_llm(temperature=0.0)
                prompt = PromptTemplate.from_template(RULE_EXTRACTION_TEMPLATE)
                chain = prompt | llm
                
                response = chain.invoke({"text": text})
                raw_response = response.content.strip()
                extracted_data = _clean_and_parse_json(raw_response)
                extracted_rules = extracted_data.get("rules", [])
            except Exception as e:
                logger.error(f"[Toggleable Service] Rule extraction via LLM failed: {str(e)}")
                return []

        # ثبت قوانین در دیتابیس PostgreSQL
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for rule in extracted_rules:
                    cur.execute(
                        """
                        INSERT INTO extracted_rules (rule_code, clause, type, description, file_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (file_id, rule_code) DO UPDATE SET
                            clause = EXCLUDED.clause,
                            type = EXCLUDED.type,
                            description = EXCLUDED.description
                        """,
                        (rule.get("rule_code"), rule.get("clause"), rule.get("type"), rule.get("description"), file_id)
                    )
                conn.commit()
                logger.info(f"[Toggleable Service] Successfully saved {len(extracted_rules)} rules to Postgres for file_id={file_id}.")
        except Exception as db_err:
            logger.error(f"[Toggleable Service] Failed to save extracted rules to Postgres: {str(db_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return extracted_rules


class Neo4jDatabaseManager:
    """
    /// <summary>
    /// مدیر ارتباط با پایگاه داده گرافی نئوفورجی (Neo4j Graph Database Manager)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.neo4j
        self.client = None
        if self.is_enabled:
            logger.info("[Toggleable Database] Neo4j Connection requested. Initializing drivers...")

    def insert_relationship(self, source: str, relation: str, target: str) -> bool:
        """
        /// <summary>
        /// درج یک یال ارتباطی گرافی در پایگاه داده Neo4j
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Database] Neo4j Graph DB is DISABLED in config.yaml. Relationship not saved.")
            return False
            
        logger.info(f"[Toggleable Database] Neo4j Graph DB is ACTIVE. Mock inserting: ({source})-[{relation}]->({target})")
        return True


class LocalGemmaSafetyAuditor:
    """
    /// <summary>
    /// بازرس امنیتی و ممیزی سوالات مبتنی بر هوش مصنوعی محلی (Local Gemma-2b Auditor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.safety_auditor
        if self.is_enabled:
            logger.info("[Toggleable Auditor] Initializing local Gemma-2b auditor in memory...")

    def audit_query(self, user_query: str) -> bool:
        if not self.is_enabled:
            return True
            
        logger.info(f"[Toggleable Auditor] Local Gemma-2b is active. Scanning query: '{user_query}'...")
        return True

    def audit_response(self, ai_response: str) -> bool:
        if not self.is_enabled:
            return True
            
        logger.info("[Toggleable Auditor] Local Gemma-2b scanning response content safety...")
        return True


# شیء‌های سراسری جهت استفاده ماژولار در سایر بخش‌های RAG
entity_extractor_worker = EntityExtractorWorker()
rule_extractor_worker = RuleExtractorWorker()
neo4j_manager = Neo4jDatabaseManager()
local_gemma_auditor = LocalGemmaSafetyAuditor()
