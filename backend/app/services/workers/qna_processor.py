"""
/// <summary>
/// FAQ files and support logs ingestion worker
/// </summary>
/// <remarks>
/// This module loads spreadsheet (CSV) files containing questions and answers, normalizes
/// and sanitizes them, and embeds each Q&A pair as a separate identifier, indexing it in the qna_query table of the vector database.
/// </remarks>
"""

import os
import logging
import pandas as pd

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text
from app.services.safety.pii_redactor import redact_text

logger = logging.getLogger("arionex.qna_processor")

class QnaDocumentProcessor:
    """
    /// <summary>
    /// Senior processor class for Excel/CSV files containing the organization's Q&A patterns
    /// </summary>
    """
    def __init__(self):
        # Check whether the module is enabled in the settings file
        self.is_enabled = settings.services.qna_processor

    def process_qna_csv(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// Process the Q&A CSV file: load rows, format texts, mask sensitive information, and store in the qna_query table
        /// </summary>
        /// <param name="temp_file_path">Path of the temporary file uploaded to the server</param>
        /// <param name="original_filename">Original name of the input file</param>
        /// <param name="file_id">Unique file identifier</param>
        /// <returns>Dictionary of execution status and the number of registered pairs</returns>
        """
        if not self.is_enabled:
            logger.warning(f"QnA Processor is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "chunks_count": 0}
            
        logger.info(f"Starting QnA ingestion pipeline for file: {original_filename} (ID: {file_id})")
        
        # 1. Load the CSV file using pandas
        try:
            # Read the file trying common encodings
            try:
                df = pd.read_csv(temp_file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding="windows-1256")
                
            # Unify column names (remove blank spaces)
            df.columns = [col.strip() for col in df.columns]
            
            # Check for the critical question and answer columns
            question_col = None
            answer_col = None
            
            # Smart matching of Persian and English column names
            for col in df.columns:
                col_lower = col.lower()
                if "question" in col_lower or col == "سوال" or col == "پرسش":
                    question_col = col
                if "answer" in col_lower or col == "جواب" or col == "پاسخ":
                    answer_col = col
                    
            if not question_col or not answer_col:
                # Try to pick the first and second columns as defaults if no name match
                if len(df.columns) >= 2:
                    question_col = df.columns[0]
                    answer_col = df.columns[1]
                    logger.warning(f"QnA columns not matched. Guessing defaults: Question='{question_col}', Answer='{answer_col}'")
                else:
                    raise ValueError("CSV must contain at least two columns for Question and Answer.")
                    
        except Exception as e:
            logger.error(f"Failed to read or parse QnA CSV file: {str(e)}")
            raise e

        # 2. Upload the original raw file to MinIO for documentation and archival
        try:
            object_name = f"qna/{file_id}/{original_filename}"
            archive_url = storage_manager.upload_file(object_name, temp_file_path, "text/csv")
            logger.info(f"QnA raw file archived successfully: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving QnA raw file failed: {str(e)}. Continuing database ingestion.")
            archive_url = "fallback_local"

        # 3. Iterate over each row, generate Q&A chunks, and store the vectors
        conn = None
        records_indexed = 0
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for idx, row in df.iterrows():
                    q = str(row[question_col]).strip()
                    a = str(row[answer_col]).strip()
                    
                    if not q or q.lower() == "nan" or not a or a.lower() == "nan":
                        continue  # Skip empty rows
                        
                    # Format the Q&A pair texts
                    formatted_chunk = f"Question: {q}, Answer: {a}"
                    
                    # Normalize the Persian texts
                    normalized_chunk = normalize_text(formatted_chunk)
                    
                    # Apply the privacy lock filter if enabled
                    if settings.security.pii_redaction:
                        final_chunk = redact_text(normalized_chunk)
                    else:
                        final_chunk = normalized_chunk
                        
                    # Generate the 3072-dimensional embedding using OpenAI
                    embedding = get_embedding(final_chunk)
                    sequence_id = idx + 1
                    
                    query = """
                        INSERT INTO qna_query (content, embedding, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s)
                    """
                    cur.execute(query, (final_chunk, embedding, file_id, sequence_id))
                    records_indexed += 1
                    
                conn.commit()
                
            logger.info(f"Successfully processed and indexed {records_indexed} Q&A records in qna_query.")
            return {
                "status": "success",
                "chunks_count": records_indexed,
                "total_rows": len(df),
                "question_column": question_col,
                "answer_column": answer_col,
                "storage_url": archive_url,
                "pii_masked_count": pii_masked_count
            }
        except Exception as e:
            logger.error(f"Failed to insert QnA records into database: {str(e)}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

# Global object for processing the organization's Q&A pairs
qna_processor = QnaDocumentProcessor()
