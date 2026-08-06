"""
/// <summary>
/// ArioNex Configuration Schemas (ArioNex Configuration Schemas)
/// </summary>
/// <remarks>
/// This module defines the data structures for live system configuration change requests.
/// Admins change Feature Toggles through the POST /v1/config endpoint using this schema.
///
/// All fields are Optional — only the sections that should change are sent.
/// </remarks>
"""

from typing import Optional
from pydantic import BaseModel, Field


class ConfigUpdateRequest(BaseModel):
    """
    /// <summary>
    /// Request model for the live update of service, integration, and security configuration
    /// </summary>
    /// <remarks>
    /// Each field is a dict of feature name → boolean value.
    /// Example: {"services": {"web_search": true, "qna_processor": false}}
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
    # Ollama settings (offline local mode)
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
    hormouz_embedding_model: Optional[str] = Field(
        default=None,
        description="مدل Embedding برای Hormouz — مثال: openai/text-embedding-3-large"
    )
    embedding_provider: Optional[str] = Field(
        default=None,
        description="تغییر پروایدر امبدینگ فعال — مثال: openai, google, hormouz, openrouter"
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="تغییر مدل امبدینگ فعال"
    )
