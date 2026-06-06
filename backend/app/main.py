"""
/// <summary>
/// فایل اصلی راه‌اندازی و اجرای وب‌سرور آریونکس (ArioNex Backend Entrypoint)
/// </summary>
/// <remarks>
/// این فایل وب‌سرور FastAPI را پیکربندی کرده، سیستم لاگ‌نویسی و اتصالات پایگاه داده را بالا می‌آورد
/// و تنظیمات CORS را برای اتصال روان فرانت‌اند و ابزارک‌های وب مدیریت می‌کند.
///
/// ساختار روترها (Route Registration):
///   /v1/query       — پرسش RAG مستقیم (REST API)
///   /v1/upload      — آپلود و ایندکس اسناد
///   /v1/config      — مدیریت Feature Toggle‌ها (ادمین)
///   /v1/widget.js   — JavaScript ابزارک وب‌سایت
///   /v1/widget/chat — پردازش پیام ابزارک
/// </remarks>
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.routes import query_router, upload_router, config_router, widget_router, integration_router
from app.services.integrations.telegram_bot import start_telegram_bot_service, stop_telegram_bot_service

# پیکربندی سیستم لاگ‌نویسی متمرکز
setup_logging()
logger = logging.getLogger("arionex.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    /// <summary>
    /// مدیریت وقایع چرخه حیات (Lifespan) وب‌سرور بک‌اند
    /// </summary>
    /// <remarks>
    /// این متد در ابتدای راه‌اندازی سرور، پایگاه داده و اکستنشن‌های مربوطه را آماده‌سازی می‌کند.
    /// همچنین ربات تلگرام سازمانی را به صورت پس‌زمینه اجرا می‌نماید.
    /// </remarks>
    """
    logger.info("ArioNex Enterprise Backend is starting up...")
    logger.info(f"Active LLM Provider: {settings.llm_provider} | Model: {settings.model_name}")
    logger.info(f"Embedding Provider: {settings.embedding_provider} | Model: {settings.embedding_model}")

    # راه‌اندازی اولیه دیتابیس پستگرس و افزونه pgvector
    try:
        init_db()
        logger.info("PostgreSQL + pgvector initialization completed successfully.")
    except Exception as e:
        logger.error(f"Critical error during database initialization on startup: {str(e)}")

    # راه‌اندازی سرویس ربات تلگرام سازمانی
    try:
        await start_telegram_bot_service()
    except Exception as e:
        logger.error(f"Failed to start telegram bot service inside lifespan: {str(e)}")

    # ثبت لیست ماژول‌های فعال برای پیگیری در کنسول لاگ
    active_services = [k for k, v in settings.services.__dict__.items() if v]
    logger.info(f"Active Pipeline Expert Workers (Feature Toggles): {active_services}")

    yield

    # متوقف کردن ایمن ربات تلگرام سازمانی
    try:
        await stop_telegram_bot_service()
    except Exception as e:
        logger.error(f"Failed to stop telegram bot service inside lifespan: {str(e)}")

    logger.info("ArioNex Enterprise Backend is shutting down...")


# ساخت وب‌سرور با عنوان رسمی محصول تجاری
app = FastAPI(
    title="ArioNex Enterprise AI Assistant API",
    description="پلتفرم هوشمند تحلیل داده، اسناد و سیستم پرسش و پاسخ سازمانی آریونکس — Multi-Provider LLM",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# پیکربندی CORS برای اتصال به فرانت‌اند ری‌اکت و ابزارک‌های پاپ‌آپ وب‌سایت‌ها
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در محیط واقعی با دامنه‌های مشخص محدود می‌شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ثبت روترهای مستقل بر اساس موضوع
app.include_router(query_router)
app.include_router(upload_router)
app.include_router(config_router)
app.include_router(widget_router)
app.include_router(integration_router)


@app.get("/health", tags=["System Status"])
async def health_check():
    """
    /// <summary>
    /// اندپوینت بررسی سلامت و وضعیت زنده بودن بک‌اند سیستم
    /// </summary>
    /// <returns>یک دیکشنری شامل وضعیت سیستم، provider فعال و ماژول‌های فعال</returns>
    """
    return {
        "status": "online",
        "service": "ArioNex AI Assistant API",
        "version": "1.1.0",
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.model_name,
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
        },
        "active_features": {
            "unstructured_doc": settings.services.unstructured_document_processor,
            "qna_processor": settings.services.qna_processor,
            "structured_analytics": settings.services.structured_data_analytics,
            "web_search": settings.services.web_search,
            "telegram_bot": settings.integrations.telegram_bot,
            "popup_widget": settings.integrations.popup_widget,
            "pii_redaction": settings.security.pii_redaction,
        },
    }


@app.get("/", tags=["System Status"])
async def root():
    """
    /// <summary>
    /// اندپوینت ریشه برای خوش‌آمدگویی به سرور
    /// </summary>
    """
    return {
        "message": "Welcome to ArioNex Enterprise AI Assistant. API is fully operational.",
        "documentation": "/docs",
        "version": "1.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    # اجرای وب‌سرور لوکال روی پورت ۸۰۰۰
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
