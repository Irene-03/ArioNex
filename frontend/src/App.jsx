/*
/// <summary>
/// کامپوننت اصلی و روت فرانت‌اند سامانه تجاری آریونکس (ArioNex React Dashboard Client)
/// </summary>
/// <remarks>
/// این بخش تمامی صفحات داشبورد، چت بات، آپلود فایل، پنل ادمین و یکپارچه‌سازی‌ها را
/// به همراه تعاملات داینامیک و افکت‌های میکرو بر اساس پالت رنگی سورمه‌ای و مسی پیاده‌سازی می‌کند.
/// </remarks>
*/

import React, { useState, useEffect } from 'react';
import './App.css';

// ─────────────────────────────────────────────────────────────────────────────
// ⚙️  MOCK MODE — برای تست UI بدون بک‌اند
//   true  → تمام API calls با داده‌های واقع‌بینانه شبیه‌سازی می‌شوند
//   false → اتصال واقعی به http://localhost:8000
// ─────────────────────────────────────────────────────────────────────────────
const MOCK_MODE = true;

/** شبیه‌سازی تاخیر شبکه (میلی‌ثانیه) */
const mockDelay = (ms = 600) => new Promise(resolve => setTimeout(resolve, ms));

/** داده‌های تنظیمات Mock */
const MOCK_CONFIG = {
  security: { pii_redaction: true, strict_non_hallucination: true },
  services: { safety_auditor: false, log_processor: true, web_search: false },
  integrations: { telegram_bot: true, popup_widget: true, rest_api: true }
};

/** پاسخ‌های نمونه برای چت Mock */
const MOCK_ANSWERS = [
  {
    answer: 'بر اساس آیین‌نامه استخدامی شرکت، مرخصی سالانه کارکنان ۳۰ روز کاری است. کارکنان می‌توانند حداکثر ۱۵ روز آن را به سال بعد انتقال دهند.',
    sources: [
      { doc_name: 'HR_Policy_Manual_v2.docx', sequence_id: 12 },
      { doc_name: 'Annual_Report_2024.pdf', sequence_id: 47 }
    ],
    is_safe: true
  },
  {
    answer: 'مجموع بدهکاری شرکت در پایان سال مالی ۱۴۰۳ برابر با ۲۴۷ میلیارد ریال بوده که نسبت به سال قبل ۱۲٪ کاهش داشته است.',
    sources: [
      { doc_name: 'Sales_Data_Q2.csv', sequence_id: 3 }
    ],
    is_safe: true
  },
  {
    answer: 'منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.',
    sources: [],
    is_safe: true
  },
  {
    answer: 'قرارداد با تامین‌کننده شماره A-2024-087 در تاریخ ۱۵ شهریور ۱۴۰۳ امضا شده و تا پایان اسفند ۱۴۰۴ اعتبار دارد. مبلغ قرارداد ۸۵۰ میلیون تومان می‌باشد.',
    sources: [
      { doc_name: 'Supplier_Contracts_Q3.pdf', sequence_id: 22 },
      { doc_name: 'Supplier_Contracts_Q3.pdf', sequence_id: 23 }
    ],
    is_safe: true
  }
];
let _mockAnswerIdx = 0;

