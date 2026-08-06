"""
/// <summary>
/// ArioNex smart configuration and settings management file (ArioNex Configuration Manager)
/// </summary>
/// <remarks>
/// This module is responsible for loading and validating system settings from the config.yaml file (feature toggles)
/// and system environment variables (.env) using Pydantic.
/// </remarks>
"""

import os
import yaml
import logging
from typing import Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load the local env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

logger = logging.getLogger("arionex.config")

class ServiceToggles(BaseSettings):
    """
    /// <summary>
    /// Model representing whether backend services are enabled or disabled
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
    unlimited_ocr: bool = False
    check_structure: bool = False
    check_categories: bool = False
    greeting: bool = False
    customization: bool = False


class ProviderToggles(BaseSettings):
    """
    /// <summary>
    /// Model representing whether language model providers are enabled or disabled
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
    ollama: bool = True

class IntegrationToggles(BaseSettings):
    """
    /// <summary>
    /// Model representing whether communication channels (integrations) are enabled or disabled
    /// </summary>
    """
    telegram_bot: bool = True
    popup_widget: bool = True
    rest_api: bool = True

class CrawlerSettings(BaseSettings):
    """
    /// <summary>
    /// Behavioral settings of the ArioNex web crawler engine
    /// </summary>
    /// <remarks>
    /// This class holds the configurable crawler settings:
    ///   - js_render: Should JavaScript-rendered pages (React/Vue) be rendered?
    ///   - follow_external_domains: Should external links (outside the main domain) be followed?
    ///   - default_max_pages: Default maximum pages for each job
    ///   - default_max_depth: Default maximum depth for each job
    ///   - request_delay_ms: Delay between each HTTP request (milliseconds)
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
    /// RAG security settings and privacy masking
    /// </summary>
    """
    pii_redaction: bool = True
    strict_non_hallucination: bool = False

