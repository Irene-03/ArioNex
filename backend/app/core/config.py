"""
/// <summary>
/// فایل مدیریت پیکربندی و تنظیمات هوشمند سیستم آریونکس (ArioNex Configuration Manager)
/// </summary>
/// <remarks>
/// این ماژول وظیفه لود کردن و اعتبارسنجی تنظیمات سیستم از فایل config.yaml (فیچر تاگل‌ها)
/// و متغیرهای محیطی سیستم (.env) با استفاده از Pydantic را بر عهده دارد.
/// </remarks>
"""

import os
import yaml
import logging
from typing import Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# لود کردن فایل env محلی
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

logger = logging.getLogger("arionex.config")

class ServiceToggles(BaseSettings):
    """
    /// <summary>
    /// مدل وضعیت فعال یا غیرفعال بودن سرویس‌های بک‌اند
    /// </summary>
    """
    unstructured_document_processor: bool = True
    qna_processor: bool = True
    log_processor: bool = True
    structured_data_analytics: bool = True
    web_search: bool = True
    web_crawler: bool = True
    entity_extractor: bool = False
    rule_extractor: bool = False
    neo4j: bool = False
    safety_auditor: bool = False

class ProviderToggles(BaseSettings):
    """
    /// <summary>
    /// مدل وضعیت فعال یا غیرفعال بودن پروایدرهای مدل‌های زبانی
    /// </summary>
    """
    openai: bool = True
    openrouter: bool = True
    anthropic: bool = True
    google: bool = True
    deepseek: bool = True
    gapgpt: bool = True
    avalai: bool = True
    hormouz: bool = True

class IntegrationToggles(BaseSettings):
    """
    /// <summary>
    /// مدل وضعیت فعال یا غیرفعال بودن کانال‌های ارتباطی (ادغام‌ها)
    /// </summary>
    """
    telegram_bot: bool = True
    popup_widget: bool = True
    rest_api: bool = True

class CrawlerSettings(BaseSettings):
    """
    /// <summary>
    /// تنظیمات رفتاری موتور کرالر وب آریونکس
    /// </summary>
    /// <remarks>
    /// این کلاس تنظیمات قابل‌تنظیم کرالر را نگه می‌دارد:
    ///   - js_render: آیا صفحات JavaScript-rendered (React/Vue) رندر شوند؟
    ///   - follow_external_domains: آیا لینک‌های خارجی (خارج از دامنه اصلی) دنبال شوند؟
    ///   - default_max_pages: حداکثر صفحات پیش‌فرض برای هر job
    ///   - default_max_depth: حداکثر عمق پیش‌فرض برای هر job
    ///   - request_delay_ms: تاخیر بین هر درخواست HTTP (میلی‌ثانیه)
    /// </remarks>
    """
    js_render: bool = False
    follow_external_domains: bool = False
    default_max_pages: int = 50
    default_max_depth: int = 3
    default_concurrency: int = 5
    request_delay_ms: int = 300
    proxy_pool: list[str] = []
    job_timeout_seconds: int = 3600

class SecuritySettings(BaseSettings):
    """
    /// <summary>
    /// تنظیمات امنیتی RAG و ماسک حریم خصوصی
    /// </summary>
    """
    pii_redaction: bool = True
    strict_non_hallucination: bool = True

