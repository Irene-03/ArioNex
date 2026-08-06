"""
/// <summary>
/// ArioNex user authentication and user management router (ArioNex User Authentication Router)
/// </summary>
"""

import hmac
import time
import base64
import json
import hashlib
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.database import get_db_connection

logger = logging.getLogger("arionex.auth_routes")
router = APIRouter(prefix="/v1/auth", tags=["Auth — User Authentication"])

import secrets
from app.core.config import settings

# -------------------------------------------------------------------
# Security settings with a fixed Salt
# -------------------------------------------------------------------

# Uses the fixed Salt from settings - if not set, uses the default value
PASSWORD_SALT = settings.password_salt or "arionex_fixed_salt_2026_secure"
SECRET_KEY = settings.jwt_secret_key or secrets.token_urlsafe(32)

# If we are in a development environment and the key is not set, generate one
if not SECRET_KEY:
    if settings.env == "development":
        SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning(f"Using auto-generated development JWT_SECRET_KEY")
    else:
        raise ValueError("JWT_SECRET_KEY must be set in production environment")

TOKEN_EXPIRY_SECONDS = 86400  # 24 Hours

# -------------------------------------------------------------------
# Security Schemes & Helpers
# -------------------------------------------------------------------

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hashing the password with the PBKDF2 algorithm
    Uses a fixed Salt defined in config.yaml
    """
    salt_to_use = salt or PASSWORD_SALT
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt_to_use.encode('utf-8'),
        100000
    ).hex()

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify password matches the stored hash
    Uses multiple methods for compatibility with legacy hashes
    """
    # 1. Check against the current Salt
    current_hash = hash_password(password, PASSWORD_SALT)
    if current_hash == stored_hash:
        return True
    
    # 2. Check against the old default Salt (for compatibility with previous hashes)
    legacy_salts = [
        "arionex_secure_salt_2026",
        "arionex_default_salt",
        "arionex_salt",
        ""  # No salt
    ]
    
    for legacy_salt in legacy_salts:
        try:
            legacy_hash = hash_password(password, legacy_salt)
            if legacy_hash == stored_hash:
                return True
        except Exception:
            continue
    
    # 3. Check simple SHA256 hash (for compatibility with the oldest versions)
    try:
        simple_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if simple_hash == stored_hash:
            return True
    except Exception:
        pass
    
    return False

def create_session_token(payload: dict, expires_in: int = 86400, token_type: str = "access") -> str:
    """Generate a secure session token using the HMAC-SHA256 algorithm"""
    payload_data = payload.copy()
    payload_data["exp"] = int(time.time()) + expires_in
    payload_data["type"] = token_type
    payload_json = json.dumps(payload_data)
    encoded_payload = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), encoded_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{sig}"

def verify_session_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """Validate the session token and check its expiry and type"""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        encoded_payload, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), encoded_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload_json = base64.urlsafe_b64decode(encoded_payload.encode('utf-8')).decode('utf-8')
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        t_type = payload.get("type", "access")
        if t_type != expected_type:
            return None
        return payload
    except Exception as e:
        logger.debug(f"Token verification failed: {str(e)}")
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> dict:
    """Get the current user from the token sent in the Authorization Bearer header"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن احراز هویت ارسال نشده است."
        )
    token = credentials.credentials
    payload = verify_session_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن احراز هویت نامعتبر یا منقضی شده است."
        )
    return {
        "username": payload.get("username"),
        "role": payload.get("role")
    }

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Access restrictor for admin users only"""
    if user.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="دسترسی به این بخش فقط برای نقش مدیر سیستم (Admin) مجاز است."
        )
    return user

# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="نام کاربری")
    password: str = Field(..., min_length=6, description="رمز عبور")
    role: str = Field("Analyst", description="نقش کاربر: Admin یا Analyst")

class UserSignUp(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="نام کاربری")
    password: str = Field(..., min_length=6, description="رمز عبور")

class UserLogin(BaseModel):
    username: str = Field(..., description="نام کاربری")
    password: str = Field(..., description="رمز عبور")

class UserResponse(BaseModel):
    username: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

# -------------------------------------------------------------------
# Auth Endpoints
# -------------------------------------------------------------------

