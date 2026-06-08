"""
/// <summary>
/// مدیریت ذخیره‌ساز آبجکت استوریج مینی‌او (MinIO Object Storage Client Manager)
/// </summary>
/// <remarks>
/// این ماژول ارتباط با ذخیره‌ساز ابری MinIO را جهت ذخیره و بازیابی اسناد اصلی خام آپلود شده توسط کاربران
/// فراهم می‌کند. در صورت عدم در دسترس بودن سرور MinIO در فاز توسعه محلی، سیستم به صورت هوشمند
/// به پوشه محلی storage/raw_files به عنوان بک‌آپ سوئیچ می‌کند تا برنامه بدون کرش به کار خود ادامه دهد.
///
/// حالت تست محلی (Local Data Directory Mode):
///   با تنظیم متغیر محیطی USE_LOCAL_DATA_DIR=true در فایل .env، سیستم به طور کامل
///   از MinIO صرف‌نظر کرده و تمام فایل‌ها را در پوشه data/ پروژه مدیریت می‌کند.
///   این حالت برای تست، توسعه و سازمان‌هایی بدون زیرساخت MinIO مناسب است.
/// </remarks>
"""

import os
import logging
from app.core.config import settings

logger = logging.getLogger("arionex.minio")

# --- بررسی فعال بودن حالت دایرکتوری محلی (Local Data Directory Mode) ---
# با تنظیم USE_LOCAL_DATA_DIR=true در فایل .env، سیستم به کلی از MinIO صرف‌نظر می‌کند
_USE_LOCAL = os.environ.get("USE_LOCAL_DATA_DIR", "false").strip().lower() == "true"

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

        # --- حالت دایرکتوری محلی: از MinIO کاملا صرف‌نظر می‌شود ---
        if _USE_LOCAL:
            self.is_fallback = True
            logger.info(
                "USE_LOCAL_DATA_DIR=true detected. "
                "ArioNex is running in Local Data Directory Mode. "
                "All file operations will use the local data/ directory. MinIO is bypassed."
            )
            return

        # --- حالت عادی: تلاش برای اتصال به MinIO ---
        try:
            from minio import Minio

            # بررسی نیاز به اتصال امن HTTPS (معمولا برای لوکال هاست غیرفعال است)
            is_secure = not (
                "localhost" in settings.minio_endpoint or
                "127.0.0.1" in settings.minio_endpoint
            )

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

    def upload_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        /// <summary>
        /// آپلود فایل به استوریج اصلی یا فایل سیستم محلی
        /// </summary>
        /// <param name="object_name">نام ذخیره‌سازی آبجکت</param>
        /// <param name="file_path">مسیر فیزیکی فایل موقت جهت آپلود</param>
        /// <param name="content_type">نوع MIME فایل</param>
        /// <returns>رشته شناسه مسیر ذخیره‌سازی نهایی</returns>
        """
        if self.is_fallback:
            import shutil
            dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            mode = "local-data-dir" if _USE_LOCAL else "local-fallback"
            logger.info(f"[{mode}] Saved raw file: {object_name}")
            return f"local://{object_name}"
        else:
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
                import shutil
                logger.error(f"Failed to upload to MinIO: {str(e)}. Attempting local save as last resort.")
                dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
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
                raise FileNotFoundError(
                    f"File not found in local fallback storage: {object_name}"
                )
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

    def put_object_data(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        /// <summary>
        /// ذخیره مستقیم داده باینری (Bytes) در MinIO یا فایل سیستم محلی
        /// </summary>
        """
        if self.is_fallback:
            dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(data)
            mode = "local-data-dir" if _USE_LOCAL else "local-fallback"
            logger.info(f"[{mode}] Saved object bytes: {object_name}")
            return f"local://{object_name}"
        else:
            import io
            try:
                data_stream = io.BytesIO(data)
                self.client.put_object(
                    settings.minio_bucket_name,
                    object_name,
                    data_stream,
                    len(data),
                    content_type=content_type
                )
                logger.info(f"[MinIO Storage] Successfully uploaded object: {object_name}")
                return f"minio://{settings.minio_bucket_name}/{object_name}"
            except Exception as e:
                logger.error(f"Failed to upload bytes to MinIO: {str(e)}. Falling back to local.")
                dest_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(data)
                return f"local_emergency://{object_name}"

    def get_object_data(self, object_name: str) -> bytes:
        """
        /// <summary>
        /// دریافت داده باینری (Bytes) یک آبجکت از MinIO یا فایل سیستم محلی
        /// </summary>
        """
        if self.is_fallback:
            src_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            if os.path.exists(src_path):
                with open(src_path, "rb") as f:
                    return f.read()
            else:
                raise FileNotFoundError(f"Object not found in local fallback: {object_name}")
        else:
            try:
                response = self.client.get_object(settings.minio_bucket_name, object_name)
                try:
                    return response.read()
                finally:
                    response.close()
                    response.release_conn()
            except Exception as e:
                logger.error(f"Failed to read from MinIO: {str(e)}. Trying local fallback.")
                src_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
                if os.path.exists(src_path):
                    with open(src_path, "rb") as f:
                        return f.read()
                raise e

    def list_objects(self, prefix: str) -> list[str]:
        """
        /// <summary>
        /// لیست کردن نام تمامی آبجکت‌ها تحت یک پیشوند (Prefix) مشخص
        /// </summary>
        """
        if self.is_fallback:
            prefix_dir = os.path.join(LOCAL_FALLBACK_DIR, prefix)
            if not os.path.exists(prefix_dir):
                return []
            
            found = []
            for root, _, files in os.walk(prefix_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, LOCAL_FALLBACK_DIR)
                    found.append(rel_path.replace("\\", "/"))
            return found
        else:
            try:
                objects = self.client.list_objects(
                    settings.minio_bucket_name,
                    prefix=prefix,
                    recursive=True
                )
                return [obj.object_name for obj in objects]
            except Exception as e:
                logger.error(f"Failed to list objects in MinIO for prefix {prefix}: {str(e)}")
                # تلاش در فولدر لوکال
                prefix_dir = os.path.join(LOCAL_FALLBACK_DIR, prefix)
                if os.path.exists(prefix_dir):
                    found = []
                    for root, _, files in os.walk(prefix_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, LOCAL_FALLBACK_DIR)
                            found.append(rel_path.replace("\\", "/"))
                    return found
                return []

    def delete_objects_in_prefix(self, prefix: str) -> None:
        """
        /// <summary>
        /// حذف تمامی آبجکت‌های تحت یک پیشوند (Prefix) مشخص
        /// </summary>
        """
        if self.is_fallback:
            import shutil
            prefix_dir = os.path.join(LOCAL_FALLBACK_DIR, prefix)
            if os.path.exists(prefix_dir):
                shutil.rmtree(prefix_dir)
                logger.info(f"[Local Fallback] Deleted folder prefix: {prefix}")
        else:
            try:
                objects = self.list_objects(prefix)
                for obj_name in objects:
                    self.client.remove_object(settings.minio_bucket_name, obj_name)
                logger.info(f"[MinIO Storage] Deleted all objects under prefix: {prefix}")
            except Exception as e:
                logger.error(f"Failed to delete prefix {prefix} from MinIO: {str(e)}")
                import shutil
                prefix_dir = os.path.join(LOCAL_FALLBACK_DIR, prefix)
                if os.path.exists(prefix_dir):
                    shutil.rmtree(prefix_dir)



# آبجکت سراسری مدیریت فیزیکی اسناد خام
storage_manager = MinioStorageManager()
