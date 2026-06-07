"""
/// <summary>
/// مدیریت ارتباطات پایگاه داده پستگرس و افزونه جی‌پی‌وکتور (PostgreSQL + pgvector connection manager)
/// </summary>
/// <remarks>
/// این کلاس وظیفه مدیریت کانکشن‌ها، باز و بسته کردن ارتباطات،
/// و راه‌اندازی اولیه تیبل‌ها (اگر وجود نداشته باشند) را بر عهده دارد.
/// </remarks>
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

logger = logging.getLogger("arionex.database")

def get_db_connection():
    """
    /// <summary>
    /// برقراری ارتباط با پایگاه داده PostgreSQL بر اساس کانفیگ‌های فعال سیستم
    /// </summary>
    /// <returns>یک شیء کانکشن معتبر از کتابخانه psycopg2</returns>
    /// <exception cref="psycopg2.OperationalError">در صورت بروز خطا در اتصال به پایگاه داده</exception>
    """
    try:
        conn = psycopg2.connect(
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port
        )
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {str(e)}")
        raise e

def init_db() -> None:
    """
    /// <summary>
    /// راه‌اندازی اولیه پایگاه داده و تعریف جداول مورد نیاز بر اساس خط لوله پردازش اطلاعات (Ingestion Pipeline)
    /// </summary>
    /// <remarks>
    /// این متد افزونه vector را فعال کرده و جداول pg_supervisor، qna_query، pg_dummy و لاگ‌های ممیزی را در صورت عدم وجود می‌سازد.
    /// </remarks>
    """
    logger.info("Initializing Database Tables and Extensions...")
    
    queries = [
        # فعال کردن اکستنشن وکتور برای ذخیره‌سازی امبدینگ‌های ۳۰۷۲ تایی
        "CREATE EXTENSION IF NOT EXISTS vector;",
        
        # ۱. جدول پردازشگر اسناد عمومی و متون بدون ساختار (Plain Doc Chunk Storage)
        """
        CREATE TABLE IF NOT EXISTS pg_supervisor (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector(3072),
            label TEXT,
            file_id INT,
            sequence_id INT
        );
        """,
        
        # ۲. جدول سوال و جواب‌ها و لاگ‌های پشتیبانی (QnA FAQ Storage)
        """
        CREATE TABLE IF NOT EXISTS qna_query (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector(3072),
            file_id INT,
            sequence_id INT
        );
        """,
        
        # ۳. جدول قطعات عمومی و فرعی (General Plain Doc Dummies)
        """
        CREATE TABLE IF NOT EXISTS pg_dummy (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector(3072)
        );
        """,
        
        # ۴. جدول حسابرسی و لاگ ممیزی مدیران ارشد (Audit Logs)
        """
        CREATE TABLE IF NOT EXISTS pg_audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_name VARCHAR(100) NOT NULL,
            user_role VARCHAR(50) NOT NULL,
            query_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            status VARCHAR(30) NOT NULL,
            pii_masked_count INT DEFAULT 0
        );
        """,
        # ۵. جدول ابزارک‌های وب‌سایت (Website Widgets)
        """
        CREATE TABLE IF NOT EXISTS website_widgets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            url VARCHAR(255) NOT NULL UNIQUE,
            welcome_message TEXT,
            theme_color VARCHAR(50),
            accent_color VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۶. جدول کلیدهای دسترسی API (API Keys)
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            api_key VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            last_used_at TIMESTAMP
        );
        """,
        # ۷. جدول موجودیت‌های استخراج شده برای گراف دانش (Extracted Entities)
        """
        CREATE TABLE IF NOT EXISTS extracted_entities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(100),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۸. جدول روابط بین موجودیت‌ها برای گراف دانش (Extracted Relationships)
        """
        CREATE TABLE IF NOT EXISTS extracted_relationships (
            id SERIAL PRIMARY KEY,
            source VARCHAR(255) NOT NULL,
            target VARCHAR(255) NOT NULL,
            relationship VARCHAR(255),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۹. جدول قوانین و آیین‌نامه‌های استخراج شده (Extracted Compliance Rules)
        """
        CREATE TABLE IF NOT EXISTS extracted_rules (
            id SERIAL PRIMARY KEY,
            rule_code VARCHAR(100),
            clause TEXT NOT NULL,
            type VARCHAR(100),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for query in queries:
                cur.execute(query)
            conn.commit()
        logger.info("Database and Extensions Initialized Successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
