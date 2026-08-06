"""
/// <summary>
/// Unstructured Document Ingestion Worker
/// </summary>
/// <remarks>
/// This module is responsible for loading PDF, Word and raw text files, extracting content, applying the safety airlock,
/// intelligent chunking, and finally generating vectors and storing the segments in the PostgreSQL database.
/// </remarks>
"""

import os
import io
import logging
import tempfile

import fitz
from docx import Document as Doc
from PIL import Image

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.core.embeddings import get_embedding
from app.services.workers.text_processor import normalize_text, chunk_text
from app.services.workers.ocr_engine import ocr_image_via_unlimited
from app.services.safety.pii_redactor import redact_and_audit

logger = logging.getLogger("arionex.unstructured_processor")

# ------------------------------------------------------------------
# Lazy-loaded PaddleOCR (single global instance)
# ------------------------------------------------------------------
_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(use_angle_cls=True, lang='fa', use_gpu=False)
            logger.info("PaddleOCR initialised (lang=fa, use_gpu=False)")
        except ImportError:
            logger.error("PaddleOCR not installed. Run: pip install paddleocr")
            raise
    return _ocr_instance


def _reshape_persian(text: str) -> str:
    """Reshape Arabic/Persian characters and apply BiDi algorithm.
    WARNING: get_display() reverses the string logically which breaks vector embeddings and LLMs!
    We should rely on logical text ordering.
    """
    return text


def _page_has_meaningful_text(text: str, min_chars: int = 15) -> bool:
    """Return True if extracted text is long enough to be real (not scanned/garbled)."""
    text = text.strip()
    if len(text) < min_chars:
        return False
    alpha = sum(1 for ch in text if ch.isalpha() or ch.isspace())
    return alpha > len(text) * 0.3


def _extract_page_fitz(page) -> str:
    """Stage 1: fast text extraction via PyMuPDF."""
    text = page.get_text()
    return _reshape_persian(text) if text.strip() else ""


