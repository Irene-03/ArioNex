"""
/// <summary>
/// روتر مدیریت احراز هویت و کاربران آریونکس (ArioNex User Authentication Router)
/// </summary>
/// <remarks>
/// این ماژول عملیات ثبت‌نام، ورود کاربران، تولید توکن‌های نشست ایمن (HMAC-SHA256)
/// و کنترل نقش‌های کاربری (Admin/Analyst) را مدیریت می‌کند.
/// </remarks>
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

SECRET_KEY = "arionex_secure_jwt_alternative_secret_key_2026"
TOKEN_EXPIRY_SECONDS = 86400  # 24 Hours

# -------------------------------------------------------------------
# Security Schemes & Helpers
# -------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """هش کردن رمز عبور با الگوریتم SHA-256 و نمک ثابت"""
    salt = "arionex_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def create_session_token(payload: dict, expires_in: int = 86400, token_type: str = "access") -> str:
    """تولید توکن نشست ایمن با الگوریتم HMAC-SHA256"""
    payload_data = payload.copy()
    payload_data["exp"] = int(time.time()) + expires_in
    payload_data["type"] = token_type
    payload_json = json.dumps(payload_data)
    encoded_payload = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), encoded_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{sig}"

def verify_session_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """اعتبارسنجی توکن نشست و بررسی انقضا و نوع توکن"""
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
        # برای توکن‌های قدیمی فیلد type وجود ندارد، بنابراین پیش‌فرض را access در نظر می‌گیریم
        t_type = payload.get("type", "access")
        if t_type != expected_type:
            return None
        return payload
    except Exception:
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> dict:
    """دریافت کاربر جاری از روی توکن ارسالی در هدر Authorization Bearer"""
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
    """محدودکننده دسترسی فقط برای کاربران ادمین"""
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
    token_type: str
    user: UserResponse

# -------------------------------------------------------------------
# Auth Endpoints
# -------------------------------------------------------------------
@router.post("/signup", response_model=UserResponse, summary="ثبت‌نام عمومی کاربر جدید (نقش تحلیل‌گر)")
async def signup_user(payload: UserSignUp):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # بررسی تکراری نبودن نام کاربری
            cur.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="این نام کاربری قبلاً ثبت شده است.")
            
            pwd_hash = hash_password(payload.password)
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

@router.post("/register", response_model=UserResponse, summary="ثبت‌نام کاربر جدید (فقط ادمین)")
async def register_user(payload: UserRegister, admin: dict = Depends(require_admin)):
    if payload.role not in ["Admin", "Analyst"]:
        raise HTTPException(status_code=400, detail="نقش وارد شده نامعتبر است. فقط Admin یا Analyst مجاز است.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # بررسی تکراری نبودن نام کاربری
            cur.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="این نام کاربری قبلاً ثبت شده است.")
            
            pwd_hash = hash_password(payload.password)
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
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash, role FROM users WHERE username = %s", (payload.username,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
            
            pwd_hash, role = row
            if hash_password(payload.password) != pwd_hash:
                raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
            
            # تولید توکن نشست
            token = create_session_token({"username": payload.username, "role": role})
            return LoginResponse(
                access_token=token,
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

@router.get("/users", response_model=List[UserResponse], summary="لیست کل کاربران (فقط ادمین)")
async def list_users(admin: dict = Depends(require_admin)):
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