export default function App() {
  // صفحه فعال جاری در داشبورد
  const [activeScreen, setActiveScreen] = useState('dashboard');
  
  // تنظیمات فیچر تاگل سیستم (ادمینی)
  const [features, setFeatures] = useState({
    piiRedaction: true,
    localGemma: true,
    hallucinationGuard: true,
    externalApiBlocked: true,
    strictCitation: true,
    auditLog: true,
    telegramBot: true,
    popupWidget: true,
    restApi: true
  });

  // لیست پیام‌های پنجره چت
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      text: 'سلام! من دستیار دانش امن شما (آریو) هستم. تمام پرسش‌ها روی داده‌های خصوصی شما اجرا می‌شوند — هیچ اطلاعاتی از زیرساخت شما خارج نمی‌شود. چطور می‌توانم کمک کنم؟',
      isSafe: true,
      sources: []
    }
  ]);

  // پیام متنی تایپ شده توسط کاربر
  const [inputText, setInputText] = useState('');
  // وضعیت لودینگ دستیار هوش مصنوعی
  const [isAiLoading, setIsAiLoading] = useState(false);

  // دستورالعمل‌های پایه سیستم (System Instruction)
  const [systemInstruction, setSystemInstruction] = useState(
    'شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید…'
  );

  // لیست فایل‌های آپلود شده و وضعیت پردازش آن‌ها
  const [documents, setDocuments] = useState([
    { id: 1, name: 'Annual_Report_2024.pdf', size: '4.2 MB', chunks: 1204, date: '۲۰ اردیبهشت', status: 'ready', ext: 'PDF' },
    { id: 2, name: 'Sales_Data_Q2.csv', size: '890 KB', chunks: 387, date: '۲۲ اردیبهشت', status: 'ready', ext: 'CSV' },
    { id: 3, name: 'HR_Policy_Manual_v2.docx', size: '1.8 MB', chunks: 0, date: 'امروز', status: 'processing', progress: 62, ext: 'DOC' },
    { id: 4, name: 'Supplier_Contracts_Q3.pdf', size: '6.1 MB', chunks: 2881, date: '۱۸ اردیبهشت', status: 'ready', ext: 'PDF' },
    { id: 5, name: 'Support_Tickets_2024.csv', size: '3.4 MB', chunks: 918, date: '۱۵ اردیبهشت', status: 'ready', ext: 'CSV' }
  ]);

  // متغیرهای وضعیت پیش‌نمایش قفل حریم شخصی PII
  const [piiPreview, setPiiPreview] = useState('');
  const [piiAuditCounts, setPiiAuditCounts] = useState({});

  // همگام‌سازی فیچر تاگل‌ها با روشن شدن فرانت‌اند
  useEffect(() => {
    const loadConfig = async () => {
      try {
        let data;
        if (MOCK_MODE) {
          // --- حالت Mock: بدون نیاز به بک‌اند ---
          await mockDelay(300);
          data = MOCK_CONFIG;
          console.info('[MOCK] Loaded config from mock data.');
        } else {
          const res = await fetch('http://localhost:8000/v1/config');
          data = await res.json();
        }
        if (data) {
          setFeatures({
            piiRedaction: data.security?.pii_redaction ?? true,
            localGemma: data.services?.safety_auditor ?? false,
            hallucinationGuard: data.security?.strict_non_hallucination ?? true,
            externalApiBlocked: !(data.services?.web_search ?? true),
            strictCitation: true,
            auditLog: data.services?.log_processor ?? true,
            telegramBot: data.integrations?.telegram_bot ?? true,
            popupWidget: data.integrations?.popup_widget ?? true,
            restApi: data.integrations?.rest_api ?? true
          });
        }
      } catch (err) {
        console.error('Error loading configuration:', err);
      }
    };
    loadConfig();
  }, []);

  // کنترل تغییر وضعیت دکمه‌ها در پنل ادمین و ذخیره در بک‌اند
  const toggleFeature = (key) => {
    const updatedFeatures = { ...features, [key]: !features[key] };
    setFeatures(updatedFeatures);

    if (MOCK_MODE) {
      // --- حالت Mock: فقط state محلی تغییر می‌کند ---
      console.info('[MOCK] Feature toggle updated locally (no API call):', key, '->', !features[key]);
      return;
    }

    // ثبت زنده تاگل‌ها در وب‌سرور FastAPI
    fetch('http://localhost:8000/v1/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        services: {
          safety_auditor: updatedFeatures.localGemma,
          log_processor: updatedFeatures.auditLog,
          web_search: !updatedFeatures.externalApiBlocked
        },
        integrations: {
          telegram_bot: updatedFeatures.telegramBot,
          popup_widget: updatedFeatures.popupWidget,
          rest_api: updatedFeatures.restApi
        },
        security: {
          pii_redaction: updatedFeatures.piiRedaction,
          strict_non_hallucination: updatedFeatures.hallucinationGuard
        }
      })
    })
    .then(res => res.json())
    .then(data => console.log('Feature toggles synchronized:', data))
    .catch(err => console.error('Failed to sync feature toggles:', err));
  };

  // ارسال پیام جدید به دستیار هوشمند و دریافت پاسخ واقعی RAG
  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = { id: Date.now(), sender: 'user', text: inputText, sources: [] };
    setChatMessages(prev => [...prev, userMessage]);
    const queryText = inputText;
    setInputText('');
    setIsAiLoading(true);

    try {
      let data;
      if (MOCK_MODE) {
        // --- حالت Mock: پاسخ چرخشی از لیست نمونه ---
        await mockDelay(900);
        data = MOCK_ANSWERS[_mockAnswerIdx % MOCK_ANSWERS.length];
        _mockAnswerIdx++;
        console.info('[MOCK] Returned mock answer #', _mockAnswerIdx);
      } else {
        const res = await fetch('http://localhost:8000/v1/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: queryText, session_id: 'react_admin_dashboard_chat' })
        });
        data = await res.json();
      }

      const isRefusal = data.answer === 'منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.';
      setChatMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ai',
        text: data.answer || '⚠️ پاسخی دریافت نشد.',
        sources: data.sources || [],
        isSafe: data.is_safe ?? true,
        isRefusal
      }]);
    } catch (err) {
      console.error('Error communicating with query API:', err);
      setChatMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ai',
        text: '⚠️ خطا در برقراری ارتباط با وب‌سرور هوشمند آریونکس. لطفاً اطمینان حاصل فرمایید که بک‌اند بر روی پورت 8000 در حال اجراست.',
        sources: [],
        isSafe: true,
        isRefusal: true
      }]);
    } finally {
      setIsAiLoading(false);
    }
  };

  // ارسال فایل واقعی به اندپوینت آپلود و دریافت پیش‌نمایش قفل حریم شخصی PII
  const handleFileUpload = (e) => {
    e.preventDefault();
    let file = null;

    if (e.type === 'drop') {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        file = e.dataTransfer.files[0];
      }
    } else {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = '.pdf,.docx,.doc,.csv,.txt,.json,.xml,.mmd';
      fileInput.onchange = (event) => {
        if (event.target.files && event.target.files[0]) {
          uploadFileToServer(event.target.files[0]);
        }
      };
      fileInput.click();
      return;
    }

    if (file) {
      uploadFileToServer(file);
    }
  };

  const uploadFileToServer = async (file) => {
    const docId = Date.now();
    const newDoc = {
      id: docId,
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
      chunks: 0,
      date: 'امروز',
      status: 'processing',
      progress: 15,
      ext: file.name.split('.').pop().toUpperCase().substring(0, 3)
    };
    setDocuments(prev => [newDoc, ...prev]);

    // میکروانیمیشن پیشرفت نوار بارگذاری
    const progressInterval = setInterval(() => {
      setDocuments(prev => prev.map(d => {
        if (d.id === docId && d.progress < 85) return { ...d, progress: d.progress + 15 };
        return d;
      }));
    }, 250);

    try {
      let data;
      if (MOCK_MODE) {
        // --- حالت Mock: شبیه‌سازی پردازش و نمایش نمونه PII ---
        await mockDelay(1800);
        const mockChunks = Math.floor(Math.random() * 400) + 80;
        data = {
          status: 'success',
          chunks_indexed: mockChunks,
          pii_preview:
            `نام فایل: ${file.name}\n\n` +
            'متن نمونه پس از اعمال قفل حریم شخصی:\n\n' +
            'کارمند گرامی،\n' +
            'کد ملی [شناسه ملی سانسور شده] شما در سامانه ثبت شده است.\n' +
            'لطفاً با شماره [شماره تلفن سانسور شده] تماس بگیرید.\n' +
            'حساب بانکی [شماره کارت سانسور شده] تأیید گردید.\n' +
            `\nمجموع ${mockChunks} قطعه متنی استخراج و ایندکس شد.`,
          pii_audit_counts: {
            national_id: 1,
            phone: 1,
            card: 1,
            email: 0,
            iban: 0
          }
        };
        console.info('[MOCK] File upload simulated:', file.name, '→', mockChunks, 'chunks');
      } else {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('http://localhost:8000/v1/upload', { method: 'POST', body: formData });
        data = await res.json();
        if (data.status !== 'success') throw new Error(data.detail || 'Upload failed');
      }

      clearInterval(progressInterval);
      setDocuments(prev => prev.map(d =>
        d.id === docId ? { ...d, status: 'ready', progress: 100, chunks: data.chunks_indexed } : d
      ));
      setPiiPreview(data.pii_preview || 'پیش‌نمایش ماسک برای این قالب فایل در دسترس نیست، اما سند با موفقیت ایندکس گردید.');
      setPiiAuditCounts(data.pii_audit_counts || {});

    } catch (err) {
      clearInterval(progressInterval);
      console.error('Smart file ingestion upload failed:', err);
      setDocuments(prev => prev.map(d =>
        d.id === docId ? { ...d, status: 'error', progress: 0, name: '⚠️ خطا: ' + d.name } : d
      ));
      setPiiPreview('خطا در پردازش سند.');
      setPiiAuditCounts({});
    }
  };

  return (
    <div className="device-frame fade-in">
      
      {/* سایدبار سمت راست اصلی داشبورد */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <svg className="logo-mark" viewBox="0 0 32 32" fill="none" width="32" height="32">
            <polygon points="16,2 28,26 4,26" fill="none" stroke="#c4894a" strokeWidth="2.5"/>
            <polygon points="16,9 22,26 10,26" fill="none" stroke="#c4894a" strokeWidth="1.5" opacity="0.5"/>
          </svg>
          <span className="logo-text">آریو<span>نکس</span></span>
        </div>

        {/* بخش منوی فضای کاری کاربری */}
        <div className="sidebar-section">
          <div className="sidebar-label">فضای کاری</div>
          <div 
            className={`nav-item ${activeScreen === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveScreen('dashboard')}
          >
            <span>📊</span> داشبورد
          </div>
          <div 
            className={`nav-item ${activeScreen === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveScreen('chat')}
          >
            <span>🤖</span> دستیار هوش مصنوعی
            <span className="nav-badge">3</span>
          </div>
          <div 
            className={`nav-item ${activeScreen === 'knowledge' ? 'active' : ''}`}
            onClick={() => setActiveScreen('knowledge')}
          >
            <span>📚</span> پایگاه دانش
          </div>
          <div 
            className={`nav-item ${activeScreen === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveScreen('upload')}
          >
            <span>📥</span> آپلود اسناد
          </div>
        </div>

        {/* بخش منوی مدیریتی ادمین */}
        <div className="sidebar-section">
          <div className="sidebar-label">مدیریت سیستم</div>
          <div 
            className={`nav-item ${activeScreen === 'admin' ? 'active' : ''}`}
            onClick={() => setActiveScreen('admin')}
          >
            <span>⚙️</span> پنل مدیریت
          </div>
          <div 
            className={`nav-item ${activeScreen === 'integrations' ? 'active' : ''}`}
            onClick={() => setActiveScreen('integrations')}
          >
            <span>🔗</span> یکپارچه‌سازی
            <span className="nav-badge" style={{background: 'var(--navy-light)'}}>3</span>
          </div>
        </div>

        {/* پروفایل کاربر در پایین سایدبار */}
        <div className="sidebar-bottom">
          <div className="user-card">
            <div className="user-avatar">AK</div>
            <div className="user-info">
              <div className="user-name">علی کریمی</div>
              <div className="user-role">مدیر ارشد سازمان</div>
            </div>
          </div>
        </div>
      </div>

      {/* بدنه اصلی محتوای صفحه فعال */}
      <div className="main">
        <div className="topbar">
          <div className="page-title">
            {activeScreen === 'dashboard' && 'داشبورد اصلی آریونکس'}
            {activeScreen === 'chat' && 'دستیار دانش هوشمند (حالت RAG امن)'}
            {activeScreen === 'knowledge' && 'مدیریت و توزیع منابع دانش'}
            {activeScreen === 'upload' && 'آپلود اسناد سازمانی و فیلتر حریم خصوصی'}
            {activeScreen === 'admin' && 'کنسول مدیریت حریم خصوصی و امنیت'}
            {activeScreen === 'integrations' && 'کانال‌های خروجی و مستندات اتصال'}
          </div>
          
          <div className="topbar-search">
            <span className="search-icon">🔍</span>
            <span className="search-placeholder">جستجو در پایگاه دانش…</span>
          </div>

          <button className="topbar-btn btn-ghost" onClick={() => setActiveScreen('chat')}>
            <span>+</span> پرسش جدید
          </button>
          
          <button className="topbar-btn btn-primary" onClick={() => setActiveScreen('upload')}>
            <span>↑</span> آپلود سریع
          </button>

          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-success)',
            border: '2px solid #e8f5e9',
            boxShadow: '0 0 8px rgba(46, 125, 50, 0.4)'
          }} title="سیستم آنلاین"></div>
        </div>

        {/* صفحه داشبورد اصلی */}
        {activeScreen === 'dashboard' && (
          <div className="screen fade-in">
            <div className="stats-row">
              <div className="stat-card stat-accent">
                <div className="stat-label">اسناد ایندکس‌شده</div>
                <div className="stat-value">{documents.length + 1204}</div>
                <div className="stat-change stat-up">↑ ۱۴ اسناد جدید این هفته</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">پرسش‌های امروز</div>
                <div className="stat-value">384</div>
                <div className="stat-change stat-up">↑ ۱۲٪ نسبت به دیروز</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">میانگین زمان پاسخ RAG</div>
                <div className="stat-value">1.4s</div>
                <div className="stat-change" style={{color: 'var(--text-muted)'}}>پایدار و ایمن</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">پوشش اطلاعات شخصی (PII)</div>
                <div className="stat-value">91 مورد</div>
                <div className="stat-change stat-up">↑ ۸ ماسک موفق امروز</div>
              </div>
            </div>

            <div className="two-col">
              <div>
                {/* وضعیت پایپ لاین زنده پردازش */}
                <div className="card">
                  <div className="card-title">
                    وضعیت زنده خط پردازش اسناد (Pipeline Progress)
                    <div style={{display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-success)', fontWeight: 'normal'}}>
                      <div className="pulse" style={{width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-success)'}}></div> زنده
                    </div>
                  </div>
                  
                  <div className="pipeline">
                    <div className="pipe-step">
                      <div className="pipe-node pipe-done">📥<div className="pipe-check">✓</div></div>
                      <div className="pipe-label">دریافت منبع</div>
                    </div>
                    <div className="pipe-arrow">←</div>
                    <div className="pipe-step">
                      <div className="pipe-node pipe-done">🔒<div className="pipe-check">✓</div></div>
                      <div className="pipe-label">ایرلاک حریم خصوصی</div>
                    </div>
                    <div className="pipe-arrow">←</div>
                    <div className="pipe-step">
                      <div className="pipe-node pipe-active">⚙️</div>
                      <div className="pipe-label" style={{color: 'var(--copper-dark)', fontWeight: 'bold'}}>تقطیع و پردازش</div>
                    </div>
                    <div className="pipe-arrow">←</div>
                    <div className="pipe-step">
                      <div className="pipe-node pipe-idle">🗄</div>
                      <div className="pipe-label">ذخیره برداری</div>
                    </div>
                    <div className="pipe-arrow">←</div>
                    <div className="pipe-step">
                      <div className="pipe-node pipe-idle">✅</div>
                      <div className="pipe-label">آماده بهره‌برداری</div>
                    </div>
                  </div>

                  <div style={{background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-secondary)'}}>
                    <strong style={{color: 'var(--text-primary)'}}>در حال پردازش:</strong> Q3_Financial_Report.pdf — قطعه ۴۷ از ۱۲۰ (۳۹٪ پیشرفت)
                    <div style={{marginTop: '10px', background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                      <div style={{width: '39%', height: '100%', background: 'linear-gradient(90deg, var(--copper), var(--copper-light))', borderRadius: '4px'}}></div>
                    </div>
                  </div>
                </div>

                {/* پرسش‌های اخیر */}
                <div className="card">
                  <div className="card-title">آخرین پرسش‌های اعضای سازمان <span className="card-link" onClick={() => setActiveScreen('chat')}>مشاهده همه چت‌ها →</span></div>
                  <div className="query-row">
                    <div className="query-dot q-green"></div>
                    <div className="q-text">حاشیه سود ناخالص خط محصول B در Q2 چقدر بود؟</div>
                    <span className="q-badge qb-done">پاسخ داده شد</span>
                  </div>
                  <div className="query-row">
                    <div className="query-dot q-green"></div>
                    <div className="q-text">خلاصه اسناد HR مربوط به مرخصی‌های زایمان جدید</div>
                    <span className="q-badge qb-done">پاسخ داده شد</span>
                  </div>
                  <div className="query-row">
                    <div className="query-dot q-amber"></div>
                    <div className="q-text">استخراج بندهای حقوقی از contract_draft_v3.pdf</div>
                    <span className="q-badge qb-proc">در پردازش RAG</span>
                  </div>
                  <div className="query-row">
                    <div className="query-dot q-green"></div>
                    <div className="q-text">مسئول انطباق بر اساس چارت سازمانی مصوب کیست؟</div>
                    <span className="q-badge qb-done">پاسخ داده شد</span>
                  </div>
                </div>
              </div>

              {/* سایدبار سمت چپ اطلاعات پایگاه دانش */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                <div className="card">
                  <div className="card-title">توزیع منابع دانش سازمان</div>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px'}}>
                    <div>
                      <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                        <span style={{color: 'var(--text-secondary)'}}>اسناد PDF</span>
                        <strong style={{color: 'var(--text-primary)'}}>1,204 سند</strong>
                      </div>
                      <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                        <div style={{width: '72%', height: '100%', background: 'var(--navy)', borderRadius: '4px'}}></div>
                      </div>
                    </div>
                    <div>
                      <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                        <span style={{color: 'var(--text-secondary)'}}>صفحات مالی و CSV</span>
                        <strong style={{color: 'var(--text-primary)'}}>387 فایل</strong>
                      </div>
                      <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                        <div style={{width: '42%', height: '100%', background: 'var(--copper)', borderRadius: '4px'}}></div>
                      </div>
                    </div>
                    <div>
                      <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                        <span style={{color: 'var(--text-secondary)'}}>لاگ‌های پشتیبانی سازمان</span>
                        <strong style={{color: 'var(--text-primary)'}}>918 لاگ</strong>
                      </div>
                      <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                        <div style={{width: '58%', height: '100%', background: 'var(--color-info)', borderRadius: '4px'}}></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-title">فعالیت‌های زنده حریم خصوصی</div>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
                    <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start', fontSize: '12.5px'}}>
                      <span style={{color: 'var(--color-success)', background: 'var(--color-success-bg)', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold'}}>✓</span>
                      <div>
                        <div style={{color: 'var(--text-primary)', fontWeight: '600'}}>قفل حریم خصوصی فعال</div>
                        <div style={{color: 'var(--text-secondary)', marginTop: '2px'}}>۳ کدملی از فایل legal_doc_091.pdf پوشش داده شد.</div>
                        <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>۲ دقیقه پیش</div>
                      </div>
                    </div>
                    <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start', fontSize: '12.5px'}}>
                      <span style={{color: 'var(--color-info)', background: 'var(--color-info-bg)', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold'}}>↑</span>
                      <div>
                        <div style={{color: 'var(--text-primary)', fontWeight: '600'}}>آپلود سند جدید</div>
                        <div style={{color: 'var(--text-secondary)', marginTop: '2px'}}>سعید م. ۴ قرارداد جدید تأمین‌کنندگان را آپلود نمود.</div>
                        <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>۱۴ دقیقه پیش</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* صفحه چت هوشمند دستیار */}
        {activeScreen === 'chat' && (
          <div className="screen fade-in" style={{padding: '16px'}}>
            <div className="chat-layout" style={{height: 'calc(800px - 100px)'}}>
              
              {/* لیست تاریخچه جلسات چت */}
              <div className="chat-sidebar">
                <button className="topbar-btn btn-primary" style={{width: '100%', justifyContent: 'center', gap: '8px'}} onClick={() => {
                  setChatMessages([{
                    id: Date.now(),
                    sender: 'ai',
                    text: 'مکالمه جدید شروع شد. چطور می‌توانم کمک کنم؟',
                    isSafe: true,
                    sources: []
                  }]);
                }}>
                  + مکالمه جدید
                </button>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', fontWeight: '700', marginTop: '10px', padding: '0 4px'}}>مکالمات اخیر</div>
                
                <div className="chat-history-item active-chat">
                  <div className="chi-title">تحلیل سود خالص Q2</div>
                  <div className="chi-sub">۴ پیام · ۸ دقیقه پیش</div>
                </div>
                <div className="chat-history-item">
                  <div className="chi-title">سیاست مرخصی کارمندان</div>
                  <div className="chi-sub">۲ پیام · ۲ ساعت پیش</div>
                </div>
                <div className="chat-history-item">
                  <div className="chi-title">بندهای فسخ قرارداد Q3</div>
                  <div className="chi-sub">۷ پیام · دیروز</div>
                </div>
              </div>

              {/* پنجره چت اصلی */}
              <div className="chat-main">
                <div className="chat-header">
                  <div className="chat-header-icon">🤖</div>
                  <div style={{flex: 1}}>
                    <div style={{fontWeight: '700', fontSize: '14.5px', color: 'var(--navy)'}}>دستیار هوش سازمانی آریونکس</div>
                    <div style={{fontSize: '11.5px', color: 'var(--color-success)', fontWeight: '600'}}>● آنلاین · RAG فعال و امن</div>
                  </div>
                  <div style={{display: 'flex', gap: '8px'}}>
                    <span className="q-badge qb-done" style={{fontSize: '12px'}}>مخزن متصل</span>
                  </div>
                </div>

                {/* نمایش لیست پیام‌ها */}
                <div className="chat-messages">
                  {chatMessages.map(msg => (
                    <div key={msg.id} className={`msg ${msg.sender === 'user' ? 'msg-user' : 'msg-ai'}`}>
                      <div className={`msg-avatar ${msg.sender === 'user' ? 'user-av' : 'ai-av'}`}>
                        {msg.sender === 'user' ? 'AK' : 'AN'}
                      </div>
                      
                      <div>
                        {msg.sender === 'ai' && (
                          <div className="safety-tag">
                            <span>🔒</span> {msg.isRefusal ? 'حفاظت عدم توهم فعال' : 'پاسخ معتبر RAG · تأیید شده توسط مخزن دانش'}
                          </div>
                        )}
                        
                        <div className={`msg-bubble ${msg.sender === 'user' ? 'user-bubble' : 'ai-bubble'}`} style={{whiteSpace: 'pre-line'}}>
                          {msg.text}
                        </div>

                        {/* نمایش استناد به منابع در چت */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="source-tags">
                            {msg.sources.map((src, i) => (
                              <span key={i} className="source-tag">
                                📄 {src.name} · {src.page}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  
                  {isAiLoading && (
                    <div className="msg msg-ai">
                      <div className="msg-avatar ai-av">AN</div>
                      <div>
                        <div className="ai-bubble pulse" style={{padding: '12px 24px'}}>
                          در حال بررسی و بازیابی پاسخ امن از پایگاه اسناد آریونکس...
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* فیلد ارسال پیام چت */}
                <div className="chat-input-area">
                  <textarea 
                    className="chat-input-box" 
                    placeholder="هر چیزی درباره اسناد خود بپرسید..." 
                    rows="1"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                  />
                  <button className="send-btn" onClick={handleSendMessage}>
                    ↑
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* صفحه کل پایگاه دانش */}
        {activeScreen === 'knowledge' && (
          <div className="screen fade-in">
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px'}}>
              <div className="card" style={{borderRight: '4px solid var(--navy)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>تعداد کل قطعات و بردارها (Chunks)</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>48,291 قطعه</div>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>مستقر در افزونه PostgreSQL pgvector</div>
              </div>
              <div className="card" style={{borderRight: '4px solid var(--copper)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>حد آستانه شباهت بازیابی (Threshold)</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>0.75 Cosine</div>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>قابل تنظیم جهت ممانعت از توهم و ورود داده کاذب</div>
              </div>
              <div className="card" style={{borderRight: '4px solid var(--color-success)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>حجم دیسک اشغال شده</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>14.2 GB</div>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>فضای اختصاص یافته آبجکت استوریج MinIO</div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">
                لیست اسناد و دیتای متصل به پایگاه دانش
                <span className="card-link" onClick={() => setActiveScreen('upload')}>+ افزودن فایل جدید</span>
              </div>
              
              <div className="files-table">
                <div className="ft-header">
                  <div>نام سند</div>
                  <div>حجم فیزیکی</div>
                  <div>تعداد چانک‌ها</div>
                  <div>تاریخ پردازش</div>
                  <div>وضعیت برداری</div>
                </div>
                
                {documents.map(doc => (
                  <div key={doc.id} className="ft-row">
                    <div className="ft-filename">
                      <span className={`ft-ext ext-${doc.ext.toLowerCase()}`}>{doc.ext}</span>
                      {doc.name}
                    </div>
                    <div style={{color: 'var(--text-secondary)'}}>{doc.size}</div>
                    <div style={{color: 'var(--text-secondary)'}}>{doc.chunks > 0 ? doc.chunks : '—'}</div>
                    <div style={{color: 'var(--text-muted)'}}>{doc.date}</div>
                    <div>
                      {doc.status === 'ready' ? (
                        <span className="q-badge qb-done">✓ ایندکس شده</span>
                      ) : (
                        <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                          <div className="prog-bar-wrap">
                            <div className="prog-bar" style={{width: `${doc.progress}%`}}></div>
                          </div>
                          <span style={{fontSize: '11px', color: 'var(--copper-dark)', fontWeight: 'bold'}}>{doc.progress}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* صفحه آپلود فایل و ایرلاک حریم خصوصی */}
        {activeScreen === 'upload' && (
          <div className="screen fade-in">
            <div className="upload-zone" onDragOver={(e) => e.preventDefault()} onDrop={handleFileUpload}>
              <div className="upload-icon">📂</div>
              <div className="upload-title">اسناد سازمان را به اینجا بکشید یا برای انتخاب کلیک کنید</div>
              <div className="upload-sub">
                اسناد پیش از تحلیل و ذخیره‌سازی، به صورت خودکار از سیستم امنیتی «قفل حریم خصوصی آریونکس» عبور کرده و تمامی کدهای ملی، شماره‌های تلفن، شماره حساب‌های مالی و نام‌های خاص بدون خروج از زیرساخت ماسک می‌شوند.
              </div>
              
              <div className="file-type-pills">
                <span className="file-pill">PDF Document</span>
                <span className="file-pill">Microsoft Word (DOCX)</span>
                <span className="file-pill">Excel / CSV Spreadsheet</span>
                <span className="file-pill">JSON / SQL Dumps</span>
                <span className="file-pill">Plain Text (TXT)</span>
              </div>

              <button className="topbar-btn btn-primary" style={{marginTop: '20px'}} onClick={() => {
                const fakeEvent = { preventDefault: () => {} };
                handleFileUpload(fakeEvent);
              }}>
                انتخاب اسناد از سیستم
              </button>
            </div>

            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
              <div className="card">
                <div className="card-title">صف نوبت‌دهی پردازش اسناد (Ingestion Queue)</div>
                <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
                  <div style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '12px'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px', fontWeight: 'bold'}}>
                      <span>Q3_Financial_Report.pdf</span>
                      <span style={{color: 'var(--text-muted)'}}>۲.۹ MB · چانک‌سازی...</span>
                    </div>
                    <div className="prog-bar-wrap" style={{width: '100%'}}>
                      <div className="prog-bar" style={{width: '39%'}}></div>
                    </div>
                  </div>
                  <div style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '12px'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px', fontWeight: 'bold'}}>
                      <span>HR_Policy_Manual_v2.docx</span>
                      <span style={{color: 'var(--text-muted)'}}>۱.۸ MB · بررسی حریم شخصی...</span>
                    </div>
                    <div className="prog-bar-wrap" style={{width: '100%'}}>
                      <div className="prog-bar" style={{width: '62%'}}></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-title">
                  🔒 پیش‌نمایش قفل حریم خصوصی (PII Masking Preview)
                  <span className="q-badge qb-done">قفل حریم شخصی فعال</span>
                </div>
                <div style={{fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '12px'}}>پیش‌نمایش زنده و هوشمند اقلام ماسک‌شده:</div>
                
                <div className="pii-demo" style={{whiteSpace: 'pre-wrap'}}>
                  {piiPreview ? (
                    piiPreview
                  ) : (
                    <span>
                      کارمند سازمان به شماره پرسنلی ۶۷۴۳ با <span className="pii-redact">کد ملی ۲۹۸۰۳****۱</span> بررسی پرونده گردید. جهت هماهنگی‌های لازم با شماره <span className="pii-redact">تلفن همراه ۰۹۱۲***۴۵۶۷</span> یا ایمیل رسمی ایشان به آدرس <span className="pii-redact">ایمیل ali***@organization.ir</span> ارتباط برقرار فرمایید.
                      پرداختی‌های حقوق ایشان به شماره <span className="pii-redact">حساب بانکی IR۷۶۰۱۲****************</span> واریز خواهد شد.
                    </span>
                  )}
                </div>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px'}}>
                  {Object.keys(piiAuditCounts).length > 0 ? (
                    <span>
                      اقلام حساس فیلتر شده در آخرین فایل: {
                        Object.entries(piiAuditCounts)
                          .map(([k, v]) => `${k === 'national_id' ? 'کد ملی' : k === 'phone_number' ? 'تلفن همراه' : k === 'email' ? 'ایمیل' : k === 'card_number' ? 'کارت بانکی' : 'شبا'}: ${v} مورد`)
                          .join(' | ')
                      }
                    </span>
                  ) : (
                    "پیش‌نمایش زنده اقلام حساس شامل کد ملی، تلفن همراه، ایمیل، کارت بانکی و شبا پیش از ایندکس در پایگاه دانش."
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* صفحه پنل مدیریتی ادمین */}
        {activeScreen === 'admin' && (
          <div className="screen fade-in">
            <div className="admin-grid">
              
              {/* بخش اول: امنیت و حریم خصوصی */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>🔒</span> کنترل‌های حریم خصوصی و امنیت داده‌ها
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">پوشش خودکار اطلاعات حساس شخصی (PII Redaction)</span>
                  <div 
                    className={`toggle ${features.piiRedaction ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('piiRedaction')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">بازرس ایمنی داده‌ها (مدل محلی Gemma-2b)</span>
                  <div 
                    className={`toggle ${features.localGemma ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('localGemma')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">محافظت هوشمند در برابر توهم‌پردازی (Hallucination Guard)</span>
                  <div 
                    className={`toggle ${features.hallucinationGuard ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('hallucinationGuard')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">مسدودسازی فراخوانی‌های API خارجی مدل‌ها</span>
                  <div 
                    className={`toggle ${features.externalApiBlocked ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('externalApiBlocked')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">الزام به استناد دقیق به خط و شماره صفحه منبع</span>
                  <div 
                    className={`toggle ${features.strictCitation ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('strictCitation')}
                  />
                </div>
              </div>

              {/* بخش دوم: لیست مدیران و دسترسی‌ها */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>👥</span> دسترسی کاربران و مدیریت مجوزها
                </div>
                
                <div className="permission-row">
                  <div className="perm-user"><div className="perm-av">AK</div> علی کریمی</div>
                  <span className="perm-badge p-admin">مدیر ارشد سازمان</span>
                </div>
                <div className="permission-row">
                  <div className="perm-user"><div className="perm-av" style={{background: 'var(--color-info)'}}>SM</div> سعید محمدی</div>
                  <span className="perm-badge p-admin">مدیر سیستم</span>
                </div>
                <div className="permission-row">
                  <div className="perm-user"><div className="perm-av" style={{background: 'var(--color-success)'}}>RH</div> رضا حسینی</div>
                  <span className="perm-badge p-analyst">تحلیلگر مالی</span>
                </div>
                <div className="permission-row">
                  <div className="perm-user"><div className="perm-av" style={{background: 'var(--gray-600)'}}>MA</div> مهدی احمدی</div>
                  <span className="perm-badge p-viewer">کاربر بیننده</span>
                </div>

                <button className="topbar-btn btn-ghost" style={{width: '100%', justifyContent: 'center', marginTop: '16px'}}>
                  + دعوت کاربر جدید به سازمان
                </button>
              </div>

              {/* بخش سوم: مدیریت دستورالعمل‌های پایه هوش */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>⚙️</span> مدیریت دستورالعمل پایه دستیار (System Instruction)
                </div>
                <div style={{fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '10px'}}>تعیین لحن، محدودیت‌ها و دستورات پایه برای مدل در تعامل با کاربران:</div>
                <textarea 
                  className="chat-input-box" 
                  style={{width: '100%', minHeight: '100px', fontSize: '13px', direction: 'rtl'}}
                  value={systemInstruction}
                  onChange={(e) => setSystemInstruction(e.target.value)}
                />
                <div style={{display: 'flex', gap: '10px', marginTop: '12px'}}>
                  <button className="topbar-btn btn-primary" style={{flex: 1, justifyContent: 'center'}}>ذخیره دستورالعمل جدید</button>
                  <button className="topbar-btn btn-ghost" style={{flex: 1, justifyContent: 'center'}} onClick={() => setSystemInstruction('شما یک دستیار دانش حرفه‌ای برای آریونکس هستید...')}>بازنشانی به پیش‌فرض</button>
                </div>
              </div>

              {/* بخش چهارم: کانال‌های خروجی فعال */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>📊</span> کانال‌های خروجی و دسترسی‌های فعال (Omni-Channels)
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">ربات تلگرام سازمانی (Telegram Bot Integration)</span>
                  <div 
                    className={`toggle ${features.telegramBot ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('telegramBot')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">ابزارک پاپ‌آپ وب‌سایت‌ها (Website Pop-up Widget)</span>
                  <div 
                    className={`toggle ${features.popupWidget ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('popupWidget')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">دسترسی از طریق وب‌سرویس REST API</span>
                  <div 
                    className={`toggle ${features.restApi ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleFeature('restApi')}
                  />
                </div>
              </div>

            </div>
          </div>
        )}

        {/* صفحه اتصالات و مستندات API */}
        {activeScreen === 'integrations' && (
          <div className="screen fade-in">
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px'}}>
              <div className="card" style={{borderTop: '3px solid var(--color-success)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>کانال‌های متصل شده</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>۳ درگاه فعال</div>
                <div style={{fontSize: '11.5px', color: 'var(--color-success)', marginTop: '4px'}}>REST, Widget, Telegram</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--color-info)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>مجموع درخواست‌ها از خارج</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>42,891 بار</div>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>از زمان راه‌اندازی سیستم</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--copper)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>میانگین لتنسی کانال‌ها</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>0.2s</div>
                <div style={{fontSize: '11.5px', color: 'var(--color-success)', marginTop: '4px'}}>سرعت تبادل فوق‌العاده بالا</div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">۱. اتصال از طریق REST API تجاری</div>
              <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '12px'}}>
                شما می‌توانید پرسش‌های سازمانی را از تمام نرم‌افزارهای حسابداری، اتوماسیون اداری و CRMهای متفرقه خود با ارسال متدهای استاندارد POST به آدرس زیر استخراج کنید:
              </div>
              <div style={{background: 'var(--navy-deep)', padding: '12px 16px', borderRadius: 'var(--radius)', color: 'white', marginBottom: '16px'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '6px', fontFamily: 'monospace'}}>ENDPOINT URL (POST)</div>
                <code style={{color: 'var(--copper-light)', fontSize: '12px'}}>https://api.arionex.io/v1/query</code>
              </div>
            </div>

            <div className="card">
              <div className="card-title">۲. ابزارک چت پاپ‌آپ اختصاصی (Website Pop-up Widget)</div>
              <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '12px'}}>
                برای قرار دادن دکمه شناور چت هوشمند در گوشه وب‌سایت‌های پورتال کارمندان یا سایت رسمی سازمان خود، کافی است کدهای اسکریپت جاوااسکریپت زیر را کپی کرده و در انتهای تگ <code>&lt;body&gt;</code> قالب سایت خود قرار دهید:
              </div>
              <div style={{background: 'var(--navy-deep)', padding: '12px 16px', borderRadius: 'var(--radius)', color: 'white'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '6px', fontFamily: 'monospace'}}>EMBEDDED JAVASCRIPT CODE</div>
                <pre style={{
                  color: '#a5d6a7',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  direction: 'ltr',
                  textAlign: 'left',
                  overflowX: 'auto',
                  whiteSpace: 'pre'
                }}>
{`<!-- ArioNex Floating Assistant Popup Widget -->
<script src="https://widget.arionex.io/v1/widget.js" async></script>
<script>
  window.addEventListener('DOMContentLoaded', () => {
    ArioNexWidget.init({
      appId: "anx_org_881",
      themeColor: "#1a2744",
      accentColor: "#c4894a",
      welcomeMessage: "چطور می‌توانم به شما کمک کنم؟"
    });
  });
</script>`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* برچسب اصالت و برندینگ در گوشه داشبورد */}
        <div className="wf-tag">ArioNex Commercial AI — v1.0.0</div>
      </div>
    </div>
  );
}
