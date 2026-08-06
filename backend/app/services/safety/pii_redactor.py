"""
/// <summary>
/// Automatic masking and safety engine for sensitive personal information (PII Redactor Safety Airlock)
/// </summary>
/// <remarks>
/// This module is responsible for monitoring and censoring users' sensitive personal information
/// (national ID, mobile phone number, email, bank card numbers, IBAN and account numbers)
/// using regular expression patterns, so that unwanted sensitive user data is prevented from
/// entering the vector database.
///
/// To prevent over-masking (False Positive), high-frequency numeric patterns (national ID and
/// bank card number) are filtered using the check-sum and Luhn validation algorithms; that is,
/// only numbers that have the actual structure of an Iranian national ID or bank card number
/// are masked, while transaction codes, order IDs and ordinary numeric values remain untouched.
/// </remarks>
"""

import re
import logging
from typing import Callable, Dict, Tuple

logger = logging.getLogger("arionex.pii_redactor")

# ------------------------------------------------------------------
# Structural validators to reduce false positives
# ------------------------------------------------------------------
def _is_valid_national_id(value: str) -> bool:
    """Validate Iranian national ID with the check-sum (Mod 11) algorithm."""
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
    """Validate bank card number with the Luhn algorithm."""
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


# Regular expression patterns for identifying sensitive Iranian and international information
PII_PATTERNS: Dict[str, str] = {
    # Iranian ten-digit national ID (checking 10 consecutive numeric digits)
    "national_id": r"\b\d{10}\b|\b\d{3}-\d{6}-\d\b",

    # Iranian mobile phone number (e.g., 09123456789 or +989123456789 or 00989123456789)
    "mobile_number": r"\b(?:0098|\+98|0)?9\d{9}\b",

    # 16-digit bank card number (with or without hyphen and regular space)
    "card_number": r"\b\d{16}\b|\b(?:\d{4}[- ]){3}\d{4}\b",

    # Iranian bank IBAN number (including the IR prefix and 24 consecutive digits)
    "iban_number": r"\bIR\d{24}\b|\bIR\d{2}[- ]?(?:\d{4}[- ]?){5}\d{2}\b",

    # Email address (general email)
    "email_address": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
}

# Structural validators — only matches passing through these functions are masked
PII_VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "national_id": _is_valid_national_id,
    "card_number": _is_valid_card_number,
}

# Persian replacement tag definitions for polished display in the dashboard output and preview
MASK_TAGS: Dict[str, str] = {
    "national_id": "[کد ملی]",
    "mobile_number": "[شماره تلفن همراه]",
    "card_number": "[شماره کارت بانکی]",
    "iban_number": "[شماره شبا]",
    "email_address": "[آدرس ایمیل]"
}


def _mask_matches(text: str, key: str, pattern: str, tag: str, validator: Callable[[str], bool]) -> Tuple[str, int]:
    """Find valid pattern matches and replace them with the mask tag."""
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
    /// Automatically mask all sensitive information fields found in the raw text
    /// </summary>
    /// <param name="text">Raw normalized text</param>
    /// <returns>Final sanitized and secure text ready for indexing in the vector database</returns>
    """
    redacted, _ = redact_and_audit(text)
    return redacted


def redact_and_audit(text: str) -> Tuple[str, Dict[str, int]]:
    """
    /// <summary>
    /// Mask the raw text along with an accurate count of the hidden entities for reporting to the admin panel
    /// </summary>
    /// <param name="text">Input text</param>
    /// <returns>A tuple containing the sanitized text and a dictionary of masking counts per model</returns>
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
