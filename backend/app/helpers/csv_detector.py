"""
/// <summary>
/// تشخیص‌دهنده هوشمند نوع فایل‌های CSV (ArioNex Smart CSV Type Detector)
/// </summary>
/// <remarks>
/// این ماژول با خواندن چند ردیف اول فایل CSV، تشخیص می‌دهد که فایل حاوی
/// الگوهای پرسش‌و‌پاسخ (QnA) است یا داده‌های ساختاریافته مالی/حسابداری.
///
/// منطق تشخیص:
///   - اگر هر یک از ستون‌ها شامل کلمه "question"، "answer"، "سوال" یا "پاسخ" باشد → QnA
///   - در غیر این صورت → Structured (مالی/حسابداری)
///
/// این helper از endpoint آپلود استخراج شده تا قابل تست مستقل و استفاده مجدد باشد.
/// </remarks>
"""

import logging
from typing import Literal

logger = logging.getLogger("arionex.csv_detector")

# نوع CSV قابل بازگشت
CsvType = Literal["qna", "structured"]


def detect_csv_type(file_path: str) -> CsvType:
    """
    /// <summary>
    /// تشخیص هوشمند نوع CSV بر اساس عنوان ستون‌ها (QnA در مقابل داده ساختاریافته)
    /// </summary>
    /// <param name="file_path">مسیر کامل فایل CSV آپلود شده روی سرور</param>
    /// <returns>"qna" اگر فایل الگوی پرسش‌وپاسخ دارد، "structured" در غیر این صورت</returns>
    /// <remarks>
    /// برای بهینه‌سازی، فقط ۵ ردیف اول خوانده می‌شود (nrows=5).
    /// تطابق با زبان فارسی و انگلیسی ستون‌ها هر دو پشتیبانی می‌شود.
    /// در صورت بروز هرگونه خطا در خواندن CSV، "structured" به عنوان پیش‌فرض ایمن برمی‌گردد.
    /// </remarks>
    """
    try:
        import pandas as pd

        # خواندن فقط header جهت کارایی بالا
        df = pd.read_csv(file_path, nrows=5)
        cols_lower = [str(c).lower().strip() for c in df.columns]

        # بررسی کلمات کلیدی QnA در نام ستون‌ها (فارسی + انگلیسی)
        is_qna = any(
            "question" in c
            or "answer" in c
            or c in ("سوال", "پرسش", "جواب", "پاسخ")
            for c in cols_lower
        )

        csv_type: CsvType = "qna" if is_qna else "structured"
        logger.info(f"CSV type detected for '{file_path}': '{csv_type}' (columns: {cols_lower[:5]})")
        return csv_type

    except Exception as e:
        logger.error(f"CSV type detection failed for '{file_path}': {str(e)}. Defaulting to 'structured'.")
        return "structured"
