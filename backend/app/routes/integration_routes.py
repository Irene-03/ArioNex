"""
/// <summary>
/// روتر مدیریت ادغام‌ها و اتصالات آریونکس (ArioNex Integrations Management Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت‌های مدیریت ابزارک‌های وب‌سایت و کلیدهای API را تعریف می‌کند.
/// عملیات‌ها مستقیماً روی دیتابیس PostgreSQL با استفاده از کانکشن سراسری اجرا می‌شوند.
/// </remarks>
"""

import logging
import secrets
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import get_db_connection

logger = logging.getLogger("arionex.integration_routes")
router = APIRouter(prefix="/v1/integrations", tags=["Integrations — Widgets & API Keys"])


# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------

class WidgetCreate(BaseModel):
    name: str = Field(..., description="نام ابزارک")
    url: str = Field(..., description="آدرس دامنه سایت")
    welcome_message: Optional[str] = Field(None, description="پیام خوش‌آمدگویی")
    theme_color: Optional[str] = Field("#1a2744", description="رنگ اصلی")
    accent_color: Optional[str] = Field("#c4894a", description="رنگ ثانویه")
    is_active: Optional[bool] = Field(True, description="وضعیت فعال بودن")


class WidgetResponse(BaseModel):
    id: int
    name: str
    url: str
    welcome_message: Optional[str]
    theme_color: Optional[str]
    accent_color: Optional[str]
    is_active: bool


class APIKeyCreate(BaseModel):
    name: str = Field(..., description="نام کلید API برای شناسایی (مثلا CRM)")


class APIKeyResponse(BaseModel):
    id: int
    name: str
    api_key: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None


# -------------------------------------------------------------------
# Website Widgets Endpoints
# -------------------------------------------------------------------

@router.get("/widgets", response_model=List[WidgetResponse], summary="لیست ابزارک‌های ثبت شده")
async def list_widgets():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, url, welcome_message, theme_color, accent_color, is_active FROM website_widgets ORDER BY id DESC"
            )
            rows = cur.fetchall()
            return [
                WidgetResponse(
                    id=row[0],
                    name=row[1],
                    url=row[2],
                    welcome_message=row[3],
                    theme_color=row[4],
                    accent_color=row[5],
                    is_active=row[6]
                ) for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to list widgets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/widgets", response_model=WidgetResponse, summary="ثبت ابزارک جدید")
async def create_widget(widget: WidgetCreate):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # بررسی تکراری نبودن دامنه
            cur.execute("SELECT id FROM website_widgets WHERE url = %s", (widget.url,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="ابزارک با این دامنه قبلاً ثبت شده است.")
            
            cur.execute(
                """
                INSERT INTO website_widgets (name, url, welcome_message, theme_color, accent_color, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, url, welcome_message, theme_color, accent_color, is_active
                """,
                (widget.name, widget.url, widget.welcome_message, widget.theme_color, widget.accent_color, widget.is_active)
            )
            row = cur.fetchone()
            conn.commit()
            return WidgetResponse(
                id=row[0],
                name=row[1],
                url=row[2],
                welcome_message=row[3],
                theme_color=row[4],
                accent_color=row[5],
                is_active=row[6]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create widget: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.put("/widgets/{widget_id}", response_model=WidgetResponse, summary="بروزرسانی ابزارک")
async def update_widget(widget_id: int, widget: WidgetCreate):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE website_widgets
                SET name = %s, url = %s, welcome_message = %s, theme_color = %s, accent_color = %s, is_active = %s
                WHERE id = %s
                RETURNING id, name, url, welcome_message, theme_color, accent_color, is_active
                """,
                (widget.name, widget.url, widget.welcome_message, widget.theme_color, widget.accent_color, widget.is_active, widget_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="ابزارک یافت نشد.")
            conn.commit()
            return WidgetResponse(
                id=row[0],
                name=row[1],
                url=row[2],
                welcome_message=row[3],
                theme_color=row[4],
                accent_color=row[5],
                is_active=row[6]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update widget: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.delete("/widgets/{widget_id}", summary="حذف ابزارک")
async def delete_widget(widget_id: int):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM website_widgets WHERE id = %s RETURNING id", (widget_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="ابزارک یافت نشد.")
            conn.commit()
            return {"status": "success", "message": "Widget deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete widget: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


# -------------------------------------------------------------------
# API Keys Endpoints
# -------------------------------------------------------------------

@router.get("/apikeys", response_model=List[APIKeyResponse], summary="لیست کلیدهای API")
async def list_apikeys():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, api_key, is_active, created_at, last_used_at FROM api_keys ORDER BY id DESC"
            )
            rows = cur.fetchall()
            return [
                APIKeyResponse(
                    id=row[0],
                    name=row[1],
                    # ماسک کردن کلید به صورت anx_live_...xxxx برای امنیت در لیست
                    api_key=row[2][:12] + "..." + row[2][-4:],
                    is_active=row[3],
                    created_at=str(row[4]),
                    last_used_at=str(row[5]) if row[5] else None
                ) for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/apikeys", response_model=APIKeyResponse, summary="تولید کلید API جدید")
async def create_apikey(payload: APIKeyCreate):
    conn = None
    try:
        # تولید یک توکن رندوم امن با پیشوند آریونکس
        token = "anx_live_" + secrets.token_hex(24)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys (name, api_key, is_active)
                VALUES (%s, %s, TRUE)
                RETURNING id, name, api_key, is_active, created_at
                """,
                (payload.name, token)
            )
            row = cur.fetchone()
            conn.commit()
            return APIKeyResponse(
                id=row[0],
                name=row[1],
                api_key=row[2],  # اینجا کلید کامل را فقط یکبار برمی‌گردانیم تا کپی شود
                is_active=row[3],
                created_at=str(row[4])
            )
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.delete("/apikeys/{key_id}", summary="حذف و ابطال کلید API")
async def delete_apikey(key_id: int):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM api_keys WHERE id = %s RETURNING id", (key_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="کلید API یافت نشد.")
            conn.commit()
            return {"status": "success", "message": "API Key revoked successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
