"""
/// <summary>
/// MinIO object storage manager (MinIO Object Storage Client Manager)
/// </summary>
/// <remarks>
/// This module provides connectivity with the MinIO cloud storage for storing and retrieving raw original documents uploaded by users.
/// If the MinIO server is unavailable during local development, the system intelligently
/// switches to the local storage/raw_files folder as a backup so the application keeps working without crashing.
///
/// Local test mode (Local Data Directory Mode):
///   By setting the USE_LOCAL_DATA_DIR=true environment variable in the .env file, the system completely
///   bypasses MinIO and manages all files in the project's data/ folder.
///   This mode is suitable for testing, development, and organizations without MinIO infrastructure.
/// </remarks>
"""

import os
import logging
from app.core.config import settings

logger = logging.getLogger("arionex.minio")

# --- Check whether the Local Data Directory Mode is enabled ---
# By setting USE_LOCAL_DATA_DIR=true in the .env file, the system completely bypasses MinIO
_USE_LOCAL = os.environ.get("USE_LOCAL_DATA_DIR", "false").strip().lower() == "true"

# Local directory for backing up files in case MinIO is unreachable
LOCAL_FALLBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage",
    "raw_files"
)


class MinioStorageManager:
    """
    /// <summary>
    /// Class for managing and uploading files to MinIO or the local file system
    /// </summary>
    """
    def __init__(self):
        self.client = None
        self.is_fallback = False

        # Ensure the local backup folder is created
        os.makedirs(LOCAL_FALLBACK_DIR, exist_ok=True)

        # --- Local data directory mode: MinIO is completely bypassed ---
        if _USE_LOCAL:
            self.is_fallback = True
            logger.info(
                "USE_LOCAL_DATA_DIR=true detected. "
                "ArioNex is running in Local Data Directory Mode. "
                "All file operations will use the local data/ directory. MinIO is bypassed."
            )
            return

        # --- Normal mode: attempt to connect to MinIO ---
        try:
            from minio import Minio

            # Check whether a secure HTTPS connection is required (usually disabled for localhost)
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

            # Test the connection by fetching the list of buckets
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
        /// Create the default bucket if it does not exist on the MinIO server
        /// </summary>
        /// <param name="bucket_name">Bucket name</param>
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
        /// Upload a file to the primary storage or the local file system
        /// </summary>
        /// <param name="object_name">Object storage name</param>
        /// <param name="file_path">Physical path of the temporary file to upload</param>
        /// <param name="content_type">MIME type of the file</param>
        /// <returns>String identifier of the final storage path</returns>
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
        /// Download a file from the storage to a temporary path
        /// </summary>
        /// <param name="object_name">Stored object name</param>
        /// <param name="dest_path">Destination path for downloading the file</param>
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
        /// Store binary data (bytes) directly in MinIO or the local file system
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
        /// Retrieve the binary data (bytes) of an object from MinIO or the local file system
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
        /// List the names of all objects under a given prefix
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
                # Try in the local folder
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
        /// Delete all objects under a given prefix
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



# Global object for physically managing raw documents
storage_manager = MinioStorageManager()
