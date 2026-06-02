"""
/// <summary>
/// ماژول مدیریت دایرکتوری داده‌های محلی آریونکس (ArioNex Local Data Directory Manager)
/// </summary>
/// <remarks>
/// این ماژول یک لایه ذخیره‌سازی کاملاً محلی بر پایه فایل‌سیستم را پیاده‌سازی می‌کند
/// که به عنوان جایگزین MinIO در محیط‌های توسعه، تست و سازمان‌هایی بدون زیرساخت MinIO
/// کار می‌کند. ساختار دایرکتوری‌ها به طور اتوماتیک ایجاد و مدیریت می‌شوند.
/// 
/// ساختار دایرکتوری:
///   data/
///   ├── unstructured/   (اسناد PDF/Word/TXT)
///   ├── structured/     (جداول مالی CSV/Excel)
///   ├── qna/            (الگوهای پرسش و پاسخ CSV)
///   └── raw_uploads/    (فایل‌های آپلود موقت بک‌اند)
/// </remarks>
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("arionex.local_storage")

# --- تعریف مسیر ریشه دایرکتوری داده‌ها ---
# مسیر: پوشه ario/data (در کنار پوشه backend)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_ROOT_DIR = os.path.join(_BACKEND_DIR, "data")

# زیرشاخه‌های اصلی داده‌ها
DATA_UNSTRUCTURED_DIR = os.path.join(DATA_ROOT_DIR, "unstructured")
DATA_STRUCTURED_DIR   = os.path.join(DATA_ROOT_DIR, "structured")
DATA_QNA_DIR          = os.path.join(DATA_ROOT_DIR, "qna")
DATA_RAW_UPLOADS_DIR  = os.path.join(DATA_ROOT_DIR, "raw_uploads")


def _ensure_data_dirs() -> None:
    """
    /// <summary>
    /// اطمینان از وجود تمام زیرشاخه‌های لازم در دایرکتوری data
    /// </summary>
    """
    for directory in [DATA_UNSTRUCTURED_DIR, DATA_STRUCTURED_DIR, DATA_QNA_DIR, DATA_RAW_UPLOADS_DIR]:
        os.makedirs(directory, exist_ok=True)

# ایجاد پوشه‌ها به محض لود شدن ماژول
_ensure_data_dirs()


def get_data_dir_for_type(file_type: str) -> str:
    """
    /// <summary>
    /// دریافت مسیر دایرکتوری مناسب بر اساس نوع داده
    /// </summary>
    /// <param name="file_type">نوع داده: 'unstructured' | 'structured' | 'qna' | 'raw'</param>
    /// <returns>مسیر کامل دایرکتوری مرتبط با نوع داده</returns>
    """
    mapping = {
        "unstructured": DATA_UNSTRUCTURED_DIR,
        "structured":   DATA_STRUCTURED_DIR,
        "qna":          DATA_QNA_DIR,
        "raw":          DATA_RAW_UPLOADS_DIR,
    }
    directory = mapping.get(file_type, DATA_RAW_UPLOADS_DIR)
    os.makedirs(directory, exist_ok=True)
    return directory


def save_uploaded_file(
    src_temp_path: str,
    original_filename: str,
    file_type: str,
    file_id: int
) -> str:
    """
    /// <summary>
    /// ذخیره‌سازی فایل آپلود شده به دایرکتوری مناسب در data/
    /// </summary>
    /// <param name="src_temp_path">مسیر فیزیکی فایل موقت دریافت شده از فرم‌داده</param>
    /// <param name="original_filename">نام اصلی فایل آپلود شده توسط کاربر</param>
    /// <param name="file_type">نوع داده برای انتخاب زیرشاخه مناسب</param>
    /// <param name="file_id">شناسه عددی منحصربه‌فرد فایل برای جلوگیری از تداخل</param>
    /// <returns>مسیر کامل فیزیکی ذخیره شده</returns>
    """
    base_dir = get_data_dir_for_type(file_type)

    # ساخت زیرشاخه file_id برای جلوگیری از تداخل نام فایل‌ها
    target_dir = os.path.join(base_dir, str(file_id))
    os.makedirs(target_dir, exist_ok=True)

    dest_path = os.path.join(target_dir, original_filename)
    shutil.copy2(src_temp_path, dest_path)

    logger.info(
        f"[LocalStorage] Saved '{original_filename}' → {dest_path}"
    )
    return dest_path


def get_file_path(file_type: str, file_id: int, filename: str) -> str:
    """
    /// <summary>
    /// دریافت مسیر فیزیکی یک فایل ذخیره‌شده در دایرکتوری محلی
    /// </summary>
    /// <param name="file_type">نوع داده</param>
    /// <param name="file_id">شناسه فایل</param>
    /// <param name="filename">نام فایل</param>
    /// <returns>مسیر کامل فایل روی دیسک</returns>
    """
    base_dir = get_data_dir_for_type(file_type)
    full_path = os.path.join(base_dir, str(file_id), filename)

    if not os.path.exists(full_path):
        raise FileNotFoundError(
            f"[LocalStorage] File not found: {full_path}\n"
            f"Hint: Make sure the file was ingested correctly into data/{file_type}/{file_id}/{filename}"
        )
    return full_path


def list_data_directory(file_type: str) -> list[dict]:
    """
    /// <summary>
    /// لیست تمام فایل‌های موجود در یک دایرکتوری داده محلی
    /// </summary>
    /// <param name="file_type">نوع داده</param>
    /// <returns>لیستی از دیکشنری‌های حاوی نام، سایز و مسیر فایل‌ها</returns>
    """
    base_dir = get_data_dir_for_type(file_type)
    files = []

    for root, dirs, filenames in os.walk(base_dir):
        # نادیده‌گیری فایل‌های راهنمای README
        for fname in filenames:
            if fname.startswith("README"):
                continue
            full = os.path.join(root, fname)
            files.append({
                "name": fname,
                "path": full,
                "size_bytes": os.path.getsize(full),
                "relative": os.path.relpath(full, DATA_ROOT_DIR),
            })

    return files


def ingest_from_data_directory(
    file_type: str,
    processor_fn,
    start_file_id: int = 1000
) -> list[dict]:
    """
    /// <summary>
    /// پردازش دسته‌ای تمام فایل‌های موجود در یک دایرکتوری داده محلی
    /// </summary>
    /// <remarks>
    /// این تابع تمام فایل‌های موجود در data/{file_type}/ را پیدا کرده
    /// و آن‌ها را از طریق تابع پردازشگر مشخص‌شده ایندکس می‌کند.
    /// مناسب برای pre-loading اولیه پایگاه دانش بدون نیاز به آپلود از UI است.
    /// </remarks>
    /// <param name="file_type">نوع داده برای تعیین پوشه منبع</param>
    /// <param name="processor_fn">تابع پردازشگر مرتبط (مثلاً unstructured_processor.process_document)</param>
    /// <param name="start_file_id">شناسه شروع برای فایل‌های دسته‌ای (پیش‌فرض: ۱۰۰۰)</param>
    /// <returns>لیست نتایج پردازش برای هر فایل</returns>
    """
    base_dir = get_data_dir_for_type(file_type)
    results = []
    file_counter = start_file_id

    logger.info(f"[LocalStorage] Starting batch ingest from: {base_dir}")

    for fname in sorted(os.listdir(base_dir)):
        # نادیده‌گیری فایل‌های راهنما و پوشه‌های sub-id
        if fname.startswith("README") or os.path.isdir(os.path.join(base_dir, fname)):
            continue

        file_path = os.path.join(base_dir, fname)
        logger.info(f"[LocalStorage] Processing file: {fname} (id={file_counter})")

        try:
            result = processor_fn(
                temp_file_path=file_path,
                original_filename=fname,
                file_id=file_counter
            )
            results.append({"file": fname, "file_id": file_counter, "result": result})
            logger.info(f"[LocalStorage] Successfully ingested: {fname}")
        except Exception as e:
            logger.error(f"[LocalStorage] Failed to process '{fname}': {str(e)}")
            results.append({"file": fname, "file_id": file_counter, "error": str(e)})

        file_counter += 1

    logger.info(f"[LocalStorage] Batch ingest complete. Processed {len(results)} files from data/{file_type}/")
    return results
