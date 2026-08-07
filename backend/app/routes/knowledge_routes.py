"""
/// <summary>
/// ArioNex Knowledge Base ACL Router (ArioNex Knowledge Base ACL Router)
/// </summary>
/// <remarks>
/// This module lets users view the list of uploaded documents based on their role,
/// and allows admins to change access levels and delete documents.
/// </remarks>
"""

import io
import base64
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db_connection
from app.core.minio_client import storage_manager
from app.routes.auth_routes import get_current_user, require_admin

logger = logging.getLogger("arionex.knowledge_routes")
router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge — Document Management & ACL"])

# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------
class DocumentResponse(BaseModel):
    id: int = Field(..., description="شناسه عددی فایل")
    filename: str = Field(..., description="نام اصلی فایل")
    file_type: str = Field(..., description="نوع فایل (pdf, docx, csv, txt)")
    min_role_required: str = Field(..., description="حداقل نقش لازم برای دسترسی")
    created_at: str = Field(..., description="زمان بارگذاری")
    chunk_count: int = Field(0, description="تعداد قطعات برداری ایندکس شده برای این سند")
    status: str = Field("indexed", description="وضعیت ایندکس: indexed یا pending")

class DocumentContentResponse(BaseModel):
    filename: str
    file_type: str
    content: str = Field("", description="متن استخراج شده فایل (برای فایل‌های متنی)")
    mime_type: str = Field("text/plain", description="نوع MIME فایل")
    size_bytes: int = Field(0, description="حجم فایل به بایت")

class UpdateDocumentRole(BaseModel):
    min_role_required: str = Field(..., description="نقش مجاز: Admin یا Analyst")

class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_queries_today: int
    average_response_time: float
    total_pii_masked: int
    pdf_count: int
    csv_excel_count: int
    other_count: int
    disk_usage_gb: float
    total_tokens_used: int
    input_tokens_used: int = 0
    output_tokens_used: int = 0

# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@router.get("/stats", response_model=KnowledgeStatsResponse, summary="آمار و معیارهای پایگاه دانش و داشبورد")
async def get_knowledge_stats(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Total number of documents with indexed chunks (orphan records without chunks are excluded)
            cur.execute(
                """
                SELECT COUNT(*) FROM documents d
                WHERE (SELECT COUNT(*) FROM pg_supervisor s WHERE s.file_id = d.id) +
                      (SELECT COUNT(*) FROM qna_query q WHERE q.file_id = d.id) > 0
                """
            )
            total_documents = cur.fetchone()[0]

            # 2. Number of chunks in pg_supervisor and qna_query (only for registered documents)
            cur.execute(
                "SELECT COUNT(*) FROM pg_supervisor WHERE file_id IN (SELECT id FROM documents)"
            )
            chunks_sup = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM qna_query WHERE file_id IN (SELECT id FROM documents)"
            )
            chunks_qna = cur.fetchone()[0]
            total_chunks = chunks_sup + chunks_qna

            # 3. Number of today's queries
            cur.execute("SELECT COUNT(*) FROM pg_audit_logs WHERE timestamp >= CURRENT_DATE")
            total_queries_today = cur.fetchone()[0]

            # 4. Average RAG response time (today — in sync with total_queries_today)
            cur.execute(
                "SELECT COALESCE(AVG(response_time_ms), 0) FROM pg_audit_logs "
                "WHERE response_time_ms > 0 AND timestamp >= CURRENT_DATE "
                "AND (agent_type IS NULL OR agent_type NOT IN ('analyst', 'langgraph'))"
            )
            avg_response_ms = cur.fetchone()[0]
            average_response_time = round(float(avg_response_ms) / 1000.0, 1)

            # 5. Total masked PII count — actual sum recorded at upload time of each document
            cur.execute("SELECT COALESCE(SUM(pii_masked_count), 0) FROM documents")
            total_pii_masked = cur.fetchone()[0]

            # 5.1 Tokens consumed (excluding analyst/langgraph)
            cur.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM pg_audit_logs WHERE (agent_type IS NULL OR agent_type NOT IN ('analyst', 'langgraph'))")
            total_tokens_used = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(input_tokens), 0) FROM pg_audit_logs WHERE (agent_type IS NULL OR agent_type NOT IN ('analyst', 'langgraph'))")
            input_tokens_used = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(output_tokens), 0) FROM pg_audit_logs WHERE (agent_type IS NULL OR agent_type NOT IN ('analyst', 'langgraph'))")
            output_tokens_used = cur.fetchone()[0]

            # 6. Format breakdown (only documents with chunks)
            indexed_sql = """
                AND (SELECT COUNT(*) FROM pg_supervisor s WHERE s.file_id = d.id) +
                    (SELECT COUNT(*) FROM qna_query q WHERE q.file_id = d.id) > 0
            """
            cur.execute(f"SELECT COUNT(*) FROM documents d WHERE file_type IN ('pdf', 'PDF') {indexed_sql}")
            pdf_count = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM documents d WHERE file_type IN ('csv', 'CSV', 'xlsx', 'XLSX') {indexed_sql}")
            csv_excel_count = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM documents d WHERE file_type NOT IN ('pdf', 'PDF', 'csv', 'CSV', 'xlsx', 'XLSX') {indexed_sql}")
            other_count = cur.fetchone()[0]

            # 7. Estimate disk usage (e.g., each chunk is 15 kilobytes in the database)
            disk_usage_gb = round((total_chunks * 15) / (1024 * 1024), 3)

            return KnowledgeStatsResponse(
                total_documents=total_documents,
                total_chunks=total_chunks,
                total_queries_today=total_queries_today,
                average_response_time=average_response_time,
                total_pii_masked=total_pii_masked,
                pdf_count=pdf_count,
                csv_excel_count=csv_excel_count,
                other_count=other_count,
                disk_usage_gb=disk_usage_gb,
                total_tokens_used=total_tokens_used,
                input_tokens_used=input_tokens_used,
                output_tokens_used=output_tokens_used
            )
    except Exception as e:
        logger.error(f"Failed to fetch knowledge stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.get("/documents", response_model=List[DocumentResponse], summary="لیست اسناد بارگذاری شده (بر اساس نقش)")
async def list_documents(user: dict = Depends(get_current_user)):
    role = user.get("role")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # All documents are returned so that the full inventory is visible.
            # The "indexed" status is derived from the actual chunk count, so a
            # document that was uploaded but not (yet) indexed is still listed.
            role_filter = "AND d.min_role_required = 'Analyst'" if role != "Admin" else ""
            cur.execute(
                f"""
                SELECT d.id, d.filename, d.file_type, d.min_role_required, d.created_at,
                       COALESCE(ch.chunk_count, 0)
                FROM documents d
                LEFT JOIN (
                    SELECT file_id, COUNT(*) AS chunk_count
                    FROM (
                        SELECT file_id FROM pg_supervisor
                        UNION ALL
                        SELECT file_id FROM qna_query
                    ) all_chunks
                    GROUP BY file_id
                ) ch ON ch.file_id = d.id
                {role_filter}
                ORDER BY d.id DESC
                """
            )
            rows = cur.fetchall()
            return [
                DocumentResponse(
                    id=row[0],
                    filename=row[1],
                    file_type=row[2],
                    min_role_required=row[3],
                    created_at=str(row[4]),
                    chunk_count=row[5],
                    status="indexed" if row[5] > 0 else "pending"
                ) for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.put("/documents/{file_id}/role", response_model=DocumentResponse, summary="تغییر سطح دسترسی سند (فقط ادمین)")
async def update_document_role(
    file_id: int,
    payload: UpdateDocumentRole,
    admin: dict = Depends(require_admin)
):
    if payload.min_role_required not in ["Admin", "Analyst"]:
        raise HTTPException(status_code=400, detail="نقش نامعتبر است. فقط Admin یا Analyst مجاز است.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET min_role_required = %s
                WHERE id = %s
                RETURNING id, filename, file_type, min_role_required, created_at
                """,
                (payload.min_role_required, file_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="سند مورد نظر یافت نشد.")
            conn.commit()

            # Count indexed chunks for a consistent response
            cur.execute(
                """
                SELECT (SELECT COUNT(*) FROM pg_supervisor s WHERE s.file_id = %s) +
                       (SELECT COUNT(*) FROM qna_query q WHERE q.file_id = %s)
                """,
                (file_id, file_id)
            )
            chunk_count = cur.fetchone()[0]

            return DocumentResponse(
                id=row[0],
                filename=row[1],
                file_type=row[2],
                min_role_required=row[3],
                created_at=str(row[4]),
                chunk_count=chunk_count
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document access level: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.delete("/documents/{file_id}", summary="حذف سند و قطعات RAG مرتبط (فقط ادمین)")
async def delete_document(file_id: int, admin: dict = Depends(require_admin)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check the file exists
            cur.execute("SELECT filename FROM documents WHERE id = %s", (file_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="سند یافت نشد.")
            
            filename = row[0]
            
            # Delete text chunks from pg_supervisor
            cur.execute("DELETE FROM pg_supervisor WHERE file_id = %s", (file_id,))
            # Delete FAQ chunks from qna_query
            cur.execute("DELETE FROM qna_query WHERE file_id = %s", (file_id,))
            # Delete knowledge extractions and audits
            cur.execute("DELETE FROM extracted_entities WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM extracted_relationships WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM extracted_rules WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM compliance_audit_logs WHERE file_id = %s", (file_id,))
            
            # Final deletion from the documents table
            cur.execute("DELETE FROM documents WHERE id = %s", (file_id,))
            
            conn.commit()
            logger.info(f"Successfully deleted document '{filename}' (ID: {file_id}) and all associated vector/knowledge chunks.")
            return {"status": "success", "message": f"سند '{filename}' و تمامی منابع برداری مرتبط با آن با موفقیت حذف شدند."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/documents/{file_id}/content", response_model=DocumentContentResponse, summary="دریافت محتوای سند جهت پیش‌نمایش")
async def get_document_content(file_id: int, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, filename, file_type FROM documents WHERE id = %s",
                (file_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="سند مورد نظر یافت نشد.")

            doc_id, filename, file_type = row[0], row[1], row[2]

        # Determine the storage category based on file type
        if file_type in ("csv", "xlsx", "xls"):
            storage_category = "structured"
        elif file_type in ("txt",):
            storage_category = "unstructured"
        else:
            storage_category = "unstructured"

        object_name = f"{storage_category}/{doc_id}/{filename}"

        try:
            raw_bytes = storage_manager.get_object_data(object_name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="فایل اصلی سند در استوریج یافت نشد.")

        file_size = len(raw_bytes)
        content = ""
        mime_type = "application/octet-stream"

        # Extract text content based on file type
        if file_type in ("txt", "csv"):
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("windows-1256", errors="ignore")
            mime_type = "text/plain"

        elif file_type == "pdf":
            content = base64.b64encode(raw_bytes).decode("ascii")
            mime_type = "application/pdf"

        elif file_type in ("docx", "doc"):
            try:
                from docx import Document as Doc
                doc = Doc(io.BytesIO(raw_bytes))
                content = "\n".join([p.text for p in doc.paragraphs])
            except Exception:
                content = "[امکان استخراج متن از فایل Word وجود ندارد]"
            mime_type = "text/plain"

        elif file_type in ("jpg", "jpeg", "png"):
            content = base64.b64encode(raw_bytes).decode("ascii")
            mime_type = f"image/{file_type}"

        elif file_type in ("json", "xml", "mmd"):
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("windows-1256", errors="ignore")
            mime_type = "text/plain"

        else:
            content = "[نوع فایل قابل پیش‌نمایش نیست]"

        return DocumentContentResponse(
            filename=filename,
            file_type=file_type,
            content=content,
            mime_type=mime_type,
            size_bytes=file_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطا در دریافت محتوای سند: {str(e)}")
    finally:
        if conn:
            conn.close()
