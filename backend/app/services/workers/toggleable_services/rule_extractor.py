import logging
import re
from typing import Optional

from app.core.config import settings
from app.core.database import get_db_connection
from app.services.workers.toggleable_services.helpers import _clean_and_parse_json

logger = logging.getLogger("arionex.toggleable_services")


class RuleExtractorWorker:
    """
    /// <summary>
    /// کارگر هوشمند استخراج قوانین کسب‌وکار و آیین‌نامه‌ها از متون خام اسناد (Rule Extractor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.rule_extractor

    def extract_rules(self, text: str, file_id: Optional[int] = None) -> list:
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

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for rule in extracted_rules:
                    rule_code = rule.get("rule_code")
                    clause = rule.get("clause") or ""
                    
                    if not rule_code or rule_code.strip() == "":
                        import hashlib
                        clause_hash = hashlib.md5(clause.encode('utf-8')).hexdigest()[:8]
                        rule_code = f"RULE-{clause_hash.upper()}"
                    else:
                        rule_code = rule_code.strip()
                        generic_patterns = [r"^rule-?\d+$", r"^policy-?\d+$", r"^clause-?\d+$", r"^قانون-?\d+$", r"^بند-?\d+$"]
                        is_generic = any(re.match(pattern, rule_code.lower()) for pattern in generic_patterns)
                        if is_generic:
                            import hashlib
                            clause_hash = hashlib.md5(clause.encode('utf-8')).hexdigest()[:8]
                            rule_code = f"{rule_code}-{clause_hash.upper()}"

                    cur.execute(
                        """
                        INSERT INTO extracted_rules (rule_code, clause, type, description, file_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (file_id, rule_code) DO UPDATE SET
                            clause = EXCLUDED.clause,
                            type = EXCLUDED.type,
                            description = EXCLUDED.description
                        """,
                        (rule_code, clause, rule.get("type"), rule.get("description"), file_id)
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
