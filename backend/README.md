# ArioNex Backend — راهنمای تست API

> **توجه**: این راهنما برای تست مستقیم endpoint‌های بک‌اند **بدون نیاز به فرانت‌اند و بدون MinIO** طراحی شده است.

---

## پیش‌نیازها

```bash
# Python 3.11+
pip install -r requirements.txt
```

### تنظیم `.env` برای اجرای محلی بدون MinIO

فایل `backend/.env` را ویرایش کنید:

```env
# --- LLM Provider (یکی را انتخاب کنید) ---
LLM_PROVIDER=openrouter
MODEL_NAME=openai/gpt-4o-mini
OPENROUTER_API_KEY=sk-or-...        # کلید OpenRouter (دسترسی به همه مدل‌ها)

# یا مستقیم OpenAI:
# LLM_PROVIDER=openai
# MODEL_NAME=gpt-4o-mini
# OPENAI_API_KEY=sk-...

# --- Embedding ---
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
OPENAI_API_KEY=sk-...               # برای embedding همچنان نیاز است

# --- PostgreSQL (اجباری) ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=arionex_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# --- MinIO: خالی بگذارید تا fallback محلی فعال شود ---
MINIO_ENDPOINT=                     # خالی = بدون MinIO، ذخیره محلی
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
MINIO_BUCKET_NAME=arionex-raw-files

# --- سایر (اختیاری) ---
TAVILY_API_KEY=                     # اختیاری — برای جستجوی وب
TELEGRAM_BOT_TOKEN=                 # اختیاری
```

> 📌 **Mock Mode**: اگر `OPENROUTER_API_KEY` یا `OPENAI_API_KEY` را تنظیم نکنید، سیستم به‌صورت خودکار وارد حالت **Mock** می‌شود — پاسخ‌ها شبیه‌سازی‌شده‌اند ولی همه endpoint‌ها کار می‌کنند.

---

## راه‌اندازی PostgreSQL (بدون Docker)

```bash
# اگر PostgreSQL نصب دارید:
psql -U postgres -c "CREATE DATABASE arionex_db;"
```

یا با Docker (فقط پستگرس، بدون MinIO):

```bash
docker run -d \
  --name arionex-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=arionex_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

---

## اجرای سرور

```bash
cd backend

# روش ۱: مستقیم
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# روش ۲: از طریق main.py
python app/main.py
```

سرور روی `http://localhost:8000` در دسترس خواهد بود.

---

## مستندات تعاملی

| آدرس | توضیح |
|------|-------|
| `http://localhost:8000/docs` | **Swagger UI** — تست تعاملی همه endpoint‌ها |
| `http://localhost:8000/redoc` | **ReDoc** — مستندات رسمی |

---

## تست endpoint‌ها با `curl`

### ۱. بررسی سلامت سرور

```bash
curl http://localhost:8000/health
```

**پاسخ نمونه:**
```json
{
  "status": "online",
  "service": "ArioNex AI Assistant API",
  "version": "1.1.0",
  "llm": { "provider": "openrouter", "model": "openai/gpt-4o-mini" },
  "active_features": {
    "unstructured_doc": true,
    "qna_processor": true,
    "pii_redaction": true
  }
}
```

---

### ۲. ارسال پرسش به دستیار RAG

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "قراردادهای پیمانکاری شامل چه مواردی می‌شوند؟",
    "session_id": "test-session-001"
  }'
```

**پاسخ نمونه (Mock Mode):**
```json
{
  "answer": "بر اساس گزارش موجود در sample.pdf: ...",
  "sources": [{ "name": "sample.pdf", "page": "قطعه 1" }],
  "is_safe": true
}
```

**پرسش با فیلتر فایل:**
```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مجموع بدهکاری چقدر است؟",
    "session_id": "analyst-session",
    "file_ids": [101, 102]
  }'
```

---

### ۳. آپلود سند (بدون MinIO — ذخیره محلی)

**آپلود PDF:**
```bash
curl -X POST http://localhost:8000/v1/upload \
  -F "file=@/path/to/document.pdf"
```

**آپلود فایل QnA CSV:**
```bash
curl -X POST http://localhost:8000/v1/upload \
  -F "file=@/path/to/qna_data.csv"
