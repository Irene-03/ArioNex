"""
/// <summary>
/// هبر انطباق و اعتبارسنجی کلیدهای دسترسی API (ArioNex API Key Verification Helper)
/// </summary>
/// <remarks>
/// این ماژول متد بررسی صحت هدرهای ارسالی درخواست‌های بیرونی (REST API) را بر عهده دارد.
/// هدرهای مورد پذیرش: x-api-key یا Authorization: Bearer.
/// </remarks>
"""

import logging
from typing import Optional
from fastapi import Header, Security, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db_connection

logger = logging.getLogger("arionex.auth")

# تعریف ساختارهای دریافت کلید از هدر
api_key_header_scheme = APIKeyHeader(name="x-api-key", auto_error=False)
api_key_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header_scheme),
    api_key_bearer: Optional[HTTPAuthorizationCredentials] = Security(api_key_bearer_scheme),
) -> Optional[str]:
    """
    /// <summary>
    /// بررسی و اعتبارسنجی کلید API ارسالی از طرف کلاینت‌های خارجی
    /// </summary>
    /// <param name="api_key_header">کلید خوانده شده از هدر x-api-key</param>
    /// <param name="api_key_bearer">کلید خوانده شده از هدر Authorization Bearer</param>
    /// <returns>نام کلید دسترسی در صورت معتبر بودن</returns>
    /// <exception cref="HTTPException">در صورت نامعتبر بودن یا فعال نبودن کلید</exception>
    """
    # استخراج کلید نهایی از یکی از دو روش مجاز
    token = api_key_header or (api_key_bearer.credentials if api_key_bearer else None)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # بررسی تعداد کل کلیدها در سیستم. اگر هیچ کلیدی تعریف نشده باشد،
            # برای سازگاری عقب‌رو و راحتی توسعه، احراز هویت را غیرفعال می‌کنیم.
            cur.execute("SELECT COUNT(*) FROM api_keys")
            count = cur.fetchone()[0]
            
            if count == 0:
                # سیستم کلید ثبت‌شده‌ای ندارد؛ دسترسی آزاد است
                return "development_bypass"
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="برای استفاده از این بخش نیاز به ارسال کلید دسترسی در هدر x-api-key یا Authorization دارید."
                )

            # بررسی وجود و فعال بودن کلید
            cur.execute(
                "SELECT id, name, is_active FROM api_keys WHERE api_key = %s",
                (token,)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="کلید API ارسالی نامعتبر است."
                )
            
            key_id, name, is_active = row
            
            if not is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="این کلید API غیرفعال شده است."
                )
            
            # به‌روزرسانی زمان آخرین استفاده به صورت پس‌زمینه
            cur.execute(
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s",
                (key_id,)
            )
            conn.commit()
            
            return name
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during API Key verification: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در بررسی اعتبار کلید API."
        )
    finally:
        if conn:
            conn.close()
