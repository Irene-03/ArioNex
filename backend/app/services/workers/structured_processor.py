"""
/// <summary>
/// پردازشگر فایل‌های داده ساختاریافته و حسابداری (Structured Data Ingestion Worker)
/// </summary>
/// <remarks>
/// این ماژول صفحات گسترده حاوی کدهای تراکنش و حسابداری سازمان را مدیریت می‌کند.
/// فایل‌های آپلود شده ابتدا اعتبارسنجی شده، در آبجکت استوریج مینی‌او یا فایل‌سیستم محلی بایگانی شده
/// و مسیر معتبر جهت دسترسی مفسر پانداس (Pandas Agent REPL) ثبت می‌گردد.
/// </remarks>
"""

import os
import logging
import pandas as pd

from app.core.config import settings
from app.core.minio_client import storage_manager, LOCAL_FALLBACK_DIR

logger = logging.getLogger("arionex.structured_processor")

class StructuredDataProcessor:
    """
    /// <summary>
    /// کلاس مدیریت و اعتبارسنجی فایل‌های ساختاریافته مالی و حسابداری
    /// </summary>
    """
    def __init__(self):
        # بررسی روشن بودن ماژول از تنظیمات
        self.is_enabled = settings.services.structured_data_analytics

    def process_structured_csv(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// اعتبارسنجی ساختار CSV و آپلود آن به فضای ذخیره‌سازی ابری مینی‌او
        /// </summary>
        /// <param name="temp_file_path">مسیر فیزیکی فایل آپلود شده موقت</param>
        /// <param name="original_filename">نام اصلی سند</param>
        /// <param name="file_id">شناسه عددی فایل</param>
        /// <returns>یک دیکشنری شامل وضعیت موفقیت و اطلاعات ستون‌ها</returns>
        """
        if not self.is_enabled:
            logger.warning(f"Structured Data Ingestion is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "columns": []}
            
        logger.info(f"Starting structured data validation for spreadsheet: {original_filename} (ID: {file_id})")
        
        # ۱. اعتبارسنجی اولیه ساختار داده با پانداس جهت تضمین سلامت تراکنش‌ها
        try:
            try:
                df = pd.read_csv(temp_file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding="windows-1256")
                
            columns_list = df.columns.tolist()
            rows_count = len(df)
            logger.info(f"Spreadsheet validated successfully. Rows: {rows_count}, Columns: {columns_list}")
        except Exception as e:
            logger.error(f"Structured data validation failed: {str(e)}")
            raise ValueError(f"Invalid or corrupted CSV format: {str(e)}")

        # ۲. آپلود فایل فیزیکی اصلی به مینی‌او جهت ارجاع تحلیلگر در لایه خواندن (Read Path)
        try:
            object_name = f"structured/{file_id}/{original_filename}"
            archive_url = storage_manager.upload_file(object_name, temp_file_path, "text/csv")
            logger.info(f"Structured spreadsheet archived successfully at: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving structured spreadsheet failed: {str(e)}")
            archive_url = "fallback_local"
            
        return {
            "status": "success",
            "rows_count": rows_count,
            "columns": columns_list,
            "storage_url": archive_url
        }

    def get_local_path_for_analysis(self, file_id: int, filename: str) -> str:
        """
        /// <summary>
        /// دریافت آدرس فیزیکی فایل روی سرور جهت تغذیه به موتور پانداس و LangGraph
        /// </summary>
        /// <param name="file_id">شناسه سند</param>
        /// <param name="filename">نام فایل</param>
        /// <returns>یک رشته شامل مسیر فیزیکی محلی برای خواندن فایل</returns>
        """
        object_name = f"structured/{file_id}/{filename}"
        
        # در صورت فعال بودن لایه Fallback محلی، مسیر فیزیکی را مستقیما برمی‌گردانیم
        if storage_manager.is_fallback:
            local_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            if os.path.exists(local_path):
                return local_path
            else:
                raise FileNotFoundError(f"Local spreadsheet file not found at: {local_path}")
        else:
            # در صورتی که فایل روی مینی‌او باشد، آن را موقتا به پوشه محلی دانلود می‌کنیم
            local_temp_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            os.makedirs(os.path.dirname(local_temp_path), exist_ok=True)
            
            try:
                storage_manager.download_file(object_name, local_temp_path)
                return local_temp_path
            except Exception as e:
                logger.error(f"Failed to fetch file from MinIO to local analysis environment: {str(e)}")
                raise e

# شیء سراسری پردازشگر و اعتبارسنج اسناد مالی ساختاریافته
structured_processor = StructuredDataProcessor()
