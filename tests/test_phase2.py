"""
/// <summary>
/// ArioNex Phase 2 verification and automated test file (ArioNex Phase 2 Verification Script)
/// </summary>
"""

import sys
import os

# Add the backend path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.safety.pii_redactor import redact_text, redact_and_audit

def test_farsi_normalization():
    print("Running Farsi Normalization tests...")
    
    # Test diacritics, Arabic letters, and conversion of Arabic/Persian digits to English
    raw_text = "حسابدار با کد پرسنلی ١٢٣٤۵ و شماره سند ٤٥٩-٨١٤٦ بررسی شد، بستانکار: ٢٥٠,٠٠٠ ریال."
    normalized = normalize_text(raw_text)
    
    print(f"Original:   {raw_text}")
    print(f"Normalized: {normalized}")
    
    # Verify the correctness of digit conversion
    assert "12345" in normalized, "Arabic/Persian digits were not converted to western format!"
    assert "459-8146" in normalized, "Document numbers were not mapped correctly!"
    assert "250,000" in normalized or "250000" in normalized, "Values were not mapped properly!"
    print(" Farsi Normalization test PASSED.\n")

def test_text_chunking():
    print("Running Text Chunking tests...")
    
    # Build a long text to feed into the chunker
    words = ["کلمه"] * 500
    long_text = " ".join(words)
    
    chunks = chunk_text(long_text, chunk_size=200, overlap=50)
    print(f"Total chunks generated: {len(chunks)}")
    
    # With 500 words, chunk size 200, and overlap 50, the chunks will be as follows:
    # Chunk 1: 0 to 200 (words)
    # Chunk 2: 150 to 350 (words)
    # Chunk 3: 300 to 500 (words)
    # In total, 3 chunks should be produced.
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert len(chunks[0].split()) == 200, "First chunk size must be exactly 200 words."
    print(" Text Chunking test PASSED.\n")

def test_pii_redaction():
    print("Running PII Redaction tests...")
    
    # Text containing all sensitive PII patterns (national ID and card must be valid to be masked)
    sensitive_text = "کد ملی من 1234567891 است و شماره کارتم 6037-9912-3456-7893 و شبا من IR760120000000001234567890. جهت هماهنگی با شماره 09123456789 یا ایمیل test@gmail.com تماس بگیرید."
    
    redacted, audit = redact_and_audit(sensitive_text)
    print(f"Original: {sensitive_text}")
    print(f"Redacted: {redacted}")
    print(f"Audit Log Counts: {audit}")
    
    # Verify the presence of mask tags
    assert "[کد ملی]" in redacted
    assert "[شماره کارت بانکی]" in redacted
    assert "[شماره شبا]" in redacted
    assert "[شماره تلفن همراه]" in redacted
    assert "[آدرس ایمیل]" in redacted
    
    # Verify the audit counts
    assert audit["national_id"] == 1
    assert audit["card_number"] == 1
    assert audit["iban_number"] == 1
    assert audit["mobile_number"] == 1
    assert audit["email_address"] == 1
    
    print(" PII Redaction test PASSED.\n")

def test_pii_no_false_positive_on_financial_data():
    print("Running PII False-Positive Reduction tests...")
    
    # Numbers without a valid structure (transaction code, order ID, and financial values) must not be masked
    financial_text = "کد تراکنش 1234567890 به مبلغ 5,000,000 ریال و شناسه سفارش 1234567890123456 ثبت شد."
    
    redacted, audit = redact_and_audit(financial_text)
    print(f"Original: {financial_text}")
    print(f"Redacted: {redacted}")
    print(f"Audit Log Counts: {audit}")
    
    # No valid PII in ordinary financial text should be masked
    assert "[کد ملی]" not in redacted
    assert "[شماره کارت بانکی]" not in redacted
    assert "1234567890" in redacted, "Transaction code must not be masked!"
    assert "1234567890123456" in redacted, "Order reference must not be masked!"
    assert audit == {}, f"Unexpected PII masking in financial data: {audit}"
    
    print(" PII False-Positive Reduction test PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 2 AUTOMATED TEST SUITE")
    print("=========================================")
    try:
        test_farsi_normalization()
        test_text_chunking()
        test_pii_redaction()
        test_pii_no_false_positive_on_financial_data()
        print("=========================================")
        print("ALL PHASE 2 TESTS COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
