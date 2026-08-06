"""
/// <summary>
/// Helper for verifying and validating API access keys (ArioNex API Key Verification Helper)
/// </summary>
/// <remarks>
/// This module provides the method for verifying the validity of headers sent in external (REST API) requests.
/// Accepted headers: x-api-key or Authorization: Bearer.
/// </remarks>
"""

import logging
from typing import Optional
from fastapi import Header, Security, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db_connection

logger = logging.getLogger("arionex.auth")

# Defining structures for extracting the key from headers
api_key_header_scheme = APIKeyHeader(name="x-api-key", auto_error=False)
api_key_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header_scheme),
    api_key_bearer: Optional[HTTPAuthorizationCredentials] = Security(api_key_bearer_scheme),
) -> Optional[str]:
    """
    /// <summary>
    /// Verifies and validates the API key sent by external clients
    /// </summary>
    /// <param name="api_key_header">Key read from the x-api-key header</param>
    /// <param name="api_key_bearer">Key read from the Authorization Bearer header</param>
    /// <returns>Access key name if valid</returns>
    /// <exception cref="HTTPException">If the key is invalid or inactive</exception>
    """
    # Extract the final key from one of the two allowed methods
    token = api_key_header or (api_key_bearer.credentials if api_key_bearer else None)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check the total number of keys in the system. If no key is defined,
            # authentication is disabled for backward compatibility and development convenience.
            cur.execute("SELECT COUNT(*) FROM api_keys")
            count = cur.fetchone()[0]
            
            if count == 0:
                # The system has no registered keys; access is unrestricted
                return "development_bypass"
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="برای استفاده از این بخش نیاز به ارسال کلید دسترسی در هدر x-api-key یا Authorization دارید."
                )

            # 1. Look up using hashed token
            import hashlib
            hashed_token = hashlib.sha256(token.encode("utf-8")).hexdigest()
            cur.execute(
                "SELECT id, name, is_active FROM api_keys WHERE api_key = %s",
                (hashed_token,)
            )
            row = cur.fetchone()
            
            # 2. Backward compatibility fallback for legacy plaintext keys
            if not row:
                cur.execute(
                    "SELECT id, name, is_active FROM api_keys WHERE api_key = %s",
                    (token,)
                )
                row = cur.fetchone()
                if row:
                    # Auto-migrate legacy key to SHA-256 hash
                    legacy_id = row[0]
                    logger.info(f"Auto-migrating legacy API key ID {legacy_id} to SHA-256 hash.")
                    cur.execute(
                        "UPDATE api_keys SET api_key = %s WHERE id = %s",
                        (hashed_token, legacy_id)
                    )
                    conn.commit()
            
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
            
            # Update the last-used time in the background
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


async def get_current_user_or_api_key(
    api_key_header: Optional[str] = Security(api_key_header_scheme),
    api_key_bearer: Optional[HTTPAuthorizationCredentials] = Security(api_key_bearer_scheme),
) -> dict:
    """
    /// <summary>
    /// Validates the request header and retrieves the user identity or API key name
    /// </summary>
    """
    token = api_key_header or (api_key_bearer.credentials if api_key_bearer else None)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check the number of users and keys
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM api_keys")
            key_count = cur.fetchone()[0]
            
            # If neither a user nor a key is registered, trial access is open (backward compatibility for tests)
            if user_count == 0 and key_count == 0 and not token:
                return {"username": "development_bypass", "role": "Admin"}
                
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="توکن احراز هویت یا کلید API ارسال نشده است."
                )
                
            # First, check whether the token is a user session token (by inspecting the Authorization Bearer header)
            from app.routes.auth_routes import verify_session_token
            user_payload = verify_session_token(token)
            if user_payload:
                return {
                    "username": user_payload.get("username"),
                    "role": user_payload.get("role")
                }
                
            # If it is not a session token, check whether the API key is valid
            import hashlib
            hashed_token = hashlib.sha256(token.encode("utf-8")).hexdigest()
            cur.execute(
                "SELECT id, name, is_active FROM api_keys WHERE api_key = %s",
                (hashed_token,)
            )
            row = cur.fetchone()
            
            # Backward compatibility fallback for legacy plaintext keys
            if not row:
                cur.execute(
                    "SELECT id, name, is_active FROM api_keys WHERE api_key = %s",
                    (token,)
                )
                row = cur.fetchone()
                if row:
                    # Auto-migrate legacy key to SHA-256 hash
                    legacy_id = row[0]
                    logger.info(f"Auto-migrating legacy API key ID {legacy_id} to SHA-256 hash.")
                    cur.execute(
                        "UPDATE api_keys SET api_key = %s WHERE id = %s",
                        (hashed_token, legacy_id)
                    )
                    conn.commit()
            if row:
                key_id, name, is_active = row
                if not is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="این کلید API غیرفعال شده است."
                    )
                # Update the last-used time
                cur.execute(
                    "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (key_id,)
                )
                conn.commit()
                return {"username": name, "role": "Admin"}
                
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="توکن احراز هویت یا کلید API نامعتبر است."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unified auth: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در سیستم احراز هویت."
        )
    finally:
        if conn:
            conn.close()
