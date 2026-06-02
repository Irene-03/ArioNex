"""
/// <summary>
/// فایل راستی‌آزمایی و تست خودکار فاز ۲ آریونکس (ArioNex Phase 2 Verification Script)
/// </summary>
"""

import sys
import os

# اضافه کردن آدرس مسیر بک‌بند جهت شناسایی پکیج app
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text, redact_and_audit

def test_farsi_normalization():
    print("Running Farsi Normalization tests...")
    
    # تست اعراب، حروف عربی و تبدیل اعداد عربی/فارسی به انگلیسی
    raw_text = "حسابدار با کد پرسنلی ١٢٣٤۵ و شماره سند ٤٥٩-٨١٤٦ بررسی شد، بستانکار: ٢٥٠,٠٠٠ ریال."
    normalized = normalize_text(raw_text)
    
    print(f"Original:   {raw_text}")
    print(f"Normalized: {normalized}")
    
    # بررسی صحت تبدیل اعداد
    assert "12345" in normalized, "Arabic/Persian digits were not converted to western format!"
    assert "459-8146" in normalized, "Document numbers were not mapped correctly!"
    assert "250,000" in normalized or "250000" in normalized, "Values were not mapped properly!"
    print(" Farsi Normalization test PASSED.\n")

def test_text_chunking():
    print("Running Text Chunking tests...")
    
    # ساخت یک متن طولانی برای فید کردن به چانک‌ساز
    words = ["کلمه"] * 500
    long_text = " ".join(words)
    
    chunks = chunk_text(long_text, chunk_size=200, overlap=50)
    print(f"Total chunks generated: {len(chunks)}")
    
    # با ۵۰۰ کلمه و چانک ۲۰۰ و همپوشانی ۵۰، چانک‌ها به این صورت خواهند بود:
    # چانک ۱: 0 تا 200 (کلمه)
    # چانک ۲: 150 تا 350 (کلمه)
    # چانک ۳: 300 تا 500 (کلمه)
    # جمعا باید ۳ چانک تولید شود.
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert len(chunks[0].split()) == 200, "First chunk size must be exactly 200 words."
    print(" Text Chunking test PASSED.\n")

def test_pii_redaction():
    print("Running PII Redaction tests...")
    
    # متنی شامل تمام الگوهای حساس PII
    sensitive_text = "کد ملی من 2980345678 است و شماره کارتم 6037-9912-3456-7890 و شبا من IR760120000000001234567890. جهت هماهنگی با شماره 09123456789 یا ایمیل test@gmail.com تماس بگیرید."
    
    redacted, audit = redact_and_audit(sensitive_text)
    print(f"Original: {sensitive_text}")
    print(f"Redacted: {redacted}")
    print(f"Audit Log Counts: {audit}")
    
    # بررسی وجود تگ‌های ماسک
    assert "[کد ملی]" in redacted
    assert "[شماره کارت بانکی]" in redacted
    assert "[شماره شبا]" in redacted
    assert "[شماره تلفن همراه]" in redacted
    assert "[آدرس ایمیل]" in redacted
    
    # بررسی شمارش ممیزی
    assert audit["national_id"] == 1
    assert audit["card_number"] == 1
    assert audit["iban_number"] == 1
    assert audit["mobile_number"] == 1
    assert audit["email_address"] == 1
    
    print(" PII Redaction test PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 2 AUTOMATED TEST SUITE")
    print("=========================================")
    try:
        test_farsi_normalization()
        test_text_chunking()
        test_pii_redaction()
        print("=========================================")
        print("ALL PHASE 2 TESTS COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
