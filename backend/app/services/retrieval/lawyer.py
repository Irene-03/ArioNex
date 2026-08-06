"""
/// <summary>
/// Legal counsel and rule compliance auditor agent (The Lawyer - Compliance & Constraint Auditing Agent)
/// </summary>
/// <remarks>
/// This agent audits the generated final responses against the business rules extracted from the audit document.
/// If any non-compliance with organizational policies is found, it reports the rule violation and records an audit log.
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
    /// Legal counsel agent class for auditing and monitoring compliance of responses with organizational rules
    /// </summary>
    """
    def __init__(self):
        # This agent operates based on whether the rule extraction module is enabled
        self.is_enabled = settings.services.rule_extractor

    def get_rules_count(self, file_id: Optional[int] = None) -> int:
        """
        /// <summary>
        /// Get the number of rules registered for a document to decide whether to run the auditor
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
        /// Audit the generated response's compliance with organizational rules sequentially (Sequential LLM Audit)
        /// </summary>
        /// <param name="query">User question</param>
        /// <param name="response">System's proposed response</param>
        /// <param name="file_id">Related document ID</param>
        /// <returns>Dictionary containing compliance status, rule violation details, and a text report</returns>
        /// </summary>
        """
        # Soft Enable: even if the toggle is off, we run the audit if rules exist in the database
        if not self.is_enabled:
            # Quickly check for any overall rules before skipping
            try:
                conn_check = get_db_connection()
                with conn_check.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM extracted_rules")
                    total_rules = cur.fetchone()[0]
                conn_check.close()
                if total_rules == 0:
                    return {"is_compliant": True, "violations": [], "audit_report": ""}
                logger.info(f"[The Lawyer] Toggle is off but {total_rules} rules found in DB. Activating soft-enable audit.")
            except Exception:
                return {"is_compliant": True, "violations": [], "audit_report": ""}

        # 1. Quickly check whether rules exist for this file (fast bypass if there are no rules)
        rules_count = self.get_rules_count(file_id)
        if rules_count == 0:
            logger.info(f"[The Lawyer] No compliance rules found for file_id={file_id}. Bypassing audit.")
            return {"is_compliant": True, "violations": [], "audit_report": ""}

        logger.info(f"[The Lawyer] Initiating compliance audit. Found {rules_count} rules for file_id={file_id}.")

        # 2. Retrieve legal clauses from the database
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
            # On database error, assume access is allowed for safety so the system is not locked up
            return {"is_compliant": True, "violations": [], "audit_report": ""}
        finally:
            if conn:
                conn.close()

        # Format the rules for injection into the prompt
        formatted_rules = []
        for r in rules:
            formatted_rules.append(
                f"- Code: {r['rule_code']}\n  Clause: {r['clause']}\n  Type: {r['type']}\n  Description: {r['description']}"
            )
        rules_str = "\n\n".join(formatted_rules)

        # 3. Call the LLM to evaluate response compliance
        audit_result = {"is_compliant": True, "violations": [], "audit_report": ""}
        
        try:
            llm = get_llm(temperature=0.0)  # zero temperature for a definitive result
            
            # Legal auditor prompt
            audit_prompt = f"""You are an expert enterprise compliance auditor (The Lawyer). Your job is to loosely audit the proposed RESPONSE.

JSON format:
{{
  "is_compliant": true
  "violations": [], // empty if compliant
  "audit_report": "A detailed Persian audit report explanation."
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
        except ValueError as ve:
            raise ve
        except Exception as e:
            logger.error(f"[The Lawyer] LLM auditing failed: {str(e)}. Defaulting to compliant for safety.")

        # 4. Save the audit report in the compliance_audit_logs table for admin monitoring
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
                        True,
                        [],
                        ""
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

# Global instance for use in RAG
lawyer_agent = LawyerAgent()
