"""
/// <summary>
/// مدل‌های Pydantic مدیریت پیکربندی سیستم (ArioNex Configuration Schemas)
/// </summary>
/// <remarks>
/// این ماژول ساختار داده‌ای درخواست‌های تغییر پیکربندی زنده سیستم را تعریف می‌کند.
/// ادمین از طریق اندپوینت POST /v1/config با استفاده از این schema، Feature Toggle‌ها را تغییر می‌دهد.
///
/// تمامی فیلدها Optional هستند — فقط بخش‌هایی که باید تغییر کنند ارسال می‌شوند.
/// </remarks>
"""

from typing import Optional
from pydantic import BaseModel, Field


class ConfigUpdateRequest(BaseModel):
    """
    /// <summary>
    /// مدل درخواست به‌روزرسانی زنده پیکربندی سرویس‌ها، ادغام‌ها و امنیت سیستم
    /// </summary>
    /// <remarks>
    /// هر فیلد یک دیکشنری از نام ویژگی → مقدار boolean است.
    /// مثال: {"services": {"web_search": true, "qna_processor": false}}
    /// </remarks>
    """
    services: Optional[dict] = Field(
        default=None,
        description="تنظیمات Feature Toggle سرویس‌های پردازشی — کلید: نام سرویس، مقدار: bool"
    )
    integrations: Optional[dict] = Field(
        default=None,
        description="تنظیمات روشن/خاموش بودن کانال‌های ارتباطی — Telegram, Widget, REST API"
    )
    security: Optional[dict] = Field(
        default=None,
        description="تنظیمات امنیتی — PII Redaction، Non-Hallucination و..."
    )
    providers: Optional[dict] = Field(
        default=None,
        description="تنظیمات روشن/خاموش بودن پروایدرهای هوش مصنوعی"
    )
    # تنظیمات Ollama (حالت محلی آفلاین)
    ollama_model: Optional[str] = Field(
        default=None,
        description="نام مدل محلی Ollama — مثال: gemma3:4b, llama3.2:3b"
    )
    ollama_base_url: Optional[str] = Field(
        default=None,
        description="آدرس سرور Ollama — پیش‌فرض: http://localhost:11434"
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="تغییر provider فعال در زمان اجرا — مثال: ollama, openrouter, openai"
    )
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="توکن ربات تلگرام جهت فعال‌سازی ربات تلگرام"
    )
    openai_api_key: Optional[str] = Field(default=None, description="کلید API برای OpenAI")
    openrouter_api_key: Optional[str] = Field(default=None, description="کلید API برای OpenRouter")
    anthropic_api_key: Optional[str] = Field(default=None, description="کلید API برای Anthropic Claude")
    google_api_key: Optional[str] = Field(default=None, description="کلید API برای Google Gemini")
    deepseek_api_key: Optional[str] = Field(default=None, description="کلید API برای DeepSeek")
    gapgpt_api_key: Optional[str] = Field(default=None, description="کلید API برای GapGPT")
    avalai_api_key: Optional[str] = Field(default=None, description="کلید API برای AvalAI")
    hormouz_api_key: Optional[str] = Field(default=None, description="کلید API برای Hormouz")