@router.post("/signup", response_model=UserResponse, summary="ثبتنام عمومی کاربر جدید (نقش تحلیلگر)")
async def signup_user(payload: UserSignUp):
    """
    Register a new user with the Analyst role
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check that the username is not already taken
            cur.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="این نام کاربری قبلاً ثبت شده است.")
            
            pwd_hash = hash_password(payload.password, PASSWORD_SALT)
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'Analyst')
                RETURNING username, role
                """,
                (payload.username, pwd_hash)
            )
            row = cur.fetchone()
            conn.commit()
            logger.info(f"User '{payload.username}' signed up successfully with role Analyst")
            return UserResponse(username=row[0], role=row[1])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to signup user: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/register", response_model=UserResponse, summary="ثبتنام کاربر جدید (فقط ادمین)")
async def register_user(payload: UserRegister, admin: dict = Depends(require_admin)):
    """
    Register a new user with a specified role (admin only)
    """
    if payload.role not in ["Admin", "Analyst"]:
        raise HTTPException(status_code=400, detail="نقش وارد شده نامعتبر است. فقط Admin یا Analyst مجاز است.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check that the username is not already taken
            cur.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="این نام کاربری قبلاً ثبت شده است.")
            
            pwd_hash = hash_password(payload.password, PASSWORD_SALT)
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING username, role
                """,
                (payload.username, pwd_hash, payload.role)
            )
            row = cur.fetchone()
            conn.commit()
            logger.info(f"User '{payload.username}' registered by admin with role {payload.role}")
            return UserResponse(username=row[0], role=row[1])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register user: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/login", response_model=LoginResponse, summary="ورود کاربر به سیستم")
async def login_user(payload: UserLogin):
    """
    Log the user in and return access tokens
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Fetch the user info
            cur.execute("SELECT password_hash, role FROM users WHERE username = %s", (payload.username,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Login failed: User '{payload.username}' not found")
                raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
            
            stored_hash, role = row
            
            # Verify the password using the verify_password function
            if not verify_password(payload.password, stored_hash):
                logger.warning(f"Login failed: Invalid password for user '{payload.username}'")
                raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
            
            # If the hash is legacy, upgrade it to the new hash with the current Salt
            if hash_password(payload.password, PASSWORD_SALT) != stored_hash:
                new_hash = hash_password(payload.password, PASSWORD_SALT)
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (new_hash, payload.username)
                )
                conn.commit()
                logger.info(f"Password hash upgraded for user '{payload.username}'")
            
            # Generate session tokens
            access_token = create_session_token(
                {"username": payload.username, "role": role}, 
                expires_in=7200,  # 2 hours
                token_type="access"
            )
            refresh_token = create_session_token(
                {"username": payload.username, "role": role}, 
                expires_in=604800,  # 7 days
                token_type="refresh"
            )
            
            logger.info(f"User '{payload.username}' logged in successfully")
            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                user=UserResponse(username=payload.username, role=role)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to login user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/refresh", response_model=TokenRefreshResponse, summary="نوسازی توکن دسترسی منقضی شده")
async def refresh_token(payload: TokenRefreshRequest):
    """
    Refresh the access token using a valid refresh token
    """
    token_payload = verify_session_token(payload.refresh_token, expected_type="refresh")
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن بازنشانی نامعتبر یا منقضی شده است. لطفاً مجدداً وارد شوید."
        )
    
    username = token_payload.get("username")
    role = token_payload.get("role")
    
    # Generate new tokens
    new_access_token = create_session_token(
        {"username": username, "role": role}, 
        expires_in=7200, 
        token_type="access"
    )
    new_refresh_token = create_session_token(
        {"username": username, "role": role}, 
        expires_in=604800, 
        token_type="refresh"
    )
    
    logger.info(f"Tokens refreshed for user '{username}'")
    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )

@router.get("/users", response_model=List[UserResponse], summary="لیست کل کاربران (فقط ادمین)")
async def list_users(admin: dict = Depends(require_admin)):
    """
    Get the list of all system users (admin only)
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT username, role FROM users ORDER BY id DESC")
            rows = cur.fetchall()
            return [UserResponse(username=row[0], role=row[1]) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.delete("/users/{username}", summary="حذف کاربر (فقط ادمین)")
async def delete_user(username: str, admin: dict = Depends(require_admin)):
    """
    Delete a user from the system (admin only)
    """
    if username == admin.get("username"):
        raise HTTPException(status_code=400, detail="نمیتوانید خودتان را حذف کنید.")
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s RETURNING id", (username,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد.")
            conn.commit()
            logger.info(f"User '{username}' deleted by admin '{admin.get('username')}'")
            return {"message": f"User '{username}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
