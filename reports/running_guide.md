# راهنمای قدم‌به‌قدم اجرا، تست و آنالیز آریونکس (ArioNex Step-by-Step Execution & Testing Guide)

این سند راهنمای عملیاتی برای راه‌اندازی، اجرا، تست و آنالیز دستیار هوشمند آریونکس است. تمام روش‌های اجرا — از ساده‌ترین حالت توسعه محلی تا استقرار کامل داکری — در اینجا توضیح داده شده‌اند.

---

## 🗂️ پیش‌نیازها (Prerequisites)

قبل از هر چیز، اطمینان حاصل کنید که موارد زیر روی سیستم شما نصب است:

| ابزار | نسخه حداقل | دستور تایید نصب |
|:---|:---:|:---|
| **Python** | 3.10+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Git** | هر نسخه | `git --version` |
| **Docker Desktop** | 24+ (اختیاری) | `docker --version` |

---

## ⚡ حالت ۱: اجرای سریع محلی برای تست (Recommended for Testing)

این حالت **بدون Docker، بدون MinIO و بدون PostgreSQL** کار می‌کند. همه چیز محلی و آفلاین است.

### قدم ۱ — کلون کردن پروژه

```powershell
git clone https://github.com/Irene-03/ArioNex.git
cd ArioNex
```

### قدم ۲ — ساخت محیط مجازی پایتون و نصب پکیج‌ها

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate          # در ویندوز
# یا:
source venv/bin/activate         # در لینوکس/مک

pip install -r requirements.txt
pip install python-multipart     # مورد نیاز برای آپلود فایل‌ها
```

### قدم ۳ — تنظیم فایل متغیرهای محیطی

فایل `backend/.env` از قبل وجود دارد. مطمئن شوید این خط در آن هست و `true` باشد:

```env
USE_LOCAL_DATA_DIR=true
```

> **نکته:** با این تنظیم، سیستم کاملاً از MinIO صرف‌نظر می‌کند و فایل‌ها را در پوشه `data/` ذخیره می‌کند. برای RAG واقعی، کلید OpenAI را هم تنظیم کنید:
> ```env
> OPENAI_API_KEY=your-real-key-here
> ```

### قدم ۴ — اجرای بک‌بند FastAPI

```powershell
# از پوشه backend اجرا کنید
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**خروجی موفق در ترمینال:**
```text
[INFO] [arionex.minio] - USE_LOCAL_DATA_DIR=true detected. MinIO is bypassed.
[INFO] [arionex.main]  - ArioNex Enterprise Backend is starting up...
[INFO] [uvicorn]       - Application startup complete.
[INFO] [uvicorn]       - Uvicorn running on http://127.0.0.1:8000
```

### قدم ۵ — اجرای فرانت‌بند React (در ترمینال جداگانه)

```powershell
cd frontend
npm install
npm run dev
```

**خروجی موفق:**
```text
  VITE v5.x  ready in 95ms
  ➜  Local:   http://localhost:5173/
```

### قدم ۶ — تست اولیه در مرورگر

| آدرس | توضیح |
|:---|:---|
| `http://localhost:5173` | داشبورد مجلل React |
| `http://localhost:8000/docs` | مستندات Swagger/OpenAPI تعاملی |
| `http://localhost:8000/health` | بررسی سلامت سیستم (JSON) |

---

## 📁 حالت ۲: بارگذاری داده برای تست RAG (Local Data Ingestion)

برای اینکه RAG واقعی کار کند، باید ابتدا اسناد را در پوشه‌های مناسب قرار داده و ایندکس کنید.

### قدم ۱ — قرار دادن فایل‌ها در دایرکتوری‌های مناسب

```text
ario/
└── data/
    ├── unstructured/    ← فایل‌های PDF، Word، TXT سازمانی بگذارید
    ├── structured/      ← جداول مالی CSV/Excel بگذارید
    └── qna/             ← فایل‌های CSV پرسش و پاسخ بگذارید
```

**مثال — ساخت یک فایل تست ساده:**

```powershell
# ایجاد یک سند تستی ساده برای unstructured
"این یک سند آزمایشی آریونکس است. قوانین مرخصی سالانه ۳۰ روز می‌باشد." | `
  Out-File -FilePath "data\unstructured\test_policy.txt" -Encoding utf8

# ایجاد یک فایل QnA تستی
"سوال,پاسخ`nقوانین مرخصی چیست?,۳۰ روز در سال" | `
  Out-File -FilePath "data\qna\test_faq.csv" -Encoding utf8
```

### قدم ۲ — اجرای اسکریپت ایندکس‌سازی دسته‌ای

```powershell
cd backend
.\venv\Scripts\activate

# ایندکس کردن همه انواع داده
python scripts\ingest_local_data.py --type all

# یا فقط یک نوع
python scripts\ingest_local_data.py --type unstructured
python scripts\ingest_local_data.py --type qna
python scripts\ingest_local_data.py --type structured

# مشاهده لیست فایل‌های موجود
python scripts\ingest_local_data.py --list
```

**خروجی موفق:**
```text
============================================================
  ArioNex Local Batch Data Ingestor
  (حالت: Local Data Directory - MinIO غیرفعال)
============================================================

============================================================
  ایندکس‌سازی اسناد بدون ساختار (Unstructured Documents)
============================================================
[INFO] [arionex.local_storage] - Processing file: test_policy.txt (id=1000)
[INFO] [arionex.local_storage] - Successfully ingested: test_policy.txt

  نتیجه: 1 موفق | 0 ناموفق از 1 فایل
```

