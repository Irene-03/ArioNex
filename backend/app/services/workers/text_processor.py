"""
/// <summary>
/// ماژول پردازش، نرمال‌سازی و چانک‌سازی متون فارسی (Farsi Text Normalizer & Chunker Worker)
/// </summary>
/// <remarks>
/// این ماژول وظیفه پاک‌سازی متون فارسی خام، حذف علائم زائد، یکدست‌سازی نویسه‌ها و اعداد،
/// و شکستن متون طولانی به چانک‌های هم‌پوشان (Sliding Window Chunks) را بر عهده دارد.
/// </remarks>
"""

import re
import logging
from typing import List
from hazm import Normalizer

logger = logging.getLogger("arionex.text_processor")

# نمونه‌سازی از نرمال‌ساز Hazm بدون دستکاری اتوماتیک فاصله‌ها برای بالا رفتن سرعت چانک‌ساز
try:
    normalizer = Normalizer(correct_spacing=False)
except Exception as e:
    logger.error(f"Failed to initialize Hazm Normalizer: {str(e)}. Using fallback spacing rules.")
    normalizer = None

def remove_diacritics(text: str) -> str:
    """
    /// <summary>
    /// حذف اعراب و حرکت‌های زائد زبان عربی/فارسی از متن
    /// </summary>
    /// <param name="text">متن ورودی</param>
    /// <returns>متن فاقد اعراب</returns>
    """
    if not text:
        return ""
    # الگو حذف تنوین، تشدید، فتحه، ضمه، کسره و سکون
    return re.sub(r'[\u064B-\u0652]', '', text)

def normalize_text(text: str) -> str:
    """
    /// <summary>
    /// یکدست‌سازی و نرمال‌سازی کامل متون فارسی و عربی (Unicode Normalization)
    /// </summary>
    /// <param name="text">رشته متنی خام ورودی</param>
    /// <returns>رشته متنی کاملاً فارسی و تمیز شده</returns>
    /// <remarks>
    /// این متد حروف ی/ک عربی را اصلاح کرده، اعدا عربی و فارسی را به رقم‌های غربی (0-9) تبدیل می‌کند تا
    /// جستارهای ریاضی و حسابداری REPL روی آن‌ها بدون خطا کار کنند و علائم نگارشی را استاندارد می‌کند.
    /// </remarks>
    """
    if not text:
        return ""
        
    # استفاده از نرمال‌ساز هضم در صورت لود موفق
    if normalizer:
        text = normalizer.normalize(text)
        
    # جایگزینی نیم‌فاصله‌های غیر استاندارد با فاصله معمولی جهت بهینه‌سازی چانک‌سازی کلمات
    text = text.replace("\u200c", " ")
    
    # یکدست‌سازی حروف عربی و فارسی
    arabic_to_persian = {
        "ي": "ی", 
        "ك": "ک", 
        "ؤ": "و", 
        "إ": "ا", 
        "أ": "ا", 
        "ة": "ه",
        "ى": "ی"
    }
    for ar, fa in arabic_to_persian.items():
        text = text.replace(ar, fa)
        
    # تبدیل تمامی رقم‌های عربی و فارسی به اعداد انگلیسی جهت سازگاری کامل با پردازشگر محاسباتی پانداس
    arabic_numbers = "٠١٢٣٤٥٦٧٨٩"
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹"
    western_numbers = "0123456789"
    
    # ابتدا عربی به فارسی
    text = text.translate(str.maketrans(arabic_numbers, persian_numbers))
    # سپس فارسی به انگلیسی
    text = text.translate(str.maketrans(persian_numbers, western_numbers))
    
    # یکدست‌سازی علائم نگارشی فارسی به انگلیسی جهت ممانعت از کرش کردن مفسرهای پایتون
    persian_punct = "،؛؟«»"
    english_punct = ",;?\"\""
    text = text.translate(str.maketrans(persian_punct, english_punct))
    
    # حذف حرکت‌ها و اعراب
    text = remove_diacritics(text)
    
    # حذف فواصل اضافی زائد
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def chunk_text(text: str, chunk_size: int = 350, overlap: int = 75) -> List[str]:
    """
    /// <summary>
    /// شکستن متون طولانی به چانک‌های معنایی کوچک‌تر بر اساس تعداد کلمات با هم‌پوشانی لغزان
    /// </summary>
    /// <param name="text">متن نرمال‌سازی شده نهایی</param>
    /// <param name="chunk_size">تعداد کلمات هر چانک (پیش‌فرض: ۳۵۰ کلمه)</param>
    /// <param name="overlap">تعداد کلمات مشترک هم‌پوشانی (پیش‌فرض: ۷۵ کلمه)</param>
    /// <returns>لیستی از چانک‌های متنی رشته‌ای</returns>
    /// <exception cref="ValueError">در صورتی که پارامترها نامعتبر باشند</exception>
    """
    if not text:
        return []
        
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        logger.error(f"Invalid chunking parameters: chunk_size={chunk_size}, overlap={overlap}")
        raise ValueError("chunk_size must be positive and overlap must be less than chunk_size")
        
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end == len(words):
            break
            
        # شیفت دادن موقعیت شروع پنجره بر اساس میزان اورلپ
        start += chunk_size - overlap
        
    logger.info(f"Successfully chunked document text into {len(chunks)} overlapping parts (size={chunk_size}, overlap={overlap}).")
    return chunks
