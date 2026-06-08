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

class UpdateDocumentRole(BaseModel):
    min_role_required: str = Field(..., description="نقش مجاز: Admin یا Analyst")

# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@router.get("/documents", response_model=List[DocumentResponse], summary="لیست اسناد بارگذاری شده (بر اساس نقش)")
async def list_documents(user: dict = Depends(get_current_user)):
    role = user.get("role")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if role == "Admin":
                # ادمین به تمام اسناد دسترسی دارد
                cur.execute(
                    "SELECT id, filename, file_type, min_role_required, created_at FROM documents ORDER BY id DESC"
                )
            else:
                # تحلیل‌گر فقط اسناد با سطح Analyst را می‌بیند
                cur.execute(
                    "SELECT id, filename, file_type, min_role_required, created_at FROM documents WHERE min_role_required = 'Analyst' ORDER BY id DESC"
                )
            rows = cur.fetchall()
            return [
                DocumentResponse(
                    id=row[0],
                    filename=row[1],
                    file_type=row[2],
                    min_role_required=row[3],
                    created_at=str(row[4])
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
            return DocumentResponse(
                id=row[0],
                filename=row[1],
                file_type=row[2],
                min_role_required=row[3],
                created_at=str(row[4])
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
