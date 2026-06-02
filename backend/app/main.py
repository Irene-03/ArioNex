"""
/// <summary>
/// فایل اصلی راه‌اندازی و اجرای وب‌سرور آریونکس (ArioNex Backend Entrypoint)
/// </summary>
/// <remarks>
/// این فایل وب‌سرور FastAPI را پیکربندی کرده، سیستم لاگ‌نویسی و اتصالات پایگاه داده را بالا می‌آورد
/// و تنظیمات CORS را برای اتصال روان فرانت‌اند مدیریت می‌کند.
/// </remarks>
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.api.endpoints import router as api_router
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
    description="پلتفرم هوشمند تحلیل داده، اسناد و سیستم پرسش و پاسخ سازمانی آریونکس",
    version="1.0.0",
    lifespan=lifespan
)

# پیکربندی CORS برای اتصال به فرانت‌اند ری‌اکت و ابزارک‌های پاپ‌آپ وب‌سایت‌ها
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در محیط واقعی با دامنه‌های مشخص محدود می‌شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# اتصال اندپوینت‌های رسمی وب‌سرویس آریونکس
app.include_router(api_router)

@app.get("/health", tags=["System Status"])
async def health_check():
    """
    /// <summary>
    /// اندپوینت بررسی سلامت و وضعیت زنده بودن بک‌اند سیستم
    /// </summary>
    /// <returns>یک دیکشنری شامل وضعیت سیستم و ماژول‌های فعال</returns>
    """
    return {
        "status": "online",
        "service": "ArioNex AI Assistant API",
        "version": "1.0.0",
        "active_features": {
            "unstructured_doc": settings.services.unstructured_document_processor,
            "qna_processor": settings.services.qna_processor,
            "structured_analytics": settings.services.structured_data_analytics,
            "web_search": settings.services.web_search,
            "telegram_bot": settings.integrations.telegram_bot,
            "popup_widget": settings.integrations.popup_widget,
            "pii_redaction": settings.security.pii_redaction
        }
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
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # اجرای وب‌سرور لوکال روی پورت ۸۰۰۰
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