```

فرمت CSV پرسش و پاسخ:
```csv
question,answer
چه خدماتی ارائه می‌دهید؟,ما خدمات مشاوره مالی و حقوقی ارائه می‌دهیم.
ساعات کاری چه زمانی است؟,از ۸ صبح تا ۵ بعد از ظهر.
```

**آپلود CSV حسابداری:**
```bash
curl -X POST http://localhost:8000/v1/upload \
  -F "file=@/path/to/accounting_data.csv"
```

**پاسخ نمونه:**
```json
{
  "file_id": 101,
  "filename": "document.pdf",
  "status": "success",
  "processor": "unstructured_document",
  "chunks_indexed": 24,
  "archive_url": "local",
  "pii_audit_counts": {},
  "pii_preview": ""
}
```

---

### ۴. مشاهده و تغییر پیکربندی

**دریافت پیکربندی فعال:**
```bash
curl http://localhost:8000/v1/config
```

**غیرفعال کردن جستجوی وب:**
```bash
curl -X POST http://localhost:8000/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "services": { "web_search": false }
  }'
```

**فعال/غیرفعال کردن PII Redaction:**
```bash
curl -X POST http://localhost:8000/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "security": { "pii_redaction": false }
  }'
```

---

### ۵. ابزارک چت وب‌سایت

**دریافت فایل JavaScript:**
```bash
curl http://localhost:8000/v1/widget.js
```

**ارسال پیام به ابزارک:**
```bash
curl -X POST http://localhost:8000/v1/widget/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "سلام، چه کمکی می‌توانید بکنید؟",
    "session_id": "widget-user-abc123"
  }'
```

---

## تغییر LLM Provider در زمان اجرا

برای تغییر provider بدون restart، فایل `.env` را ویرایش کنید و سرور را restart کنید:

```env
# استفاده از Claude Sonnet:
LLM_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# استفاده از Gemini:
LLM_PROVIDER=google
MODEL_NAME=gemini-1.5-pro-latest
GOOGLE_API_KEY=AIza...

# استفاده از DeepSeek:
LLM_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
DEEPSEEK_API_KEY=...

# استفاده از OpenRouter (پیشنهادی — یک کلید برای همه):
LLM_PROVIDER=openrouter
MODEL_NAME=anthropic/claude-3.5-sonnet   # یا هر مدل دیگر
OPENROUTER_API_KEY=sk-or-...
```

---

## ساختار دایرکتوری بک‌اند (پس از Refactoring)

```
backend/app/
├── prompts/          ← قالب‌های پرامپت LLM (RAG + Analyst)
├── schemas/          ← مدل‌های Pydantic (Query, Config)
├── routes/           ← FastAPI routers مستقل از frontend
│   ├── query_routes.py     POST /v1/query
│   ├── upload_routes.py    POST /v1/upload
│   ├── config_routes.py    GET/POST /v1/config
│   └── widget_routes.py    GET /v1/widget.js + POST /v1/widget/chat
├── logics/           ← منطق کسب‌وکار (جدا از router)
├── helpers/          ← توابع کمکی (file_id, audit, csv_detector)
├── core/
│   ├── llm_factory.py      ← کارخانه LLM (OpenAI, Anthropic, Google, DeepSeek, OpenRouter)
│   ├── embeddings.py       ← Embedding multi-provider
│   └── config.py           ← تنظیمات چندگانه provider
└── services/
    └── retrieval/
        ├── query_router.py   ← (سابقاً synthesizer.py)
        ├── vector_search.py  ← (سابقاً librarian.py)
        ├── qna.py            ← (سابقاً support_lead.py)
        ├── analyst.py
        └── query_rewriter.py
```

---

## عیب‌یابی رایج

| مشکل | راه‌حل |
|------|--------|
| `Connection refused` روی پورت 5432 | PostgreSQL را راه‌اندازی کنید |
| پاسخ mock — بدون RAG واقعی | `OPENROUTER_API_KEY` یا `OPENAI_API_KEY` را تنظیم کنید |
| خطای `pgvector` هنگام startup | افزونه pgvector را نصب کنید: `CREATE EXTENSION vector;` |
| MinIO error در لاگ | طبیعی است — سیستم به fallback محلی می‌رود |
| `Module not found: langchain_anthropic` | `pip install langchain-anthropic` را اجرا کنید |
