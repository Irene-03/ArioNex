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
        # ۷. جدول ردیابی Job‌های کرالر وب (Web Crawler Jobs)
        """
        CREATE TABLE IF NOT EXISTS crawler_jobs (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(64) UNIQUE NOT NULL,
            url VARCHAR(2048) NOT NULL,
            status VARCHAR(30) DEFAULT 'queued',
            pages_crawled INT DEFAULT 0,
            chunks_indexed INT DEFAULT 0,
            pages_failed INT DEFAULT 0,
            max_pages INT DEFAULT 50,
            max_depth INT DEFAULT 3,
            concurrency INT DEFAULT 5,
            js_render BOOLEAN DEFAULT FALSE,
            follow_external BOOLEAN DEFAULT FALSE,
            label VARCHAR(255),
            error_message TEXT,
            widget_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۸. جدول کاربران سیستم (Users Table)
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'Analyst',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۹. جدول فایل‌های آپلود شده و سطح دسترسی (Documents & ACL)
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            min_role_required VARCHAR(50) NOT NULL DEFAULT 'Analyst',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۱۰. جدول پرامپت‌های سیستم (System Prompts Table)
        """
        CREATE TABLE IF NOT EXISTS system_prompts (
            key VARCHAR(100) PRIMARY KEY,
            prompt TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # ۱۱. جدول موجودیت‌های استخراج شده برای گراف دانش (Extracted Entities)
        """
        CREATE TABLE IF NOT EXISTS extracted_entities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(100),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (file_id, name)
        );
        """,
        # ۱۲. جدول روابط بین موجودیت‌ها برای گراف دانش (Extracted Relationships)
        """
        CREATE TABLE IF NOT EXISTS extracted_relationships (
            id SERIAL PRIMARY KEY,
            source VARCHAR(255) NOT NULL,
            target VARCHAR(255) NOT NULL,
            relationship VARCHAR(255),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (file_id, source, target, relationship)
        );
        """,
        # ۱۳. جدول قوانین و آیین‌نامه‌های استخراج شده (Extracted Compliance Rules)
        """
        CREATE TABLE IF NOT EXISTS extracted_rules (
            id SERIAL PRIMARY KEY,
            rule_code VARCHAR(100),
            clause TEXT NOT NULL,
            type VARCHAR(100),
            description TEXT,
            file_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (file_id, rule_code)
        );
        """,
        # ۱۴. جدول گزارش‌های ممیزی انطباق قوانین (Compliance Audit Logs)
        """
        CREATE TABLE IF NOT EXISTS compliance_audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_id INT,
            query_text TEXT,
            response_text TEXT,
            is_compliant BOOLEAN NOT NULL,
            violations TEXT,
            audit_report TEXT
        );
        """,
        # ۱۵. جدول دسته‌بندی‌ها (Categories Table)
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE
        );
        """,
        # ۱۶. جدول فیلدهای سفارشی‌سازی (Customization Fields Table)
        """
        CREATE TABLE IF NOT EXISTS customization_fields (
            id SERIAL PRIMARY KEY,
            field_name VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        );
        """
    ]
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for query in queries:
                cur.execute(query)
            
            # ثبت کاربر ادمین پیش‌فرض در صورت عدم وجود (پسورد: admin123)
            from app.routes.auth_routes import hash_password
            admin_username = "admin"
            admin_pwd_hash = hash_password("admin123")
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'Admin')
                ON CONFLICT (username) DO NOTHING;
                """,
                (admin_username, admin_pwd_hash)
            )

            # ثبت پرامپت سیستم پیش‌فرض
            default_prompt = (
                "شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. "
                "هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید."
            )
            cur.execute(
                """
                INSERT INTO system_prompts (key, prompt)
                VALUES ('default_system_instruction', %s)
                ON CONFLICT (key) DO NOTHING;
                """,
                (default_prompt,)
            )

            # بررسی و سید دسته‌بندی‌ها در صورت خالی بودن جدول
            cur.execute("SELECT COUNT(*) FROM categories;")
            if cur.fetchone()[0] == 0:
                default_cats = [
                    (1, "کارگزاری ایساتیس پویا، ثبت نام غیرحضوری، اعتبار معاملاتی، معاملات اختیارمعامله، لینک سامانه‌ کارگزاری"),
                    (2, "کد مشتقه کالایی"),
                    (3, "کد بورس کالا اشخاص حقیقی"),
                    (4, "سامانه آنلاین پلاس، پیش سفارش عرضه اولیه"),
                    (5, "کارگزار ناظر، تغییر کارگزار ناظر"),
                    (6, "سهام عدالت، انتقال سهام متوفیان، انحصار وراثت"),
                    (7, "خطای مانده حساب، تسویه T+1 و T+2، خطای پنل آنلاین"),
                    (8, "افزایش سرمایه، تجدید ارزیابی دارایی‌، آورده نقدی و حق تقدم، تبدیل حق تقدم به سهم"),
                    (9, "گواهی سپرده کالایی، بورس کالا، مزایای گواهی سپرده"),
                    (10, "قرارداد اختیار معامله، ابزارهای مشتقه، تأثیر اقدامات شرکتی بر اختیار معامله"),
                    (11, "تغییر شماره حساب"),
                    (12, "بازار جبرانی، تمدید زمان معاملات، دامنه نوسان بازار"),
                    (13, "تسویه نقدی، تسویه فیزیکی")
                ]
                cur.executemany(
                    "INSERT INTO categories (id, name) VALUES (%s, %s);",
                    default_cats
                )
                logger.info("Seeded 13 default categories into database.")

            # بررسی و سید فیلدهای سفارشی‌سازی در صورت خالی بودن جدول
            cur.execute("SELECT COUNT(*) FROM customization_fields;")
            if cur.fetchone()[0] == 0:
                default_fields = [
                    ("cloud saves",),
                    ("Workshop",),
                    ("Steam",)
                ]
                cur.executemany(
                    "INSERT INTO customization_fields (field_name) VALUES (%s);",
                    default_fields
                )
                logger.info("Seeded default customization fields into database.")

            conn.commit()
        logger.info("Database and Extensions Initialized Successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

