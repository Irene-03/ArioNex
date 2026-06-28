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
_initialized: bool = False


def get_next_file_id() -> int:
    """
    /// <summary>
    /// تولید شناسه یکتای افزایشی برای فایل‌های آپلود شده
    /// </summary>
    """
    global _file_id_counter, _initialized
    with _lock:
        if not _initialized:
            from app.core.database import get_db_connection
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(MAX(id), 100) FROM documents;")
                    max_id = cur.fetchone()[0]
                    _file_id_counter = max(int(max_id), 100)
                conn.close()
                _initialized = True
            except Exception:
                # در صورت عدم امکان دسترسی به دیتابیس در زمان شروع، با مقدار پیش‌فرض ادامه بده
                pass
                
        _file_id_counter += 1
        return _file_id_counter
