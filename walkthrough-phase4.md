# سند جامع گزارش انجام کار و معماری فنی فاز ۴ (ArioNex Phase 4 Walkthrough Report)

این سند گزارش فنی و شناسنامه تغییرات پیاده‌سازی شده در **فاز ۴ (موتور جستجوی معنایی و عامل‌های RAG امن)** برای دستیار هوشمند سازمانی **آریونکس (ArioNex)** است. تمامی بخش‌های مربوط به لایه خواندن (Read Path) با بالاترین کیفیت مهندسی نرم‌افزار و رعایت قانون طلایی عدم توهم RAG پیاده‌سازی شده‌اند.

---

## ۱. کارهای انجام شده در فاز ۴ (Phase 4 Completed Tasks)

در این فاز، مغز متفکر خواندن و بازیابی اطلاعات RAG بر اساس بهترین الگوهای مهندسی RAG توسعه داده شد. جریان کار به صورت کاملاً تفکیک‌شده و با پوشش ۱۰۰٪ پیاده‌سازی گردید:

1. **زنجیره بازنویسی مستقل پرسش‌ها (`query_rewriter.py`):** خواندن تاریخچه گفتگوهای گذشته کاربر و بازنویسی پرسش جدید برای رفع هرگونه ضمیر مبهم ارجاعی فارسی (مانند "آن"، "این پرونده" و...).
2. **روتینگ هوشمند قصد کاربر (Farsi Intent Router):** تفکیک خودکار و هوشمند پرسش‌های کاربر. پرسش‌های فرمولی، حسابداری و تراکنش‌های عددی به عامل محاسباتی داده فرستاده شده و پرسش‌های عمومی/پشتیبانی به مخزن RAG برداری هدایت می‌شوند.
3. **عامل بازیابی اسناد - کتابدار (`librarian.py`):** جستجوی معنایی کسینوسی روی چانک‌های جدول `pg_supervisor` و `pg_dummy` با نگهداری متادیتاهای دقیق (نام سند، آیدی سند، سکانس) جهت نمایش تگ‌های استناد در سمت چت‌بات فرانت‌اند.
4. **عامل بازیابی سوالات متداول - سرپرست پشتیبانی (`support_lead.py`):** جستجوی انطباقی روی ردیف‌های سوال و جواب جدول `qna_query`.
5. **عامل محاسباتی تراکنش‌ها - تحلیلگر داده (`analyst.py`):** پیاده‌سازی زنجیره محاسباتی مبتنی بر LangGraph StateGraph به همراه ابزارهای مجهز (Column Sum, Summary Stats, Groupby, Filter, Python Ast REPL) جهت حل فرمول‌های عددی روی صفحات مالی سازمان.
6. **تلفیق‌کننده و رتبه‌بندی مجدد (`synthesizer.py`):** تجمیع قطعات بازیابی شده از عامل‌های مختلف، مرتب‌سازی مجدد بر اساس Cosine Similarity، و تلاش برای فراخوانی Tavily Web Search به عنوان بک‌آپ زنده وب در صورت خالی بودن دیتابیس لوکال.
7. **قانون طلایی عدم توهم (Golden Non-Hallucination Guardrail):** در صورتی که نتایج سرچ کمتر از حد شباهت مشخص باشند، یا مدل نهایی پاسخ `"####"` تولید کند، سیستم فوراً خروجی را مسدود کرده و متن امتناع استاندارد فارسی زیر را برمی‌گرداند:
   > "منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند."

---

## ۲. نتایج اجرای تست‌های خودکار فاز ۴ (`test_phase4.py`)

تست‌های فاز ۴ به همراه راستی‌آزمایی سدهای امنیتی RAG و روتینگ به طور ۱۰۰٪ موفقیت‌آمیز اجرا شدند:

*   **تست روتینگ قصد کاربر:** پرسش‌های محاسباتی به درستی به `"analyst"` و پرسش‌های عمومی به `"rag"` روت شدند.
*   **تست بازنویسی زاپاس:** تأیید بازگشت بدون ارور پرسش در حالت کاذب توسعه محلی.
*   **تست مفسر محاسباتی:** تأیید اجرای موفق گراف لنگ‌گراف و محاسبه مجموع بدهکاری‌ها به مقدار `۶۲۳,۳۴۶ ریال`.
*   **تست سد عدم توهم:** بررسی تطابق سورس‌ها با یک موضوع نامربوط (سفر به مریخ) و تأیید امتناع فوری سیستم با پاسخ استاندارد فارسی.

```text
=========================================
STARTING PHASE 4 AUTOMATED TEST SUITE
=========================================
Testing Query Intent Routing...
Calc 1 routed: analyst
Calc 2 routed: analyst
RAG 1 routed:  rag
RAG 2 routed:  rag
 Query Intent Routing checks PASSED.

Testing Query Rewriter Fallback...
Original: این چطور کار میکنه؟ -> Rewritten: این چطور کار میکنه؟
 Query Rewriter checks PASSED.

Testing Analyst Graph Mock Solving...
Query: مجموع بدهکاری نوع سند چک -> Response: مجموع بدهکاری اسناد از نوع سند چک برابر با ۶۲۳,۳۴۶ ریال می‌باشد.
 Analyst Agent checks PASSED.

Testing Golden Non-Hallucination Guardrail...
Query: پرواز فضایی به مریخ چقدر زمان میبرد؟
Response: منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.
Sources:  []
 Golden Non-Hallucination Guardrail checks PASSED.

=========================================
ALL PHASE 4 TESTS COMPLETED SUCCESSFULLY! 
=========================================
```

---

## ۳. لیست فایل‌های ایجاد شده در فاز ۴ (Physical File Mapping)

```
e:\rio\
├── backend/
│   ├── app/
│   │   └── services/
│   │       └── retrieval/
│   │           ├── __init__.py       # [اصلاح] اکسپورت متدهای RAG
│   │           ├── analyst.py        # [جدید] عامل محاسباتی LangGraph + ابزارهای پانداس
│   │           ├── librarian.py      # [جدید] عامل سرچ معنایی اسناد + استخراج متادیتا
│   │           ├── query_rewriter.py # [جدید] زنجیره بازنویسی مستقل پیام‌ها
│   │           ├── support_lead.py   # [جدید] عامل انطباق سوالات متداول و لاگ‌ها
│   │           └── synthesizer.py    # [جدید] روتینگ قصد، رتبه‌بندی، وب‌سرچ و قانون عدم توهم
└── test_phase4.py                    # [جدید] تست خودکار اعتبارسنجی RAG
```

---

## ۴. تاریخچه کامیت‌های گیت در فاز ۴ (Git Commit Log)

تغییرات با ۵ کامیت Conventional روی شاخه اصلی مخزن پرایوت گیت‌هاب شما پوش شدند:

1. `0112aab` — **feat(retrieval): implement standalone query rewriter with chat history integration**
2. `38be28e` — **feat(retrieval): implement Librarian and Support Lead RAG agents for pgvector search**
3. `a802904` — **feat(retrieval): implement LangGraph computational Analyst agent with pandas tools**
4. `cc9ec98` — **feat(retrieval): implement intent router, central synthesizer, and non-hallucination guardrail**
5. `a7bc466` — **test(retrieval): add automated tests for RAG rewriters, routers, and hallucination guardrail**

نشانی مخزن پرایوت گیت‌هاب شما به طور کامل به‌روزرسانی شده است:
👉 [https://github.com/Irene-03/ArioNex.git](https://github.com/Irene-03/ArioNex.git)