class Settings(BaseSettings):
    """
    /// <summary>
    /// Main class holding all active configurations of the ArioNex system
    /// </summary>
    /// <remarks>
    /// Supports multiple LLM providers: openrouter (recommended), openai, anthropic, google, deepseek
    /// The default provider is read from the LLM_PROVIDER env and openrouter is used if it is not set.
    /// </remarks>
    """
    # -------------------------------------------------------
    # LLM Provider Settings — multiple and interchangeable
    # -------------------------------------------------------
    llm_provider: str = Field(default="openrouter", validation_alias="LLM_PROVIDER")
    model_name: str = Field(default="openai/gpt-4o-mini", validation_alias="MODEL_NAME")

    # API keys for each provider
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", validation_alias="GOOGLE_API_KEY")
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    gapgpt_api_key: str = Field(default="", validation_alias="GAPGPT_API_KEY")
    avalai_api_key: str = Field(default="", validation_alias="AVALAI_API_KEY")
    hormouz_api_key: str = Field(default="", validation_alias="HORMOUZ_API_KEY")

    # -------------------------------------------------------
    # Embedding Provider Settings — independent of the Chat LLM
    # -------------------------------------------------------
    embedding_provider: str = Field(default="openai", validation_alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-large", validation_alias="EMBEDDING_MODEL")
    hormouz_embedding_model: str = Field(default="openai/text-embedding-3-large", validation_alias="HORMOUZ_EMBEDDING_MODEL")

    # -------------------------------------------------------
    # Local Ollama server settings
    # -------------------------------------------------------
    ollama_model: str = Field(default="gemma3:4b", validation_alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")

    # -------------------------------------------------------
    # Unlimited-OCR settings (baidu/Unlimited-OCR via vLLM/SGLang)
    # -------------------------------------------------------
    unlimited_ocr_base_url: str = Field(default="http://localhost:8000", validation_alias="UNLIMITED_OCR_BASE_URL")
    unlimited_ocr_model: str = Field(default="baidu/Unlimited-OCR", validation_alias="UNLIMITED_OCR_MODEL")
    unlimited_ocr_image_mode: str = Field(default="gundam", validation_alias="UNLIMITED_OCR_IMAGE_MODE")

    # -------------------------------------------------------
    # Settings for other services
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
    jwt_secret_key: str = Field(default="arionex_jwt_secret_2026_secure", validation_alias="JWT_SECRET_KEY")
    password_salt: str = Field(default="arionex_fixed_salt_2026_secure", validation_alias="PASSWORD_SALT")
    env: str = Field(default="development", validation_alias="ENV")
    cors_allowed_origins: str = Field(default="", validation_alias="CORS_ALLOWED_ORIGINS")
    
    # Dynamic settings loaded from config.yaml
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
    /// Helper method for simultaneously reading the yaml file and environment variables and producing a unified settings object
    /// </summary>
    /// <returns>A valid instance of the Settings class</returns>
    """
    # First, load the default settings
    settings_obj = Settings()
    
    # Find the path of the config.yaml file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                
            if yaml_data:
                # Merge service settings
                if "services" in yaml_data:
                    services_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["services"].items()
                    }
                    settings_obj.services = ServiceToggles(**services_data)

                # Merge Unlimited-OCR sub-settings (base_url, model_name, image_mode)
                unlimited_cfg = None
                if "services" in yaml_data and isinstance(yaml_data["services"].get("unlimited_ocr"), dict):
                    unlimited_cfg = yaml_data["services"]["unlimited_ocr"]
                if unlimited_cfg:
                    if "base_url" in unlimited_cfg:
                        settings_obj.unlimited_ocr_base_url = unlimited_cfg["base_url"]
                    if "model_name" in unlimited_cfg:
                        settings_obj.unlimited_ocr_model = unlimited_cfg["model_name"]
                    if "image_mode" in unlimited_cfg:
                        settings_obj.unlimited_ocr_image_mode = unlimited_cfg["image_mode"]
                    logger.info(
                        f"Unlimited-OCR configured: base_url={settings_obj.unlimited_ocr_base_url}, "
                        f"model={settings_obj.unlimited_ocr_model}, image_mode={settings_obj.unlimited_ocr_image_mode}"
                    )

                # Merge provider settings
                if "providers" in yaml_data:
                    providers_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["providers"].items()
                    }
                    settings_obj.providers = ProviderToggles(**providers_data)
                
                # Merge output channel settings
                if "integrations" in yaml_data:
                    integrations_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["integrations"].items()
                    }
                    settings_obj.integrations = IntegrationToggles(**integrations_data)
                    
                # Merge safety and privacy settings
                if "security" in yaml_data:
                    security_data = {
                        k: v.get("enabled", True) if isinstance(v, dict) else v
                        for k, v in yaml_data["security"].items()
                    }
                    settings_obj.security = SecuritySettings(**security_data)

                # Merge web crawler engine settings
                if "crawler" in yaml_data:
                    crawler_raw = yaml_data["crawler"]
                    crawler_data = {}
                    for k, v in crawler_raw.items():
                        if isinstance(v, dict):
                            # Support the {enabled: true} or {value: 300} format
                            crawler_data[k] = v.get("value", v.get("enabled", True))
                        else:
                            crawler_data[k] = v
                    settings_obj.crawler = CrawlerSettings(**crawler_data)

                # Merge general root settings
                if "jwt_secret_key" in yaml_data:
                    settings_obj.jwt_secret_key = yaml_data["jwt_secret_key"]
                if "password_salt" in yaml_data:
                    settings_obj.password_salt = yaml_data["password_salt"]
                if "env" in yaml_data:
                    settings_obj.env = yaml_data["env"]
                if "hormouz_embedding_model" in yaml_data:
                    settings_obj.hormouz_embedding_model = yaml_data["hormouz_embedding_model"]
                if "embedding_provider" in yaml_data:
                    settings_obj.embedding_provider = yaml_data["embedding_provider"]
                if "embedding_model" in yaml_data:
                    settings_obj.embedding_model = yaml_data["embedding_model"]
                if "proxy_url" in yaml_data:
                    settings_obj.proxy_url = yaml_data["proxy_url"]
                if "fallback_embedding_provider" in yaml_data:
                    settings_obj.fallback_embedding_provider = yaml_data["fallback_embedding_provider"]
                if "llm_provider" in yaml_data and not os.environ.get("LLM_PROVIDER"):
                    settings_obj.llm_provider = yaml_data["llm_provider"]
                if "model_name" in yaml_data and not os.environ.get("MODEL_NAME"):
                    settings_obj.model_name = yaml_data["model_name"]
                if "ollama_model" in yaml_data and not os.environ.get("OLLAMA_MODEL"):
                    settings_obj.ollama_model = yaml_data["ollama_model"]
                if "ollama_base_url" in yaml_data and not os.environ.get("OLLAMA_BASE_URL"):
                    settings_obj.ollama_base_url = yaml_data["ollama_base_url"]
                    
            logger.info("Successfully loaded dynamic feature toggles from config.yaml")
        except Exception as e:
            logger.error(f"Failed to parse config.yaml, using defaults. Error: {str(e)}")
    else:
        logger.warning("config.yaml not found at root, using default feature toggles.")

        
    return settings_obj

# Global settings object of the application for use across all modules
settings = load_settings()
