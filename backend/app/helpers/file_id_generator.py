"""
/// <summary>
/// مولد شناسه فایل‌های آپلود شده (ArioNex File ID Generator)
/// </summary>
/// <remarks>
/// این ماژول یک شمارنده thread-safe برای تولید شناسه‌های منحصر‌به‌فرد فایل‌های آپلود شده
/// فراهم می‌کند. این شمارنده به عنوان جایگزین موقت sequence دیتابیس در مرحله توسعه استفاده می‌شود.
///
/// نکته مهم: در محیط تولید، باید از SERIAL/SEQUENCE پستگرس یا UUID استفاده شود.
/// شمارنده فعلی در حافظه نگهداری می‌شود و پس از restart سرور reset می‌شود.
/// </remarks>
"""

import threading

# شمارنده سراسری با lock برای thread-safety
_lock = threading.Lock()
_file_id_counter: int = 100


def get_next_file_id() -> int:
    """
    /// <summary>
    /// تولید شناسه یکتای افزایشی برای فایل‌های آپلود شده
    /// </summary>
    /// <returns>یک عدد صحیح منحصربه‌فرد به عنوان شناسه فایل</returns>
    /// <remarks>
    /// از threading.Lock برای جلوگیری از race condition در درخواست‌های همزمان استفاده می‌شود.
    /// شناسه از ۱۰۱ شروع می‌شود — ۱۰۰ اول برای داده‌های demo/seed رزرو هستند.
    /// در محیط production، این را با RETURNING id از INSERT پستگرس جایگزین کنید.
    /// </remarks>
    """
    global _file_id_counter
    with _lock:
        _file_id_counter += 1
        return _file_id_counter
