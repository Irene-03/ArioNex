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
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.schemas.config_schemas import ConfigUpdateRequest

logger = logging.getLogger("arionex.config_routes")
router = APIRouter(prefix="/v1", tags=["Config — Feature Toggles"])


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

        if update.integrations:
            for k, v in update.integrations.items():
                if hasattr(settings.integrations, k):
                    setattr(settings.integrations, k, bool(v))

        if update.security:
            for k, v in update.security.items():
                if hasattr(settings.security, k):
                    setattr(settings.security, k, bool(v))

        if update.providers and hasattr(settings, "providers"):
            for k, v in update.providers.items():
                # Ollama: ذخیره در settings به عنوان provider فعال
                if k == "ollama" and bool(v):
                    settings.llm_provider = "ollama"
                    logger.info("LLM provider switched to Ollama (local mode).")
                elif hasattr(settings.providers, k):
                    setattr(settings.providers, k, bool(v))

        # تنظیمات Ollama — مدل و آدرس سرور
        if update.ollama_model:
            settings.ollama_model = update.ollama_model
            logger.info(f"Ollama model set to: {update.ollama_model}")

        if update.ollama_base_url:
            settings.ollama_base_url = update.ollama_base_url
            logger.info(f"Ollama base URL set to: {update.ollama_base_url}")

        # تغییر provider فعال
        if update.llm_provider:
            settings.llm_provider = update.llm_provider
            logger.info(f"LLM provider switched to: {update.llm_provider}")

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
            },
        }
    except Exception as e:
        logger.error(f"Failed to update runtime configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
