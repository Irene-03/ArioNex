"""
/// <summary>
/// ArioNex Audit Log Router
/// </summary>
/// <remarks>
/// This module exposes the admin audit log page backed by the pg_audit_logs table.
///
/// Endpoints:
///   GET /v1/audit/logs — paginated audit log entries (admin only)
/// </remarks>
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_db_connection
from app.routes.auth_routes import require_admin

logger = logging.getLogger("arionex.audit_routes")
router = APIRouter(prefix="/v1", tags=["Audit Logs"])


# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------
class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    user_name: str
    user_role: str
    query_text: str
    status: str
    pii_masked_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    response_time_ms: int = 0


class AuditLogsResponse(BaseModel):
    total: int
    items: List[AuditLogEntry]


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@router.get(
    "/audit/logs",
    response_model=AuditLogsResponse,
    summary="لاگ حسابرسی پرسش‌ها (فقط مدیر سیستم)",
)
async def audit_logs(
    limit: int = Query(20, ge=1, le=100, description="تعداد رکوردها"),
    offset: int = Query(0, ge=0, description="نقطه شروع"),
    user_filter: Optional[str] = Query(None, alias="user", description="فیلتر نام کاربر"),
    status_filter: Optional[str] = Query(None, alias="status", description="فیلتر وضعیت"),
    admin: dict = Depends(require_admin),
):
    """Paginated, filterable audit log entries. Admin role required."""
    conn = None
    try:
        conn = get_db_connection()
        where_sql = ""
        params: List = []
        if user_filter:
            where_sql += " WHERE user_name ILIKE %s"
            params.append(f"%{user_filter}%")
        if status_filter:
            where_sql += (" AND " if where_sql else " WHERE ") + " status = %s"
            params.append(status_filter)

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM pg_audit_logs{where_sql}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, timestamp, user_name, user_role, query_text, status,
                       pii_masked_count, total_tokens, input_tokens, output_tokens, response_time_ms
                FROM pg_audit_logs{where_sql}
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()

        items = [
            {
                "id": r[0],
                "timestamp": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "user_name": r[2],
                "user_role": r[3],
                "query_text": r[4],
                "status": r[5],
                "pii_masked_count": int(r[6] or 0),
                "total_tokens": int(r[7] or 0),
                "input_tokens": int(r[8] or 0),
                "output_tokens": int(r[9] or 0),
                "response_time_ms": int(r[10] or 0),
            }
            for r in rows
        ]
        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
