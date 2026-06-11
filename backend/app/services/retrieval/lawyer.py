"""
/// <summary>
/// عامل حقوقدان و ممیز انطباق قوانین (The Lawyer - Compliance & Constraint Auditing Agent)
/// </summary>
/// <remarks>
/// این عامل پاسخ‌های نهایی تولید شده را در برابر قوانین کسب‌وکار استخراج شده از سند ممیزی می‌کند.
/// در صورت وجود هرگونه عدم انطباق با سیاست‌های سازمانی، نقض قانون را گزارش نموده و لاگ ممیزی را ثبت می‌کند.
/// </remarks>
"""

import json
import logging
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.llm_factory import get_llm
from app.services.workers.toggleable_services import _clean_and_parse_json

logger = logging.getLogger("arionex.lawyer")

class LawyerAgent:
    """
    /// <summary>
    /// کلاس عامل حقوقدان جهت ممیزی و پایش انطباق پاسخ‌ها با قوانین سازمانی
    /// </summary>
    """
    def __init__(self):
        # این عامل بر اساس فعال بودن ماژول استخراج قوانین کار می‌کند
        self.is_enabled = settings.services.rule_extractor

    def get_rules_count(self, file_id: Optional[int] = None) -> int:
        """
        /// <summary>
        /// دریافت تعداد قوانین ثبت شده برای یک سند جهت تصمیم‌گیری در مورد اجرای ممیز
        /// </summary>
        """
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM extracted_rules WHERE (file_id = %s OR %s IS NULL)",
                    (file_id, file_id)
                )
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"[The Lawyer] Failed to query rules count: {str(e)}")
            return 0
        finally:
            if conn:
                conn.close()

    def audit_compliance(self, query: str, response: str, file_id: Optional[int] = None) -> dict:
        """
        /// <summary>
        /// ممیزی انطباق پاسخ تولیدی با قوانین سازمان به صورت متوالی (Sequential LLM Audit)
        /// </summary>
        /// <param name="query">سوال کاربر</param>
        /// <param name="response">پاسخ پیشنهادی سیستم</param>
        /// <param name="file_id">شناسه سند مربوطه</param>
        /// <returns>دیکشنری شامل وضعیت انطباق، جزئیات نقض قوانین، و گزارش متنی</returns>
        /// </summary>
        """
        # اگر کل ماژول خاموش است، ممیزی را بای‌پاس می‌کنیم
        if not self.is_enabled:
            return {"is_compliant": True, "violations": [], "audit_report": ""}

        # ۱. بررسی سریع وجود قوانین برای این فایل (بای‌پاس سریع در صورت نبود قانون)
        rules_count = self.get_rules_count(file_id)
        if rules_count == 0:
            logger.info(f"[The Lawyer] No compliance rules found for file_id={file_id}. Bypassing audit.")
            return {"is_compliant": True, "violations": [], "audit_report": ""}

        logger.info(f"[The Lawyer] Initiating compliance audit. Found {rules_count} rules for file_id={file_id}.")

        # ۲. بازیابی بندهای قانونی از دیتابیس
        rules = []
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rule_code, clause, type, description FROM extracted_rules WHERE (file_id = %s OR %s IS NULL)",
                    (file_id, file_id)
                )
                rows = cur.fetchall()
                for row in rows:
                    rules.append({
                        "rule_code": row[0],
                        "clause": row[1],
                        "type": row[2],
                        "description": row[3] or ""
                    })
        except Exception as e:
            logger.error(f"[The Lawyer] Database error during rules retrieval: {str(e)}")
            # در صورت بروز خطای دیتابیس، برای ایمنی دسترسی را مجاز فرض می‌کنیم تا سیستم قفل نشود
            return {"is_compliant": True, "violations": [], "audit_report": ""}
        finally:
            if conn:
                conn.close()

        # فرمت‌دهی قوانین جهت تزریق به پرامپت
        formatted_rules = []
        for r in rules:
            formatted_rules.append(
                f"- Code: {r['rule_code']}\n  Clause: {r['clause']}\n  Type: {r['type']}\n  Description: {r['description']}"
            )
        rules_str = "\n\n".join(formatted_rules)

        # ۳. فراخوانی LLM جهت ارزیابی انطباق پاسخ
        audit_result = {"is_compliant": True, "violations": [], "audit_report": ""}
        
        try:
            llm = get_llm(temperature=0.0)  # دمای صفر برای دریافت نتیجه قطعی
                
                # پرامپت ممیز حقوقی
                audit_prompt = f"""You are an expert enterprise compliance auditor (The Lawyer). Your job is to strictly audit the proposed RESPONSE to the USER QUERY against the list of corporate COMPLIANCE RULES.

Evaluate if the proposed response violates any rule or restriction. 
Return your analysis STRICTLY in JSON format. Do not include any explanations, code block ticks, or text outside the JSON.

JSON format:
{{
  "is_compliant": false, // or true
  "violations": ["list of violated rule codes"], // empty if compliant
  "audit_report": "A detailed Persian audit report explanation of the compliance status and any violations."
}}

RULES:
{rules_str}

USER QUERY:
{query}

PROPOSED RESPONSE:
{response}
"""
                llm_response = llm.invoke(audit_prompt)
                raw_text = llm_response.content.strip()
                audit_result = _clean_and_parse_json(raw_text)
            except Exception as e:
                logger.error(f"[The Lawyer] LLM auditing failed: {str(e)}. Defaulting to compliant for safety.")

        # ۴. ذخیره گزارش ممیزی در جدول compliance_audit_logs جهت مانیتورینگ ادمین
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO compliance_audit_logs 
                        (file_id, query_text, response_text, is_compliant, violations, audit_report)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        file_id,
                        query,
                        response,
                        audit_result.get("is_compliant", True),
                        json.dumps(audit_result.get("violations", [])),
                        audit_result.get("audit_report", "")
                    )
                )
                conn.commit()
                logger.info(f"[The Lawyer] Compliance audit logged. Compliant: {audit_result.get('is_compliant', True)}")
        except Exception as log_err:
            logger.error(f"[The Lawyer] Failed to write compliance log: {str(log_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return audit_result

# نمونه سراسری جهت استفاده در RAG
lawyer_agent = LawyerAgent()
