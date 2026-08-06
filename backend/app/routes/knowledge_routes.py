"""
/// <summary>
/// روتر مدیریت اسناد و سطح دسترسی‌ها (ArioNex Knowledge Base ACL Router)
/// </summary>
/// <remarks>
/// این ماژول امکان مشاهده لیست اسناد بارگذاری شده را بر اساس نقش کاربر فراهم ساخته
/// و به مدیران اجازه تغییر سطح دسترسی و حذف اسناد را می‌دهد.
/// </remarks>
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.core.database import get_db_connection
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

# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@router.get("/stats", response_model=KnowledgeStatsResponse, summary="آمار و معیارهای پایگاه دانش و داشبورد")
async def get_knowledge_stats(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # ۱. تعداد کل اسناد دارای قطعات ایندکس شده (رکوردهای یتیم و بدون chunk حذف می‌شوند)
            cur.execute(
                """
                SELECT COUNT(*) FROM documents d
                WHERE (SELECT COUNT(*) FROM pg_supervisor s WHERE s.file_id = d.id) +
                      (SELECT COUNT(*) FROM qna_query q WHERE q.file_id = d.id) > 0
                """
            )
            total_documents = cur.fetchone()[0]

            # ۲. تعداد قطعات در pg_supervisor و qna_query (فقط مربوط به اسناد ثبت شده)
            cur.execute(
                "SELECT COUNT(*) FROM pg_supervisor WHERE file_id IN (SELECT id FROM documents)"
            )
            chunks_sup = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM qna_query WHERE file_id IN (SELECT id FROM documents)"
            )
            chunks_qna = cur.fetchone()[0]
            total_chunks = chunks_sup + chunks_qna

            # ۳. تعداد پرسش‌های امروز
            cur.execute("SELECT COUNT(*) FROM pg_audit_logs WHERE timestamp >= CURRENT_DATE")
            total_queries_today = cur.fetchone()[0]

            # ۴. میانگین زمان پاسخ RAG (امروز — هماهنگ با total_queries_today)
            cur.execute(
                "SELECT COALESCE(AVG(response_time_ms), 1200) FROM pg_audit_logs "
                "WHERE response_time_ms > 0 AND timestamp >= CURRENT_DATE"
            )
            avg_response_ms = cur.fetchone()[0]
            average_response_time = round(float(avg_response_ms) / 1000.0, 1)

            # ۵. تعداد کل PIIهای ماسک شده — جمع واقعی ثبت‌شده هنگام آپلود هر سند
            cur.execute("SELECT COALESCE(SUM(pii_masked_count), 0) FROM documents")
            total_pii_masked = cur.fetchone()[0]

            # ۵.۱ توکن‌های مصرفی
            cur.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM pg_audit_logs")
            total_tokens_used = cur.fetchone()[0]

            # ۶. تفکیک فرمت‌ها (فقط اسناد دارای chunk)
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

            # ۷. تخمین حجم دیسک (مثلاً هر چانک ۱۵ کیلوبایت در دیتابیس)
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
                total_tokens_used=total_tokens_used
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
            # فقط اسنادی که واقعاً قطعات برداری ایندکس شده دارند برمی‌گردد.
            # رکوردهای قدیمی و یتیم (بدون هیچ chunk) نمایش داده نمی‌شوند.
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
                WHERE COALESCE(ch.chunk_count, 0) > 0
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
                    chunk_count=row[5]
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

            # محاسبه تعداد قطعات ایندکس شده برای پاسخ سازگار
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
            # بررسی وجود فایل
            cur.execute("SELECT filename FROM documents WHERE id = %s", (file_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="سند یافت نشد.")
            
            filename = row[0]
            
            # حذف چانک‌های متنی از pg_supervisor
            cur.execute("DELETE FROM pg_supervisor WHERE file_id = %s", (file_id,))
            # حذف چانک‌های FAQ از qna_query
            cur.execute("DELETE FROM qna_query WHERE file_id = %s", (file_id,))
            # حذف استخراج‌های دانش و ممیزی‌ها
            cur.execute("DELETE FROM extracted_entities WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM extracted_relationships WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM extracted_rules WHERE file_id = %s", (file_id,))
            cur.execute("DELETE FROM compliance_audit_logs WHERE file_id = %s", (file_id,))
            
            # حذف نهایی از جدول documents
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
