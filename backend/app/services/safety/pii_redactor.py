"""
/// <summary>
/// موتور ایمنی و ماسک‌گذاری خودکار اطلاعات حساس شخصی (PII Redactor Safety Airlock)
/// </summary>
/// <remarks>
/// این ماژول وظیفه پایش و سانسور کردن اطلاعات شخصی حساس کاربران (کد ملی، شماره تلفن همراه،
/// ایمیل، شماره کارت‌های بانکی، شماره شبا و حساب) را با الگوهای منظم عبارات باقاعده بر عهده دارد
/// تا از ورود ناخواسته دیتای کاربری حساس به پایگاه برداری ممانعت شود.
///
/// برای جلوگیری از ماسک‌گذاری بیش از حد (False Positive)، الگوهای پرتکرار عددی (کد ملی و شماره
/// کارت بانکی) با الگوریتم‌های اعتبارسنجی چک‌سام و لوهن فیلتر می‌شوند؛ یعنی فقط اعدادی که
/// ساختار واقعی کد ملی ایرانی یا شماره کارت بانکی دارند ماسک می‌شوند و کدهای تراکنش، شناسه
/// سفارش و مقادیر عددی عادی دست‌نخورده باقی می‌مانند.
/// </remarks>
"""

import re
import logging
from typing import Callable, Dict, Tuple

logger = logging.getLogger("arionex.pii_redactor")

# ------------------------------------------------------------------
# اعتبارسنج‌های ساختاری جهت کاهش مثبت‌های کاذب
# ------------------------------------------------------------------
def _is_valid_national_id(value: str) -> bool:
    """اعتبارسنجی کد ملی ایرانی با الگوریتم چک‌سام (Mod 11)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10 or digits[0] == "0":
        return False
    if len(set(digits)) == 1:
        return False
    numbers = [int(d) for d in digits]
    total = sum(numbers[i] * (10 - i) for i in range(9))
    remainder = total % 11
    control = remainder if remainder < 2 else 11 - remainder
    return control == numbers[9]


def _is_valid_card_number(value: str) -> bool:
    """اعتبارسنجی شماره کارت بانکی با الگوریتم لوهن (Luhn)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) != 16:
        return False
    total = 0
    for index, digit in enumerate(reversed([int(d) for d in digits])):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


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

# اعتبارسنج‌های ساختاری — فقط تطابق‌هایی که از این توابع عبور کنند ماسک می‌شوند
PII_VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "national_id": _is_valid_national_id,
    "card_number": _is_valid_card_number,
}

# تعاریف برچسب‌های جایگزین فارسی جهت نمایش شکیل در خروجی داشبورد و پیش‌نمایش
MASK_TAGS: Dict[str, str] = {
    "national_id": "[کد ملی]",
    "mobile_number": "[شماره تلفن همراه]",
    "card_number": "[شماره کارت بانکی]",
    "iban_number": "[شماره شبا]",
    "email_address": "[آدرس ایمیل]"
}


def _mask_matches(text: str, key: str, pattern: str, tag: str, validator: Callable[[str], bool]) -> Tuple[str, int]:
    """یافتن تطابق‌های معتبر الگو و جایگزینی آن‌ها با برچسب ماسک."""
    hits = [
        match for match in re.finditer(pattern, text)
        if validator is None or validator(match.group(0))
    ]
    for match in reversed(hits):
        text = text[:match.start()] + tag + text[match.end():]
    return text, len(hits)


def redact_text(text: str) -> str:
    """
    /// <summary>
    /// ماسک‌گذاری خودکار تمامی فیلدهای اطلاعاتی حساس یافت شده در متن خام
    /// </summary>
    /// <param name="text">متن نرمال‌سازی شده خام</param>
    /// <returns>متن نهایی سانسور شده و امن جهت ایندکس در دیتابیس برداری</returns>
    """
    redacted, _ = redact_and_audit(text)
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
        tag = MASK_TAGS[key]
        validator = PII_VALIDATORS.get(key)
        redacted, count = _mask_matches(redacted, key, pattern, tag, validator)

        if count > 0:
            audit_counts[key] = count

    if audit_counts:
        logger.info(f"PII Redaction Completed. Masked elements: {audit_counts}")

    return redacted, audit_counts
