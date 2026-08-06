"""
/// <summary>
/// Structured and accounting data files ingestion worker
/// </summary>
/// <remarks>
/// This module manages spreadsheets containing the organization's transaction and accounting codes.
/// Uploaded files are first validated, archived in the MinIO object storage or the local file system,
/// and then each row is indexed as a chunk in pg_supervisor so semantic search can be performed in RAG.
/// A valid path is also registered for access by the pandas interpreter (Analyst Agent).
/// </remarks>
"""

import os
import logging
import pandas as pd

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager, LOCAL_FALLBACK_DIR
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text
from app.services.safety.pii_redactor import redact_and_audit

logger = logging.getLogger("arionex.structured_processor")

class StructuredDataProcessor:
    """
    /// <summary>
    /// Management and validation class for structured financial and accounting files
    /// </summary>
    """
    def __init__(self):
        # Check whether the module is enabled in the settings
        self.is_enabled = settings.services.structured_data_analytics

    def process_structured_csv(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// Validate the CSV structure, upload to MinIO, and index each row in pgvector for semantic search
        /// </summary>
        /// <param name="temp_file_path">Physical path of the temporary uploaded file</param>
        /// <param name="original_filename">Original document name</param>
        /// <param name="file_id">Numeric file identifier</param>
        /// <returns>A dictionary containing the success status and column information</returns>
        """
        if not self.is_enabled:
            logger.warning(f"Structured Data Ingestion is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "columns": [], "chunks_count": 0}

        logger.info(f"Starting structured data ingestion pipeline for: {original_filename} (ID: {file_id})")

        # 1. Initial data structure validation with pandas to guarantee transaction integrity
        try:
            try:
                df = pd.read_csv(temp_file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding="windows-1256")

            columns_list = df.columns.tolist()
            rows_count = len(df)
            logger.info(f"Spreadsheet validated. Rows: {rows_count}, Columns: {columns_list}")
        except Exception as e:
            logger.error(f"Structured data validation failed: {str(e)}")
            raise ValueError(f"Invalid or corrupted CSV format: {str(e)}")

        # 2. Upload the original physical file to MinIO for reference by the analyst (Analyst Agent)
        try:
            object_name = f"structured/{file_id}/{original_filename}"
            archive_url = storage_manager.upload_file(object_name, temp_file_path, "text/csv")
            logger.info(f"Structured spreadsheet archived successfully at: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving structured spreadsheet failed: {str(e)}")
            archive_url = "fallback_local"

        # 3. Index each row in pgvector for RAG semantic search
        chunks_indexed = 0
        pii_masked_count = 0
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for idx, row in df.iterrows():
                    # Format each row as "col1: val1 | col2: val2 | ..."
                    row_parts = []
                    for col in columns_list:
                        val = str(row[col]).strip()
                        if val and val.lower() != "nan":
                            row_parts.append(f"{col}: {val}")

                    if not row_parts:
                        continue

                    raw_chunk = " | ".join(row_parts)

                    # Normalize the Persian texts
                    normalized_chunk = normalize_text(raw_chunk)

                    # Apply PII Redaction if enabled
                    if settings.security.pii_redaction:
                        final_chunk, pii_audit = redact_and_audit(normalized_chunk)
                        pii_masked_count += sum(pii_audit.values())
                    else:
                        final_chunk = normalized_chunk

                    # Generate the embedding with a zero fallback
                    try:
                        embedding = get_embedding(final_chunk)
                    except Exception as emb_err:
                        logger.warning(f"Embedding failed for row {idx} in '{original_filename}': {str(emb_err)}. Using zero-vector fallback.")
                        from app.core.embeddings import _get_embedding_dimension
                        embedding = [0.0] * _get_embedding_dimension()

                    sequence_id = idx + 1
                    cur.execute(
                        """
                        INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s, %s)
                        """,
                        (final_chunk, embedding, original_filename, file_id, sequence_id)
                    )
                    chunks_indexed += 1

                conn.commit()
            logger.info(f"Successfully indexed {chunks_indexed} rows from '{original_filename}' into pg_supervisor.")
        except Exception as e:
            logger.error(f"Failed to index structured CSV rows into pgvector: {str(e)}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

        return {
            "status": "success",
            "rows_count": rows_count,
            "chunks_count": chunks_indexed,
            "columns": columns_list,
            "storage_url": archive_url,
            "pii_masked_count": pii_masked_count
        }

    def get_local_path_for_analysis(self, file_id: int, filename: str) -> str:
        """
        /// <summary>
        /// Get the file's physical address on the server to feed the pandas and LangGraph engine
        /// </summary>
        /// <param name="file_id">Document identifier</param>
        /// <param name="filename">File name</param>
        /// <returns>A string containing the local physical path for reading the file</returns>
        """
        object_name = f"structured/{file_id}/{filename}"

        # If the local Fallback layer is enabled, return the physical path directly
        if storage_manager.is_fallback:
            local_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            if os.path.exists(local_path):
                return local_path
            else:
                raise FileNotFoundError(f"Local spreadsheet file not found at: {local_path}")
        else:
            # If the file is on MinIO, temporarily download it to the local folder
            local_temp_path = os.path.join(LOCAL_FALLBACK_DIR, object_name)
            os.makedirs(os.path.dirname(local_temp_path), exist_ok=True)

            try:
                storage_manager.download_file(object_name, local_temp_path)
                return local_temp_path
            except Exception as e:
                logger.error(f"Failed to fetch file from MinIO to local analysis environment: {str(e)}")
                raise e

# Global processor and validator object for structured financial documents
structured_processor = StructuredDataProcessor()
