"""
/// <summary>
/// موتور ایمنی و ماسک‌گذاری خودکار اطلاعات حساس شخصی (PII Redactor Safety Airlock)
/// </summary>
/// <remarks>
/// این ماژول وظیفه پایش و سانسور کردن اطلاعات شخصی حساس کاربران (کد ملی، شماره تلفن همراه،
/// ایمیل، شماره کارت‌های بانکی، شماره شبا و حساب) را با الگوهای منظم عبارات باقاعده بر عهده دارد
/// تا از ورود ناخواسته دیتای کاربری حساس به پایگاه برداری ممانعت شود.
/// </remarks>
"""

import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger("arionex.pii_redactor")

# تعریف الگوهای عبارات منظم برای شناسایی اطلاعات حساس ایرانی و بین‌المللی
PII_PATTERNS: Dict[str, str] = {
    # کد ملی ده رقمی ایرانی (بررسی ۱۰ رقم متوالی عددی)
    "national_id": r"\b\d{10}\b|\b\d{3}-\d{6}-\d\b",
    
    # شماره تلفن همراه ایرانی (نظیر 09123456789 یا +989123456789 یا 00989123456789)
    "mobile_number": r"\b(?:0098|\+98|0)?9\d{9}\b",
    
    # شماره کارت بانکی ۱۶ رقمی (با یا بدون خط فاصله و فاصله معمولی)
    "card_number": r"\b\d{16}\b|\b(?:\d{4}[- ]){3}\d{4}\b",
    
    # شماره شبا بانکی ایران (شامل پیشوند IR و ۲۴ رقم متوالی)
    "iban_number": r"\bIR\d{24}\b|\bIR\d{2}[- ]?(?:\d{4}[- ]?){5}\d{2}\b",
    
    # آدرس پست الکترونیکی (ایمیل عمومی)
    "email_address": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
}

# تعاریف برچسب‌های جایگزین فارسی جهت نمایش شکیل در خروجی داشبورد و پیش‌نمایش
MASK_TAGS: Dict[str, str] = {
    "national_id": "[کد ملی]",
    "mobile_number": "[شماره تلفن همراه]",
    "card_number": "[شماره کارت بانکی]",
    "iban_number": "[شماره شبا]",
    "email_address": "[آدرس ایمیل]"
}

def redact_text(text: str) -> str:
    """
    /// <summary>
    /// ماسک‌گذاری خودکار تمامی فیلدهای اطلاعاتی حساس یافت شده در متن خام
    /// </summary>
    /// <param name="text">متن نرمال‌سازی شده خام</param>
    /// <returns>متن نهایی سانسور شده و امن جهت ایندکس در دیتابیس برداری</returns>
    """
    if not text:
        return ""
        
    redacted = text
    
    for key, pattern in PII_PATTERNS.items():
        tag = MASK_TAGS[key]
        # جایگزینی الگو با برچسب فارسی متناظر
        redacted = re.sub(pattern, tag, redacted)
        
    return redacted

def redact_and_audit(text: str) -> Tuple[str, Dict[str, int]]:
    """
    /// <summary>
    /// ماسک‌گذاری متن خام به همراه شمارش دقیق تعداد موجودیت‌های پنهان شده جهت گزارش به پنل ادمین
    /// </summary>
    /// <param name="text">متن ورودی</param>
    /// <returns>یک توپل شامل متن سانسور شده و دیکشنری تعداد سانسورها به تفکیک مدل</returns>
    """
    if not text:
        return "", {}
        
    redacted = text
    audit_counts: Dict[str, int] = {}
    
    for key, pattern in PII_PATTERNS.items():
        # پیدا کردن تمامی تطابق‌های الگو در متن قبل از جایگزینی
        matches = re.findall(pattern, redacted)
        count = len(matches)
        
        if count > 0:
            audit_counts[key] = count
            tag = MASK_TAGS[key]
            # جایگزین کردن الگو
            redacted = re.sub(pattern, tag, redacted)
            
    if audit_counts:
        logger.info(f"PII Redaction Completed. Masked elements: {audit_counts}")
        
    return redacted, audit_counts
