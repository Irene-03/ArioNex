"""
/// <summary>
/// روتر مدیریت پیکربندی آریونکس — GET/POST /v1/config (ArioNex Config Management Router)
/// </summary>
/// <remarks>
/// این ماژول اندپوینت‌های مدیریت زنده Feature Toggle‌ها را تعریف می‌کند.
/// منطق به‌روزرسانی به صورت مستقیم در این فایل قرار دارد — چون ساده و بدون dependency پیچیده است.
///
/// اندپوینت‌ها:
///   GET  /v1/config  — دریافت پیکربندی فعال سیستم
///   POST /v1/config  — به‌روزرسانی زنده Feature Toggle‌ها (ادمین)
/// </remarks>
"""

import logging
import os
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.schemas.config_schemas import ConfigUpdateRequest

logger = logging.getLogger("arionex.config_routes")
router = APIRouter(prefix="/v1", tags=["Config — Feature Toggles"])


def _mask_api_key(key: str) -> str:
    if not key or key.strip() == "" or "your-" in key:
        return ""
    if len(key) <= 12:
        return "********"
    return key[:6] + "..." + key[-4:]


def _update_env_file(key: str, value: str):
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        ".env"
    )
    if not os.path.exists(env_path):
        env_path = "/app/.env"
        if not os.path.exists(env_path):
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

    tmp_path = env_path + ".tmp"
    try:
        lines = []
        key_found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f"\n{key}={value}\n")

        # Atomic write using a temp file and flushing it to disk
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, env_path)
        logger.info(f"Successfully updated environment variable {key} in {env_path}")
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        logger.error(f"Failed to update .env file for {key}: {str(e)}")


@router.get(
    "/config",
    summary="دریافت پیکربندی فعال سیستم",
    description="وضعیت روشن/خاموش تمامی Feature Toggle‌های سرویس‌ها، کانال‌های ادغام و تنظیمات امنیتی را برمی‌گرداند.",
)
async def get_active_configuration():
    """
    /// <summary>
    /// اندپوینت دریافت کانفیگ زنده و وضعیت تمامی Feature Toggle‌ها
    /// </summary>
    """
    return {
        "services": settings.services.__dict__,
        "integrations": settings.integrations.__dict__,
        "security": settings.security.__dict__,
        "providers": settings.providers.__dict__ if hasattr(settings, "providers") else {},
        "llm_provider": settings.llm_provider,
        "model_name": settings.model_name,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "hormouz_embedding_model": settings.hormouz_embedding_model,
        "ollama_model": getattr(settings, "ollama_model", "gemma3:4b"),
        "ollama_base_url": getattr(settings, "ollama_base_url", "http://localhost:11434"),
        "cosine_threshold": getattr(settings, "cosine_threshold", 0.50),
        "telegram_bot_token": settings.telegram_bot_token,
        "api_keys": {
            "openai": _mask_api_key(settings.openai_api_key),
            "openrouter": _mask_api_key(settings.openrouter_api_key),
            "anthropic": _mask_api_key(settings.anthropic_api_key),
            "google": _mask_api_key(settings.google_api_key),
            "deepseek": _mask_api_key(settings.deepseek_api_key),
            "gapgpt": _mask_api_key(settings.gapgpt_api_key),
            "avalai": _mask_api_key(settings.avalai_api_key),
            "hormouz": _mask_api_key(settings.hormouz_api_key),
        }
    }


