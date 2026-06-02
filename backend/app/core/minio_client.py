"""
/// <summary>
/// مدیریت ذخیره‌ساز آبجکت استوریج مینی‌او (MinIO Object Storage Client Manager)
/// </summary>
/// <remarks>
/// این ماژول ارتباط با ذخیره‌ساز ابری MinIO را جهت ذخیره و بازیابی اسناد اصلی خام آپلود شده توسط کاربران
/// فراهم می‌کند. در صورت عدم در دسترس بودن سرور MinIO در فاز توسعه محلی، سیستم به صورت هوشمند
/// به پوشه محلی storage/raw_files به عنوان بک‌آپ سوئیچ می‌کند تا برنامه بدون کرش به کار خود ادامه دهد.
/// </remarks>
"""

import os
import logging
from minio import Minio
from app.core.config import settings

logger = logging.getLogger("arionex.minio")

# دایرکتوری محلی برای ذخیره‌سازی بک‌آپ فایل‌ها در صورت عدم اتصال به MinIO
LOCAL_FALLBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage",
    "raw_files"
)

class MinioStorageManager:
    """
    /// <summary>
    /// کلاس مدیریت و آپلود فایل‌ها به MinIO یا فایل سیستم محلی
    /// </summary>
    """
    def __init__(self):
        self.client = None
        self.is_fallback = False
        
        # تضمین ایجاد پوشه محلی بک‌آپ
        os.makedirs(LOCAL_FALLBACK_DIR, exist_ok=True)
        
        try:
            # بررسی نیاز به اتصال امن HTTPS (معمولا برای لوکال هاست کاذب است)
            is_secure = not ("localhost" in settings.minio_endpoint or "127.0.0.1" in settings.minio_endpoint)
            
            logger.info(f"Attempting to connect to MinIO at {settings.minio_endpoint}...")
            self.client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_root_user,
                secret_key=settings.minio_root_password,
                secure=is_secure
            )
            
            # تست اتصال با دریافت لیست باکت‌ها
            self.client.list_buckets()
            self._ensure_bucket_exists(settings.minio_bucket_name)
            logger.info("Successfully connected to MinIO Server.")
        except Exception as e:
            self.is_fallback = True
            logger.warning(
                f"MinIO Server is not available ({str(e)}). "
                f"ArioNex is automatically falling back to Local File System storage at: {LOCAL_FALLBACK_DIR}"
            )

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        /// <summary>
        /// ساخت باکت پیش‌فرض در صورت عدم وجود در سرور MinIO
        /// </summary>
        /// <param name="bucket_name">نام باکت</param>
        """
        if self.client and not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
            logger.info(f"Created default MinIO bucket: '{bucket_name}'")

    def upload_file(self, object_name: str, file_path: str, content_type: str = "application/octet-stream") -> str:
        """
        /// <summary>
        /// آپلود فایل به استوریج اصلی یا فایل سیستم محلی
        /// </summary>
        /// <param name="object_name">نام ذخیره‌سازی آبجکت (مانند نام فایل به همراه پیشوند)</param>
        /// <param name="file_path">مسیر فیزیکی فایل موقت جهت آپلود</param>
        /// <param name="content_type">نوع فایل (MIME Type)</param>
        /// <returns>یک رشته نشان‌دهنده مسیر ذخیره‌سازی نهایی یا شناسه آن</returns>
        """
        if self.is_fallback:
            # ذخیره‌سازی محلی
            dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            # ایجاد زیرشاخه اگر نام آبجکت شامل فولدر فرعی باشد
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # کپی فایل
            import shutil
            shutil.copy2(file_path, dest_path)
            logger.info(f"[Local Storage] Saved raw file: {object_name}")
            return f"local://{object_name}"
        else:
            # آپلود به MinIO
            try:
                self.client.fput_object(
                    settings.minio_bucket_name,
                    object_name,
                    file_path,
                    content_type=content_type
                )
                logger.info(f"[MinIO Storage] Successfully uploaded raw file: {object_name}")
                return f"minio://{settings.minio_bucket_name}/{object_name}"
            except Exception as e:
                logger.error(f"Failed to upload to MinIO: {str(e)}. Attempting local save as last resort.")
                # سوئیچ اضطراری به محلی
                dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
                import shutil
                shutil.copy2(file_path, dest_path)
                return f"local_emergency://{object_name}"

    def download_file(self, object_name: str, dest_path: str) -> None:
        """
        /// <summary>
        /// دانلود فایل از استوریج به یک مسیر موقت
        /// </summary>
        /// <param name="object_name">نام آبجکت ذخیره شده</param>
        /// <param name="dest_path">مسیر مقصد برای دانلود فایل</param>
        """
        if self.is_fallback:
            src_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            if os.path.exists(src_path):
                import shutil
                shutil.copy2(src_path, dest_path)
            else:
                raise FileNotFoundError(f"File not found in local fallback storage: {object_name}")
        else:
            try:
                self.client.fget_object(
                    settings.minio_bucket_name,
                    object_name,
                    dest_path
                )
            except Exception as e:
                logger.error(f"Failed to download from MinIO: {str(e)}")
                raise e

# آبجکت سراسری مدیریت فیزیکی اسناد خام
storage_manager = MinioStorageManager()
