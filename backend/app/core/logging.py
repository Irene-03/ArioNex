"""
/// <summary>
/// سیستم مدیریت لاگ‌نویسی متمرکز آریونکس (ArioNex Logging Configuration)
/// </summary>
/// <remarks>
/// تمامی لاگ‌های سیستمی تولید شده در این برنامه با ساختار منظم و در سطح‌های مختلف
/// به زبان انگلیسی تولید شده و به کنسول فرستاده می‌شوند.
/// </remarks>
"""

import logging
import sys

def setup_logging() -> None:
    """
    /// <summary>
    /// راه‌اندازی و کانفیگ ماژول لاگ‌نویسی پایتون
    /// </summary>
    /// <remarks>
    /// فرمت خروجی لاگ‌ها شامل زمان، نام فایل، سطح لاگ و پیام لاگ به زبان انگلیسی است.
    /// </remarks>
    """
    # Reconfigure stdout and stderr to handle UTF-8 Persian/Arabic text correctly on Windows/etc.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # تنظیم سطح لاگ برای کتابخانه‌های ثالث جهت کاهش شلوغی کنسول
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)
    
    logger = logging.getLogger("arionex")
    logger.info("ArioNex Enterprise Logging System Initialized Successfully.")