@router.post(
    "/config",
    summary="به‌روزرسانی زنده Feature Toggle‌ها (ادمین)",
    description="تنظیمات سرویس‌ها، کانال‌ها و امنیت را در زمان اجرا بدون نیاز به restart سرور تغییر می‌دهد.",
)
async def update_active_configuration(update: ConfigUpdateRequest):
    """
    /// <summary>
    /// اندپوینت ادمین پنل جهت تغییر زنده تنظیمات سرویس‌ها و درگاه‌های خروجی
    /// </summary>
    /// <param name="update">درخواست به‌روزرسانی شامل بخش‌هایی که باید تغییر کنند</param>
    """
    try:
        if update.services:
            for k, v in update.services.items():
                if hasattr(settings.services, k):
                    setattr(settings.services, k, bool(v))

        telegram_needs_restart = False
        if update.integrations:
            for k, v in update.integrations.items():
                if hasattr(settings.integrations, k):
                    if k == "telegram_bot" and getattr(settings.integrations, k) != bool(v):
                        telegram_needs_restart = True
                    setattr(settings.integrations, k, bool(v))

        if update.telegram_bot_token is not None:
            if settings.telegram_bot_token != update.telegram_bot_token:
                settings.telegram_bot_token = update.telegram_bot_token
                telegram_needs_restart = True

        if telegram_needs_restart:
            from app.services.integrations.telegram_bot import start_telegram_bot_service, stop_telegram_bot_service
            import asyncio
            async def restart_bot():
                await stop_telegram_bot_service()
                if settings.integrations.telegram_bot:
                    await start_telegram_bot_service()
            asyncio.create_task(restart_bot())

        if update.security:
            for k, v in update.security.items():
                if hasattr(settings.security, k):
                    setattr(settings.security, k, bool(v))

        if update.providers and hasattr(settings, "providers"):
            for k, v in update.providers.items():
                # Ollama: ذخیره در settings به عنوان provider فعال
                if k == "ollama":
                    if bool(v):
                        settings.llm_provider = "ollama"
                        logger.info("LLM provider switched to Ollama (local mode).")
                    else:
                        # Find fallback provider
                        fallback = "openrouter"
                        for p_name in ["openrouter", "openai", "deepseek", "google", "anthropic", "gapgpt", "avalai", "hormouz"]:
                            if getattr(settings.providers, p_name, False):
                                fallback = p_name
                                break
                        settings.llm_provider = fallback
                        logger.info(f"Ollama disabled. LLM provider fell back to: {fallback}")
                elif hasattr(settings.providers, k):
                    setattr(settings.providers, k, bool(v))

        # تنظیمات Ollama — مدل و آدرس سرور
        if update.ollama_model:
            settings.ollama_model = update.ollama_model
            logger.info(f"Ollama model set to: {update.ollama_model}")

        if update.ollama_base_url:
            settings.ollama_base_url = update.ollama_base_url
            logger.info(f"Ollama base URL set to: {update.ollama_base_url}")

        if update.hormouz_embedding_model:
            settings.hormouz_embedding_model = update.hormouz_embedding_model
            _update_env_file("HORMOUZ_EMBEDDING_MODEL", update.hormouz_embedding_model)
            logger.info(f"Hormouz embedding model set to: {update.hormouz_embedding_model}")

        if update.embedding_provider:
            settings.embedding_provider = update.embedding_provider
            _update_env_file("EMBEDDING_PROVIDER", update.embedding_provider)
            logger.info(f"Embedding provider set to: {update.embedding_provider}")

        if update.embedding_model:
            settings.embedding_model = update.embedding_model
            _update_env_file("EMBEDDING_MODEL", update.embedding_model)
            logger.info(f"Embedding model set to: {update.embedding_model}")

        # تغییر provider فعال
        if update.llm_provider:
            settings.llm_provider = update.llm_provider
            logger.info(f"LLM provider switched to: {update.llm_provider}")

        # به‌روزرسانی کلیدهای API پروایدرها
        api_keys_to_update = {
            "openai_api_key": getattr(update, "openai_api_key", None),
            "openrouter_api_key": getattr(update, "openrouter_api_key", None),
            "anthropic_api_key": getattr(update, "anthropic_api_key", None),
            "google_api_key": getattr(update, "google_api_key", None),
            "deepseek_api_key": getattr(update, "deepseek_api_key", None),
            "gapgpt_api_key": getattr(update, "gapgpt_api_key", None),
            "avalai_api_key": getattr(update, "avalai_api_key", None),
            "hormouz_api_key": getattr(update, "hormouz_api_key", None),
        }

        for key_name, key_val in api_keys_to_update.items():
            if key_val is not None:
                # Do not overwrite actual key if incoming value is masked or empty
                if "..." in key_val or "***" in key_val or "********" in key_val or key_val.strip() == "":
                    continue
                setattr(settings, key_name, key_val)
                _update_env_file(key_name.upper(), key_val)

        logger.info("Administrative Feature Toggles updated successfully at runtime.")
        return {
            "status": "success",
            "message": "Configuration updated at runtime.",
            "current_config": {
                "services": settings.services.__dict__,
                "integrations": settings.integrations.__dict__,
                "security": settings.security.__dict__,
                "providers": settings.providers.__dict__ if hasattr(settings, "providers") else {},
                "llm_provider": settings.llm_provider,
                "ollama_model": getattr(settings, "ollama_model", "gemma3:4b"),
                "ollama_base_url": getattr(settings, "ollama_base_url", "http://localhost:11434"),
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
                "hormouz_embedding_model": settings.hormouz_embedding_model,
                "telegram_bot_token": settings.telegram_bot_token,
                "api_keys": {
                    "openai": _mask_api_key(settings.openai_api_key),
                    "openrouter": _mask_api_key(settings.openrouter_api_key),
                    "anthropic": _mask_api_key(settings.anthropic_api_key),
                    "google": _mask_api_key(settings.google_api_key),
                    "deepseek": _mask_api_key(settings.deepseek_api_key),
                    "gapgpt": _mask_api_key(settings.gapgpt_api_key),
                    "avalai": _mask_api_key(settings.avalai_api_key),
                    "hormouz": _mask_api_key(settings.hormouz_api_key),
                }
            },
        }
    except Exception as e:
        logger.error(f"Failed to update runtime configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# System Prompts Management Endpoints
# -------------------------------------------------------------------
from pydantic import BaseModel
from app.core.database import get_db_connection

class PromptUpdateRequest(BaseModel):
    prompt: str


@router.get("/config/prompts", summary="دریافت پرامپت فعال سیستم")
async def get_system_prompt():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT prompt FROM system_prompts WHERE key = 'default_system_instruction'")
            row = cur.fetchone()
            if row:
                return {"prompt": row[0]}
            
            # در صورت عدم وجود، یک مقدار پیش‌فرض برمی‌گردانیم
            default_prompt = (
                "شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. "
                "هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید."
            )
            return {"prompt": default_prompt}
    except Exception as e:
        logger.error(f"Failed to get system prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/config/prompts", summary="بروزرسانی پرامپت فعال سیستم")
async def update_system_prompt(payload: PromptUpdateRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_prompts (key, prompt, updated_at)
                VALUES ('default_system_instruction', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET
                    prompt = EXCLUDED.prompt,
                    updated_at = EXCLUDED.updated_at
                """,
                (payload.prompt,)
            )
            conn.commit()
        return {"status": "success", "message": "System prompt updated successfully.", "prompt": payload.prompt}
    except Exception as e:
        logger.error(f"Failed to update system prompt: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