class Settings(BaseSettings):
    """
    /// <summary>
    /// کلاس اصلی نگهداری تمامی پیکربندی‌های فعال سیستم آریونکس
    /// </summary>
    /// <remarks>
    /// پشتیبانی از چندین LLM provider: openrouter (پیشنهادی)، openai، anthropic، google، deepseek
    /// provider پیش‌فرض از env LLM_PROVIDER خوانده می‌شود و در صورت عدم تنظیم openrouter استفاده می‌شود.
    /// </remarks>
    """
    # -------------------------------------------------------
    # تنظیمات LLM Provider — چندگانه و قابل‌تعویض
    # -------------------------------------------------------
    llm_provider: str = Field(default="openrouter", validation_alias="LLM_PROVIDER")
    model_name: str = Field(default="openai/gpt-4o-mini", validation_alias="MODEL_NAME")

    # کلیدهای API هر provider
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", validation_alias="GOOGLE_API_KEY")
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    gapgpt_api_key: str = Field(default="", validation_alias="GAPGPT_API_KEY")
    avalai_api_key: str = Field(default="", validation_alias="AVALAI_API_KEY")
    hormouz_api_key: str = Field(default="", validation_alias="HORMOUZ_API_KEY")

    # -------------------------------------------------------
    # تنظیمات Embedding Provider — مستقل از Chat LLM
    # -------------------------------------------------------
    embedding_provider: str = Field(default="openai", validation_alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-large", validation_alias="EMBEDDING_MODEL")

    # -------------------------------------------------------
    # تنظیمات سایر سرویس‌ها
    # -------------------------------------------------------
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="postgres", validation_alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: str = Field(default="5432", validation_alias="POSTGRES_PORT")
    
    minio_root_user: str = Field(default="admin", validation_alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(default="admin123", validation_alias="MINIO_ROOT_PASSWORD")
    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_bucket_name: str = Field(default="arionex-raw-files", validation_alias="MINIO_BUCKET_NAME")
    
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    
    # Security, Environment, and CORS Settings
    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    password_salt: str = Field(default="", validation_alias="PASSWORD_SALT")
    env: str = Field(default="development", validation_alias="ENV")
    cors_allowed_origins: str = Field(default="", validation_alias="CORS_ALLOWED_ORIGINS")
    
    # تنظیمات داینامیک لود شده از config.yaml
    services: ServiceToggles = ServiceToggles()
    providers: ProviderToggles = ProviderToggles()
    integrations: IntegrationToggles = IntegrationToggles()
    security: SecuritySettings = SecuritySettings()
    crawler: CrawlerSettings = CrawlerSettings()

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

def load_settings() -> Settings:
    """
    /// <summary>
    /// متد کمکی برای خواندن همزمان فایل yaml و متغیرهای محیطی و تولید آبجکت تنظیمات واحد
    /// </summary>
    /// <returns>یک نمونه معتبر از کلاس Settings</returns>
    """
    # ابتدا تنظیمات پیش‌فرض را لود می‌کنیم
    settings_obj = Settings()
    
    # پیدا کردن مسیر فایل config.yaml
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                
            if yaml_data:
                # ادغام تنظیمات سرویس‌ها
                if "services" in yaml_data:
                    services_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["services"].items()
                    }
                    settings_obj.services = ServiceToggles(**services_data)

                # ادغام تنظیمات پروایدرها
                if "providers" in yaml_data:
                    providers_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["providers"].items()
                    }
                    settings_obj.providers = ProviderToggles(**providers_data)
                
                # ادغام تنظیمات کانال‌های خروجی
                if "integrations" in yaml_data:
                    integrations_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["integrations"].items()
                    }
                    settings_obj.integrations = IntegrationToggles(**integrations_data)
                    
                # ادغام تنظیمات ایمنی و حریم خصوصی
                if "security" in yaml_data:
                    security_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["security"].items()
                    }
                    settings_obj.security = SecuritySettings(**security_data)

                # ادغام تنظیمات موتور کرالر وب
                if "crawler" in yaml_data:
                    crawler_raw = yaml_data["crawler"]
                    crawler_data = {}
                    for k, v in crawler_raw.items():
                        if isinstance(v, dict):
                            # پشتیبانی از فرمت {enabled: true} یا {value: 300}
                            crawler_data[k] = v.get("value", v.get("enabled", True))
                        else:
                            crawler_data[k] = v
                    settings_obj.crawler = CrawlerSettings(**crawler_data)
                    
            logger.info("Successfully loaded dynamic feature toggles from config.yaml")
        except Exception as e:
            logger.error(f"Failed to parse config.yaml, using defaults. Error: {str(e)}")
    else:
        logger.warning("config.yaml not found at root, using default feature toggles.")

        
    return settings_obj

# آبجکت تنظیمات سراسری برنامه جهت استفاده در تمام ماژول‌ها
settings = load_settings()
