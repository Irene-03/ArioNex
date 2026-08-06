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
import threading
import psycopg2
from psycopg2 import extensions
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from app.core.config import settings

logger = logging.getLogger("arionex.database")

# -------------------------------------------------------------------
# اتصال‌پول (Connection Pool) برای کاهش سربار دست‌دادن TCP + احراز هویت
# در هر فراخوانی — به‌جای ساخت کانکشن جدید برای هر کوئری
# -------------------------------------------------------------------
_pool = None
_pool_lock = threading.Lock()
_POOL_MAX_CONNECTIONS = 30


def _get_pool():
    """
    /// <summary>
    /// ساخت یا بازیابی اتصال‌پول سراسری PostgreSQL (lazy init)
    /// </summary>
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=_POOL_MAX_CONNECTIONS,
                    dbname=settings.postgres_db,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                    host=settings.postgres_host,
                    port=settings.postgres_port
                )
    return _pool


def _reset_connection(conn) -> None:
    """
    /// <summary>
    /// بازنشانی وضعیت تراکنش کانکشن پیش از برگرداندن به پول
    /// </summary>
    """
    try:
        if conn.get_transaction_status() != extensions.TRANSACTION_STATUS_IDLE:
            conn.rollback()
    except Exception:
        pass


def _return_connection(conn) -> None:
    try:
        _reset_connection(conn)
        _get_pool().putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


class _PooledConnection:
    """
    /// <summary>
    /// پوسته کانکشن پول‌شده — متد close() به‌جای بستن واقعی، کانکشن را به پول برمی‌گرداند
    /// تا تمامی کدهای موجود (conn.close()) بدون تغییر سازگار بمانند.
    /// </summary>
    """
    __slots__ = ("_conn",)

    def __init__(self, conn):
        self._conn = conn

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            _return_connection(conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def get_db_connection():
    """
    /// <summary>
    /// برقراری ارتباط با پایگاه داده PostgreSQL از اتصال‌پول بر اساس کانفیگ‌های فعال سیستم
    /// </summary>
    /// <returns>یک شیء کانکشن پول‌شده سازگار با psycopg2</returns>
    /// <exception cref="psycopg2.OperationalError">در صورت بروز خطا در اتصال به پایگاه داده</exception>
    """
    try:
        conn = _get_pool().getconn()
        _reset_connection(conn)
        return _PooledConnection(conn)
    except Exception as e:
        logger.error(f"PostgreSQL pooled connection failed: {str(e)}")
        raise e

def _create_vector_indexes(cur) -> None:
    """
    /// <summary>
    /// ساخت ایندکس برداری بهینه برای جداول جستجوی شباهت (pgvector)
    /// </summary>
    /// <remarks>
    /// ابتدا HNSW امتحان می‌شود (سریع‌ترین برای داده‌های حجیم). اگر ابعاد امبدینگ
    /// بیش از سقف ۲۰۰۰ بعدی HNSW باشد، به IVFFlat برمی‌گردد که هر ابعادی را پشتیبانی می‌کند.
    /// </remarks>
    """
    index_specs = [
        ("idx_pg_supervisor_embedding", "pg_supervisor"),
        ("idx_qna_query_embedding", "qna_query"),
        ("idx_pg_dummy_embedding", "pg_dummy"),
    ]
    for name, table in index_specs:
        # SAVEPOINT: خطای یک ایندکس نباید تراکنش جاری را مسموم کند
        cur.execute("SAVEPOINT vector_index_sp;")
        try:
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {name}_hnsw "
                f"ON {table} USING hnsw (embedding vector_cosine_ops);"
            )
            cur.execute("RELEASE SAVEPOINT vector_index_sp;")
            logger.info(f"Created HNSW vector index on {table}")
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT vector_index_sp;")
            logger.warning(
                f"HNSW index on {table} failed ({str(e)[:80]}). "
                f"Falling back to IVFFlat."
            )
            try:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {name}_ivfflat "
                    f"ON {table} USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = 100);"
                )
                cur.execute("RELEASE SAVEPOINT vector_index_sp;")
                logger.info(f"Created IVFFlat vector index on {table}")
            except Exception as e2:
                cur.execute("ROLLBACK TO SAVEPOINT vector_index_sp;")
                logger.error(f"Vector index on {table} failed: {str(e2)}")


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
            pii_masked_count INT DEFAULT 0,
            total_tokens INT DEFAULT 0,
            response_time_ms INT DEFAULT 0
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
            pii_masked_count INT DEFAULT 0,
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
        """,
    ]

    # Migration: existing tables created by older schema versions may be missing
    # columns that were added later. CREATE TABLE IF NOT EXISTS does not alter
    # existing tables, so we add the missing columns idempotently here.
    migrations = [
        "ALTER TABLE pg_audit_logs ADD COLUMN IF NOT EXISTS pii_masked_count INT DEFAULT 0;",
        "ALTER TABLE pg_audit_logs ADD COLUMN IF NOT EXISTS total_tokens INT DEFAULT 0;",
        "ALTER TABLE pg_audit_logs ADD COLUMN IF NOT EXISTS response_time_ms INT DEFAULT 0;",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS pii_masked_count INT DEFAULT 0;",
    ]

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for query in queries:
                cur.execute(query)

            for migration in migrations:
                cur.execute(migration)

            # ایندکس‌های برداری (HNSW یا IVFFlat بسته به ابعاد امبدینگ)
            _create_vector_indexes(cur)
            
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