def _extract_page_ocr(page, dpi: int = 300) -> str:
    """Stage 2: OCR via Unlimited-OCR (HTTP) with PaddleOCR CPU fallback."""
    try:
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
    except Exception:
        return ""

    # --- Sub-stage 2a: Unlimited-OCR via the vLLM/SGLang server (if enabled) ---
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        unlimited_text = ocr_image_via_unlimited(tmp_path)
        if unlimited_text.strip():
            return unlimited_text
    except Exception as e:
        logger.warning(f"Unlimited-OCR failed for scanned page: {str(e)}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # --- Sub-stage 2b: PaddleOCR (CPU) fallback ---
    try:
        img = Image.open(io.BytesIO(png_bytes))
    except Exception:
        return ""

    ocr = _get_ocr()
    try:
        result = ocr.ocr(img, cls=True)
    except Exception:
        return ""

    if not result or not result[0]:
        return ""

    lines = []
    for line_info in result[0]:
        text, conf = line_info[1]
        if conf and conf > 0.3:
            lines.append(text)
    return "\n".join(lines)


def split_into_semantic_windows(text: str, window_size: int = 3000, overlap: int = 500) -> list:
    """
    /// <summary>
    /// Split large texts into semantic windows with a specified size and overlap
    /// </summary>
    """
    if len(text) <= window_size:
        return [text]
        
    windows = []
    start = 0
    while start < len(text):
        end = start + window_size
        chunk = text[start:end]
        windows.append(chunk)
        start += (window_size - overlap)
        if start >= len(text) - overlap:
            break
            
    if start < len(text):
        windows.append(text[start:])
        
    return windows


class UnstructuredDocumentProcessor:
    """
    /// <summary>
    /// Senior processor class for text, PDF and Microsoft Word documents
    /// </summary>
    """
    def __init__(self):
        # Check whether the processor is enabled in the system toggle feature
        self.is_enabled = settings.services.unstructured_document_processor

    def parse_pdf(self, file_path: str) -> str:
        """
        /// <summary>
        /// Two-stage text extraction pipeline for PDF:
        ///   1. PyMuPDF (fitz) — fast text extraction when a text layer exists
        ///   2. PaddleOCR    — visual character recognition for scanned pages
        /// </summary>
        """
        text_content = []
        try:
            doc = fitz.open(file_path)
            total = len(doc)
            logger.info(f"PDF opened via PyMuPDF: {total} page(s)")

            for i in range(total):
                page = doc[i]

                # Stage 1: fast extraction with PyMuPDF
                page_text = _extract_page_fitz(page)

                if _page_has_meaningful_text(page_text):
                    text_content.append(page_text)
                else:
                    # Stage 2: fall back to PaddleOCR for the scanned page
                    logger.info(f"Page {i+1}/{total}: low-quality text → PaddleOCR fallback")
                    ocr_text = _extract_page_ocr(page)
                    text_content.append(ocr_text if ocr_text.strip() else page_text)

            return "\n".join(text_content)

        except Exception as e:
            logger.error(f"Failed to parse PDF file at {file_path}. Error: {str(e)}")
            raise e

    def parse_docx(self, file_path: str) -> str:
        """
        /// <summary>
        /// Extract all texts inside the Microsoft Word (DOCX) file
        /// </summary>
        """
        try:
            doc = Doc(file_path)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        except Exception as e:
            logger.error(f"Failed to parse DOCX file at {file_path}. Error: {str(e)}")
            raise e

    def parse_txt(self, file_path: str) -> str:
        """
        /// <summary>
        /// Read a plain raw text file (TXT)
        /// </summary>
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try common encodings if a Unicode problem occurs
            try:
                with open(file_path, "r", encoding="windows-1256") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read TXT file with windows-1256 encoding: {str(e)}")
                raise e
        except Exception as e:
            logger.error(f"Failed to read TXT file at {file_path}. Error: {str(e)}")
            raise e

    def process_document(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// Main document ingestion process: physical load, normalization, privacy lock, embedding generation and vector indexing
        /// </summary>
        /// <param name="temp_file_path">Path of the temporary physical file on the server</param>
        /// <param name="original_filename">Original name of the uploaded file</param>
        /// <param name="file_id">Numeric identifier assigned to the file for source tracking in chat</param>
        /// <returns>A dictionary containing the success status and the number of generated chunks</returns>
        """
        if not self.is_enabled:
            logger.warning(f"Unstructured Document Processor is disabled in config.yaml. Skipping file: {original_filename}")
            return {"status": "disabled", "chunks_count": 0}
            
        logger.info(f"Starting pipeline ingestion for unstructured file: {original_filename} (ID: {file_id})")
        
        # 1. Extract content based on the file extension
        _, ext = os.path.splitext(original_filename.lower())
        raw_text = ""
        
        if ext == ".pdf":
            raw_text = self.parse_pdf(temp_file_path)
        elif ext in [".docx", ".doc"]:
            raw_text = self.parse_docx(temp_file_path)
        elif ext in [".txt", ".json", ".xml", ".mmd"]:
            raw_text = self.parse_txt(temp_file_path)
        else:
            logger.error(f"Unsupported file format: {ext}")
            raise ValueError(f"Unsupported file extension: {ext}")
            
        if not raw_text.strip():
            logger.warning(f"Extracted empty text content from document: {original_filename}")
            return {"status": "empty", "chunks_count": 0}
            
        # 2. Persian text normalization layer
        normalized_text = normalize_text(raw_text)
        
        # 3. Safety airlock layer (PII Redaction) if enabled in the system
        pii_masked_count = 0
        if settings.security.pii_redaction:
            redacted_text, pii_audit = redact_and_audit(normalized_text)
            pii_masked_count = sum(pii_audit.values())
        else:
            redacted_text = normalized_text
            
        # 4. Upload the original file to MinIO simultaneously to keep an archive copy
        try:
            object_name = f"unstructured/{file_id}/{original_filename}"
            # Guess the file type for headers
            content_type = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "text/plain"

            archive_url = storage_manager.upload_file(object_name, temp_file_path, content_type)
            logger.info(f"File uploaded and archived at storage endpoint: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving raw file failed: {str(e)}. Continuing chunk indexing anyway.")
            archive_url = "fallback_local"

        # 5. Chunk, generate vectors, and index them in the PostgreSQL + pgvector database
        chunks_indexed = self._index_text_chunks(redacted_text, original_filename, file_id, archive_url)

        # 6. Launch the background knowledge extraction process (entities and rules) asynchronously (Celery Tasks)
        self._dispatch_knowledge_extraction(redacted_text, file_id)

        return {
            "status": "success",
            "chunks_count": chunks_indexed,
            "storage_url": archive_url,
            "pii_masked_count": pii_masked_count
        }

    def _index_text_chunks(self, redacted_text: str, original_filename: str, file_id: int, archive_url: str) -> int:
        """
        /// <summary>
        /// Chunk, embed, and index the given text into the PostgreSQL + pgvector database
        /// </summary>
        /// <param name="redacted_text">Normalized, PII-redacted text</param>
        /// <param name="original_filename">Original file name used for chunk labels</param>
        /// <param name="file_id">Numeric identifier of the file</param>
        /// <param name="archive_url">Storage URL of the archived raw file</param>
        /// <returns>Number of chunks successfully indexed</returns>
        """
        chunks = chunk_text(redacted_text, chunk_size=350, overlap=75)

        conn = None
        chunks_indexed = 0
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for idx, chunk in enumerate(chunks):
                    sequence_id = idx + 1
                    embedding = get_embedding(chunk)

                    query = """
                        INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s, %s)
                    """
                    cur.execute(query, (chunk, embedding, original_filename, file_id, sequence_id))
                    chunks_indexed += 1

                conn.commit()
            logger.info(f"Successfully processed and indexed {chunks_indexed} chunks for file '{original_filename}'.")
            return chunks_indexed
        except Exception as e:
            logger.error(f"Failed to insert chunks into database: {str(e)}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _dispatch_knowledge_extraction(redacted_text: str, file_id: int) -> None:
        """Launch background knowledge extraction (entities and rules) asynchronously via Celery tasks."""
        if settings.services.entity_extractor or settings.services.rule_extractor:
            logger.info(f"Dispatching background consolidated knowledge extraction task for file_id={file_id}...")
            from app.tasks.extractor_tasks import run_knowledge_extraction_pipeline_task
            run_knowledge_extraction_pipeline_task.delay(
                text=redacted_text,
                file_id=file_id,
                run_entities=settings.services.entity_extractor,
                run_rules=settings.services.rule_extractor
            )

    @staticmethod
    def _ocr_image_paddle(image_path: str) -> str:
        """
        /// <summary>
        /// OCR a single image with the local PaddleOCR engine (CPU)
        /// </summary>
        """
        try:
            img = Image.open(image_path)
        except Exception:
            return ""

        ocr = _get_ocr()
        try:
            result = ocr.ocr(img, cls=True)
        except Exception:
            return ""

        if not result or not result[0]:
            return ""

        lines = []
        for line_info in result[0]:
            text, conf = line_info[1]
            if conf and conf > 0.3:
                lines.append(text)
        return "\n".join(lines)

    def process_image(self, temp_file_path: str, original_filename: str, file_id: int) -> dict:
        """
        /// <summary>
        /// Image (JPG/PNG) OCR ingestion pipeline and vector indexing
        /// </summary>
        /// <param name="temp_file_path">Path of the temporary physical file on the server</param>
        /// <param name="original_filename">Original name of the uploaded file</param>
        /// <param name="file_id">Numeric identifier assigned to the file for source tracking in chat</param>
        /// <returns>A dictionary containing the success status and the number of generated chunks</returns>
        /// <remarks>
        /// OCR engine chain: Unlimited-OCR (HTTP) → PaddleOCR (CPU) → empty
        /// </remarks>
        """
        if not self.is_enabled:
            logger.warning(f"Unstructured Document Processor is disabled in config.yaml. Skipping image: {original_filename}")
            return {"status": "disabled", "chunks_count": 0}

        logger.info(f"Starting image OCR ingestion: {original_filename} (ID: {file_id})")

        # 1. Extract text via Unlimited-OCR (if enabled) then fall back to PaddleOCR
        raw_text = ocr_image_via_unlimited(temp_file_path)
        if not raw_text.strip():
            raw_text = self._ocr_image_paddle(temp_file_path)

        if not raw_text.strip():
            logger.warning(f"No text extracted from image: {original_filename}")
            return {"status": "empty", "chunks_count": 0}

        # 2. Persian text normalization layer
        normalized_text = normalize_text(raw_text)

        # 3. Safety airlock layer (PII Redaction) if enabled in the system
        pii_masked_count = 0
        if settings.security.pii_redaction:
            redacted_text, pii_audit = redact_and_audit(normalized_text)
            pii_masked_count = sum(pii_audit.values())
        else:
            redacted_text = normalized_text

        # 4. Upload the image to MinIO simultaneously to keep an archive copy
        try:
            object_name = f"images/{file_id}/{original_filename}"
            content_type = "image/jpeg" if original_filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
            archive_url = storage_manager.upload_file(object_name, temp_file_path, content_type)
            logger.info(f"Image uploaded and archived at storage endpoint: {archive_url}")
        except Exception as e:
            logger.error(f"Archiving image failed: {str(e)}. Continuing chunk indexing anyway.")
            archive_url = "fallback_local"

        # 5. Chunk, generate vectors, and index them in the PostgreSQL + pgvector database
        chunks_indexed = self._index_text_chunks(redacted_text, original_filename, file_id, archive_url)

        # 6. Launch the background knowledge extraction process (entities and rules) asynchronously (Celery Tasks)
        self._dispatch_knowledge_extraction(redacted_text, file_id)

        return {
            "status": "success",
            "chunks_count": chunks_indexed,
            "storage_url": archive_url,
            "pii_masked_count": pii_masked_count
        }

# Global object for processing general documents
unstructured_processor = UnstructuredDocumentProcessor()
