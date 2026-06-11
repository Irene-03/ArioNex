"""
/// <summary>
/// فایل تست خودکار و راستی‌آزمایی فاز ۸ آریونکس (ArioNex Phase 8 Verification Script)
/// </summary>
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# اضافه کردن مسیر پروژه جهت شناسایی پکیج app
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.core.config import settings
from app.services.retrieval.investigator import investigator_agent
from app.services.retrieval.lawyer import lawyer_agent
from app.services.retrieval.query_router import synthesize_rag_response
from app.prompts.rag_prompts import STANDARD_REFUSAL_MESSAGE

class TestPhase8Agents(unittest.TestCase):
    
    def setUp(self):
        # فعال کردن دستی سرویس‌ها جهت تست
        settings.services.entity_extractor = True
        settings.services.rule_extractor = True
        investigator_agent.is_enabled = True
        lawyer_agent.is_enabled = True

    @patch("app.services.retrieval.investigator.get_db_connection")
    def test_investigator_retrieval_and_formatting(self, mock_get_db):
        print("Testing Investigator retrieval and formatting...")
        
        # شبیه‌سازی نتایج کوئری پایگاه داده
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # شبیه‌سازی موجودیت‌ها در fetchall اول
        mock_cur.fetchall.side_effect = [
            [("آریونکس", "ORGANIZATION", "دستیار هوشمند سازمانی")],  # موجودیت‌ها
            [("مدیریت سیستم", "آریونکس", "EMPLOYEE_OF", "استخدام در سازمان")]  # روابط
        ]
        
        graph_context = investigator_agent.retrieve_graph_context("اطلاعات درباره شرکت آریونکس", file_id=1)
        
        print(f"Generated Graph Context:\n{graph_context}")
        
        # بررسی صحت فرمت رندر شبه‌کد
        self.assertIn("[اطلاعات ساختاریافته گراف دانش]:", graph_context)
        self.assertIn('- موجودیت "آریونکس" از نوع "ORGANIZATION" است. (توضیحات: دستیار هوشمند سازمانی)', graph_context)
        self.assertIn('- "مدیریت سیستم" رابطه "EMPLOYEE_OF" دارد با "آریونکس". (توضیحات: استخدام در سازمان)', graph_context)
        
        print(" Investigator Agent checks PASSED.\n")

    @patch("app.services.retrieval.lawyer.get_llm")
    @patch("app.services.retrieval.lawyer.get_db_connection")
    def test_lawyer_compliance_violations(self, mock_get_db, mock_get_llm):
        print("Testing Lawyer compliance audit violations...")
        
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # شبیه‌سازی COUNT(*) قوانین (۱) و سپس جزئیات قوانین
        mock_cur.fetchone.return_value = [1]
        mock_cur.fetchall.return_value = [
            ("RULE-CONF-2", "هرگونه افشای اطلاعات محرمانه تجاری بدون هماهنگی کتبی ممنوع است", "CONSTRAINT", "حفظ اسرار")
        ]
        
        # ماک کردن LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        from langchain_core.messages import AIMessage
        import json
        
        non_compliant_json = json.dumps({
            "is_compliant": False,
            "violations": ["RULE-CONF-2"],
            "audit_report": "نقض سیاست محرمانگی"
        })
        compliant_json = json.dumps({
            "is_compliant": True,
            "violations": [],
            "audit_report": "تایید انطباق کامل با ضوابط"
        })
        mock_llm.invoke.side_effect = [
            AIMessage(content=non_compliant_json),
            AIMessage(content=compliant_json)
        ]
        
        # تست با پاسخ غیرمنطبق (نقض بحرانی حاوی کلمات کارت بانکی و رمز)
        non_compliant_response = "اطلاعات مالی محرمانه و رمز عبور شما فاش شد."
        audit_res = lawyer_agent.audit_compliance("سوال درباره رمز", non_compliant_response, file_id=1)
        
        print(f"Non-compliant audit report: {audit_res.get('audit_report')}")
        self.assertFalse(audit_res["is_compliant"])
        self.assertIn("RULE-CONF-2", audit_res["violations"])
        
        # تست با پاسخ منطبق
        compliant_response = "کاربر گرامی، کلیه اطلاعات در امنیت کامل نگهداری می‌شوند."
        audit_res_ok = lawyer_agent.audit_compliance("سوال درباره امنیت", compliant_response, file_id=1)
        
        print(f"Compliant audit report: {audit_res_ok.get('audit_report')}")
        self.assertTrue(audit_res_ok["is_compliant"])
        self.assertEqual(len(audit_res_ok["violations"]), 0)
        
        print(" Lawyer Agent checks PASSED.\n")

    @patch("app.services.retrieval.query_router.synthesizer.get_llm")
    @patch("app.services.retrieval.query_router.vector_search_agent")
    @patch("app.services.retrieval.query_router.qna_agent")
    @patch("app.services.retrieval.query_router.investigator_agent")
    @patch("app.services.retrieval.query_router.lawyer_agent")
    @patch("app.services.retrieval.query_router.get_db_connection")
    def test_query_router_integration_compliance_blocking(self, mock_get_db, mock_lawyer, mock_investigator, mock_qna, mock_vector, mock_get_llm):
        print("Testing Query Router Integration & Compliance Blocking...")
        
        # شبیه‌سازی دیتابیس در کل زنجیره RAG
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            ("RULE-CONF-2", "هرگونه افشای اطلاعات محرمانه تجاری بدون هماهنگی کتبی ممنوع است")
        ]
        
        # شبیه‌سازی نتایج بازیابی
        mock_vector.retrieve_context.return_value = [{
            "content": "متن نمونه سند آریونکس",
            "label": "document.txt",
            "sequence_id": 1,
            "file_id": 1,
            "similarity": 0.8,
            "source_type": "document"
        }]
        mock_qna.retrieve_context.return_value = []
        
        # شبیه‌سازی Investigator
        mock_investigator.retrieve_graph_context.return_value = "[اطلاعات ساختاریافته گراف دانش]:\n- موجودیت آریونکس"
        
        # ماک کردن LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        from langchain_core.messages import AIMessage
        mock_llm.return_value = AIMessage(content="پاسخ نمونه تولید شده توسط هوش مصنوعی")
        mock_llm.invoke.return_value = AIMessage(content="پاسخ نمونه تولید شده توسط هوش مصنوعی")
        
        # سناریو اول: عدم انطباق بحرانی (باید پاسخ بلاک شده و پیغام امتناع برگردد)
        mock_lawyer.audit_compliance.return_value = {
            "is_compliant": False,
            "violations": ["RULE-CONF-2"],
            "audit_report": "نقض سیاست محرمانگی"
        }
        
        response = synthesize_rag_response("سوال من چیست؟", chat_history=[])
        
        self.assertEqual(response["answer"], STANDARD_REFUSAL_MESSAGE)
        self.assertFalse(response["is_safe"])
        self.assertEqual(len(response["sources"]), 0)
        print("  Non-compliant response blocking check PASSED.")
        
        # سناریو دوم: انطباق کامل (باید پاسخ تایید شده به همراه تگ گزارش انطباق برگردد)
        mock_lawyer.audit_compliance.return_value = {
            "is_compliant": True,
            "violations": [],
            "audit_report": "تایید انطباق کامل با ضوابط"
        }
        
        response_ok = synthesize_rag_response("سوال من چیست؟", chat_history=[])
        
        self.assertTrue(response_ok["is_safe"])
        self.assertIn("⚖️ **گزارش انطباق قوانین (ArioNex Lawyer Audit):**", response_ok["answer"])
        self.assertIn("تایید انطباق کامل با ضوابط", response_ok["answer"])
        print("  Compliant response appending check PASSED.")
        
        print(" Query Router Integration checks PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 8 AUTOMATED TEST SUITE")
    print("=========================================")
    unittest.main()