---

## 🧪 حالت ۳: اجرای تست‌های خودکار (Automated QA Tests)

### تست سراسری تجمیعی (همه فازها)

```powershell
cd backend
.\venv\Scripts\activate

$env:PYTHONIOENCODING = "utf-8"
python ..\tests\test_phase7.py
```

### تست فازهای جداگانه

```powershell
# تست ایرلاک PII و پردازش متون فارسی
python ..\tests\test_phase2.py

# تست پردازشگرهای اسناد
python ..\tests\test_phase3.py

# تست موتور RAG و عامل‌های هوش مصنوعی
python ..\tests\test_phase4.py

# تست درگاه‌های API، ربات تلگرام و ویجت
python ..\tests\test_phase5.py
```

### تست سریع اندپوینت‌ها با curl

```powershell
# بررسی سلامت سیستم
curl http://localhost:8000/health

# ارسال پرسش به موتور RAG
curl -X POST http://localhost:8000/v1/query `
  -H "Content-Type: application/json" `
  -d '{"query": "قوانین مرخصی چیست؟", "session_id": "test-001"}'

# دریافت وضعیت فیچر تاگل‌ها
curl http://localhost:8000/v1/config

# آپلود یک فایل تستی
curl -X POST http://localhost:8000/v1/upload `
  -F "file=@data/unstructured/test_policy.txt"
```

---

## 🐳 حالت ۴: اجرای کامل داکری (Full Docker Deployment)

این حالت برای محیط‌های Production یا تست یکپارچه کامل استفاده می‌شود.

### قدم ۱ — تنظیم `.env` برای داکر

در فایل `backend/.env` موارد زیر را اطمینان حاصل کنید:

```env
USE_LOCAL_DATA_DIR=false     # در داکر از MinIO استفاده می‌شود
POSTGRES_HOST=db             # نام سرویس داکر
MINIO_ENDPOINT=minio:9000    # نام سرویس داکر
```

### قدم ۲ — راه‌اندازی کل شبکه

```powershell
# از پوشه ریشه پروژه
docker-compose up -d --build
```

### قدم ۳ — بررسی وضعیت کانتینرها

```powershell
docker-compose ps
docker-compose logs -f backend    # لاگ‌های بک‌بند
docker-compose logs -f db         # لاگ‌های دیتابیس
```

### آدرس‌های دسترسی در حالت داکر

| آدرس | سرویس |
|:---|:---|
| `http://localhost` | داشبورد React (پورت ۸۰) |
| `http://localhost:8000/docs` | Swagger API |
| `http://localhost:9001` | کنسول MinIO |

### توقف و حذف کانتینرها

```powershell
docker-compose down              # توقف و حذف کانتینرها
docker-compose down -v           # حذف کانتینرها + volumes (داده‌ها پاک می‌شوند)
```

---

## 🔍 حالت ۵: دیباگ و آنالیز مستقیم ماژول‌ها (Module-Level Debugging)

### آنالیز مستقیم ماژول PII Redactor

```powershell
cd backend
.\venv\Scripts\activate
python -c "
from app.services.safety.pii_redactor import redact_text, redact_and_audit
text = 'کد ملی: 1234567890 و شماره: 09123456789'
result = redact_and_audit(text)
print('متن سانسور شده:', result['redacted_text'])
print('آمار:', result['counts'])
"
```

### آنالیز مستقیم نرمال‌ساز فارسی

```powershell
python -c "
from app.services.workers.text_processor import normalize_text, chunk_text
text = 'این یک متنِ آزمایشی با اعراب و ارقام فارسی ۱۲۳۴ است.'
print('نرمال شده:', normalize_text(text))
chunks = chunk_text(text * 20)
print('تعداد چانک‌ها:', len(chunks))
"
```

### مشاهده لاگ‌های بک‌بند در لحظه

```powershell
# در یک ترمینال: سرور را با لاگ کامل اجرا کنید
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug
```

---

## 📊 جدول خلاصه حالت‌های اجرا

| حالت | PostgreSQL | MinIO | Docker | مناسب برای |
|:---|:---:|:---:|:---:|:---|
| **حالت ۱: محلی سریع** | ❌ (fallback) | ❌ (bypassed) | ❌ | توسعه روزانه |
| **حالت ۲: Ingest محلی** | ❌ | ❌ | ❌ | بارگذاری داده تست |
| **حالت ۳: تست خودکار** | ❌ | ❌ | ❌ | CI/CD و QA |
| **حالت ۴: داکر کامل** | ✅ | ✅ | ✅ | Production/Staging |
| **حالت ۵: دیباگ ماژول** | ❌ | ❌ | ❌ | خطایابی عمیق |

---

## ❓ رفع مشکلات رایج (Troubleshooting)

### مشکل: `ModuleNotFoundError: No module named 'app'`
```powershell
# مطمئن شوید از پوشه backend اجرا می‌کنید:
cd backend
python scripts\ingest_local_data.py --type all
```

### مشکل: `python-multipart is not installed`
```powershell
pip install python-multipart
```

### مشکل: لاگ‌های خطای اتصال به PostgreSQL در تست
این لاگ‌ها طبیعی‌اند. سیستم به fallback محلی سوئیچ می‌کند و تست‌ها پاس می‌شوند.

### مشکل: فونت فارسی در ترمینال ویندوز خراب است
```powershell
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
```
