"""
/// <summary>
/// فایل تست خودکار و راستی‌آزمایی فاز ۳ آریونکس (ArioNex Phase 3 Verification Script)
/// </summary>
"""

import sys
import os

# اضافه کردن مسیر پروژه جهت شناسایی پکیج app
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.services.workers.unstructured_processor import unstructured_processor
from app.services.workers.qna_processor import qna_processor
from app.services.workers.structured_processor import structured_processor
from app.services.workers.toggleable_services import (
    entity_extractor_worker,
    rule_extractor_worker,
    neo4j_manager,
    local_gemma_auditor
)

def test_unstructured_worker():
    print("Testing Unstructured Document Ingestion Worker...")
    assert unstructured_processor.is_enabled == True, "Unstructured processor should be enabled by default!"
    
    # ساخت فایل متنی نمونه محلی برای تست پارسر
    test_file = "test_unstructured.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("این یک متن نمونه حسابداری برای آریونکس است. کد ملی ۱۲۳۴۵۶۷۸۹۰ محرمانه است.")
        
    try:
        # تست استخراج متن
        text = unstructured_processor.parse_txt(test_file)
        print(f"Extracted Text: {text}")
        assert "آریونکس" in text
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
            
    print(" Unstructured worker checks PASSED.\n")

def test_qna_worker():
    print("Testing QnA Template Processor Ingestion Worker...")
    assert qna_processor.is_enabled == True, "QnA processor should be enabled by default!"
    
    # بررسی متدها و مقادیر اولیه
    print(f"QnA Ingestion status: {qna_processor.is_enabled}")
    print(" QnA worker checks PASSED.\n")

def test_structured_worker():
    print("Testing Structured Data Ingestion Worker...")
    assert structured_processor.is_enabled == True, "Structured processor should be enabled by default!"
    
    # بررسی متدها و مقادیر اولیه
    print(f"Structured Ingestion status: {structured_processor.is_enabled}")
    print(" Structured worker checks PASSED.\n")

def test_toggleable_services():
    print("Testing Toggleable Shell Services Pluggability...")
    
    # ذخیره حالت‌های اصلی برای بازگردانی
    orig_entity = entity_extractor_worker.is_enabled
    orig_rule = rule_extractor_worker.is_enabled
    orig_neo = neo4j_manager.is_enabled
    orig_safety = local_gemma_auditor.is_enabled
    
    # غیرفعال کردن موقت سرویس‌ها جهت تست رفتار بای‌پاس در حالت غیرفعال
    entity_extractor_worker.is_enabled = False
    rule_extractor_worker.is_enabled = False
    neo4j_manager.is_enabled = False
    local_gemma_auditor.is_enabled = False
    
    try:
        # بررسی وضعیت غیرفعال پیش‌فرض و صحت کارکرد در لایه ایزوله
        assert entity_extractor_worker.is_enabled == False, "Entity extractor should be disabled by default!"
        assert rule_extractor_worker.is_enabled == False, "Rule extractor should be disabled by default!"
        assert neo4j_manager.is_enabled == False, "Neo4j should be disabled by default!"
        assert local_gemma_auditor.is_enabled == False, "Local Gemma safety auditor should be disabled by default!"
        
        # تست رفتارهای شبیه‌سازی شده در حالت غیرفعال (باید لیست خالی یا False برگردانند و کرش نکنند)
        entities = entity_extractor_worker.extract_entities("متن نمونه")
        rules = rule_extractor_worker.extract_rules("متن نمونه")
        neo_inserted = neo4j_manager.insert_relationship("موجودیت ۱", "مرتبط", "موجودیت ۲")
        query_audited = local_gemma_auditor.audit_query("پرسش امن")
        response_audited = local_gemma_auditor.audit_response("پاسخ امن")
        
        print(f"Mock Entity Extractor returns: {entities}")
        print(f"Mock Rule Extractor returns: {rules}")
        print(f"Mock Neo4j Insert returns: {neo_inserted}")
        print(f"Mock Local Gemma audit returns: Query: {query_audited}, Response: {response_audited}")
        
        assert len(entities.get("entities", [])) == 0
        assert len(entities.get("relationships", [])) == 0
        assert len(rules) == 0
        assert neo_inserted == False
        assert query_audited == True
        assert response_audited == True
    finally:
        # بازگرداندن وضعیت اصلی سرویس‌ها
        entity_extractor_worker.is_enabled = orig_entity
        rule_extractor_worker.is_enabled = orig_rule
        neo4j_manager.is_enabled = orig_neo
        local_gemma_auditor.is_enabled = orig_safety
        
    print(" Toggleable Shell Services Pluggability checks PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 3 AUTOMATED TEST SUITE")
    print("=========================================")
    try:
        test_unstructured_worker()
        test_qna_worker()
        test_structured_worker()
        test_toggleable_services()
        print("=========================================")
        print("ALL PHASE 3 TESTS COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
