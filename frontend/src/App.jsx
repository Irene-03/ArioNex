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
const MOCK_MODE = false;

/** شبیه‌سازی تاخیر شبکه (میلی‌ثانیه) */
const mockDelay = (ms = 600) => new Promise(resolve => setTimeout(resolve, ms));

/** داده‌های تنظیمات Mock */
const MOCK_CONFIG = {
  security: { pii_redaction: true, strict_non_hallucination: true },
  services: { safety_auditor: false, log_processor: true, web_search: false },
  integrations: { telegram_bot: true, popup_widget: true, rest_api: true }
};

/** پاسخ‌های نمونه برای چت Mock */
const MOCK_ANSWERS = [];
let _mockAnswerIdx = 0;

/** نگاشت کلیدهای PII بک‌اند به برچسب فارسی */
const PII_KEY_LABELS = {
  national_id: 'کد ملی',
  phone_number: 'تلفن همراه',
  phone: 'تلفن همراه',
  email: 'ایمیل',
  card_number: 'کارت بانکی',
  card: 'کارت بانکی',
  iban: 'شبا',
  bank_account: 'حساب بانکی',
};

/** مدل‌های Ollama موجود */
const OLLAMA_MODELS = [
  { id: 'gemma3:4b', label: 'Gemma 3 4B (سریع)' },
  { id: 'gemma3:12b', label: 'Gemma 3 12B (دقیق‌تر)' },
  { id: 'gemma2:2b', label: 'Gemma 2 2B (سبک‌ترین)' },
  { id: 'llama3.2:3b', label: 'Llama 3.2 3B' },
  { id: 'qwen2.5:3b', label: 'Qwen 2.5 3B' },
];

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
    restApi: true,
    providerOpenAI: true,
    providerOpenRouter: true,
    providerAnthropic: true,
    providerGoogle: true,
    providerDeepSeek: true,
    providerGapGPT: true,
    providerAvalAI: true,
    providerHormouz: true
  });

  // لیست پیام‌های پنجره چت
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      text: 'سلام! من دستیار دانش امن شما (آریو) هستم. تمام پرسش‌ها روی داده‌های خصوصی شما اجرا می‌شوند — هیچ اطلاعاتی از زیرساخت شما خارج نمی‌شود. چطور می‌توانم کمک کنم؟',
      isSafe: true,
      isWelcome: true,
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

  // تنظیمات حالت محلی Ollama
  const [ollamaEnabled, setOllamaEnabled] = useState(false);
  const [ollamaModel, setOllamaModel] = useState('gemma3:4b');
  const [ollamaEndpoint, setOllamaEndpoint] = useState('http://localhost:11434');

  // لیست فایل‌های آپلود شده و وضعیت پردازش آن‌ها — خالی در ابتدا، از بک‌اند بارگذاری می‌شود
  const [documents, setDocuments] = useState([]);

  // متغیرهای وضعیت پیش‌نمایش قفل حریم شخصی PII
  const [piiPreview, setPiiPreview] = useState('');
  const [piiAuditCounts, setPiiAuditCounts] = useState({});

  // لیست ابزارک‌های سایت‌ها — از بک‌اند بارگذاری می‌شود
  const [widgets, setWidgets] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);

  // متغیرهای فرم
  const [newWidgetName, setNewWidgetName] = useState('');
  const [newWidgetUrl, setNewWidgetUrl] = useState('');
  const [newWidgetMsg, setNewWidgetMsg] = useState('سلام! چطور می‌توانم کمک کنم؟ 💼✨');
  const [newWidgetTheme, setNewWidgetTheme] = useState('#1a2744');
  const [newWidgetAccent, setNewWidgetAccent] = useState('#c4894a');
  
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [widgetPreviewSelected, setWidgetPreviewSelected] = useState(null);

  // بارگذاری اولیه اسناد از بک‌اند
  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://localhost:8000/v1/knowledge/documents');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setDocuments(data);
      }
    } catch (err) {
      console.info('Documents endpoint not available yet:', err.message);
    }
  };

  const fetchIntegrations = async () => {
    if (MOCK_MODE) return;
    try {
      const resWidgets = await fetch('http://localhost:8000/v1/integrations/widgets');
      const dataWidgets = await resWidgets.json();
      setWidgets(dataWidgets);
      if (dataWidgets.length > 0 && !widgetPreviewSelected) {
        setWidgetPreviewSelected(dataWidgets[0]);
      } else if (dataWidgets.length === 0) {
        setWidgetPreviewSelected(null);
      }

      const resKeys = await fetch('http://localhost:8000/v1/integrations/apikeys');
      const dataKeys = await resKeys.json();
      setApiKeys(dataKeys);
    } catch (err) {
      console.error('Error fetching integrations:', err);
    }
  };

  useEffect(() => {
    fetchIntegrations();
    if (activeScreen === 'knowledge' || activeScreen === 'upload') {
      fetchDocuments();
    }
  }, [activeScreen]);

  const handleCreateWidget = async (e) => {
    e.preventDefault();
    if (!newWidgetName.trim() || !newWidgetUrl.trim()) return;

    const widgetData = {
      name: newWidgetName,
      url: newWidgetUrl,
      welcome_message: newWidgetMsg,
      theme_color: newWidgetTheme,
      accent_color: newWidgetAccent,
      is_active: true
    };

    try {
      if (MOCK_MODE) {
        const newW = { id: Date.now(), ...widgetData };
        setWidgets(prev => [newW, ...prev]);
        setWidgetPreviewSelected(newW);
      } else {
        const res = await fetch('http://localhost:8000/v1/integrations/widgets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(widgetData)
        });
        const data = await res.json();
        if (res.ok) {
          setWidgets(prev => [data, ...prev]);
          setWidgetPreviewSelected(data);
        } else {
          alert(data.detail || 'خطا در ثبت ابزارک');
        }
      }
      setNewWidgetName('');
      setNewWidgetUrl('');
    } catch (err) {
      console.error('Error creating widget:', err);
    }
  };

  const handleDeleteWidget = async (id) => {
    if (!confirm('آیا از حذف این ابزارک اطمینان دارید؟')) return;
    try {
      if (MOCK_MODE) {
        setWidgets(prev => prev.filter(w => w.id !== id));
        if (widgetPreviewSelected?.id === id) {
          setWidgetPreviewSelected(null);
        }
      } else {
        const res = await fetch(`http://localhost:8000/v1/integrations/widgets/${id}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          setWidgets(prev => prev.filter(w => w.id !== id));
          if (widgetPreviewSelected?.id === id) {
            setWidgetPreviewSelected(null);
          }
        }
      }
    } catch (err) {
      console.error('Error deleting widget:', err);
    }
  };

  const handleCreateAPIKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    try {
      if (MOCK_MODE) {
        const mockToken = 'anx_live_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        const newKey = {
          id: Date.now(),
          name: newKeyName,
          api_key: mockToken,
          is_active: true,
          created_at: new Date().toLocaleDateString('fa-IR'),
          last_used_at: '—'
        };
        setApiKeys(prev => [newKey, ...prev]);
        setGeneratedKey(mockToken);
      } else {
        const res = await fetch('http://localhost:8000/v1/integrations/apikeys', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newKeyName })
        });
        const data = await res.json();
        if (res.ok) {
          setApiKeys(prev => [data, ...prev]);
          setGeneratedKey(data.api_key);
        }
      }
      setNewKeyName('');
    } catch (err) {
      console.error('Error creating API key:', err);
    }
  };

  const handleDeleteAPIKey = async (id) => {
    if (!confirm('آیا از ابطال این کلید API اطمینان دارید؟')) return;
    try {
      if (MOCK_MODE) {
        setApiKeys(prev => prev.filter(k => k.id !== id));
      } else {
        const res = await fetch(`http://localhost:8000/v1/integrations/apikeys/${id}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          setApiKeys(prev => prev.filter(k => k.id !== id));
        }
      }
    } catch (err) {
      console.error('Error deleting API key:', err);
    }
  };

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
            restApi: data.integrations?.rest_api ?? true,
            providerOpenAI: data.providers?.openai ?? true,
            providerOpenRouter: data.providers?.openrouter ?? true,
            providerAnthropic: data.providers?.anthropic ?? true,
            providerGoogle: data.providers?.google ?? true,
            providerDeepSeek: data.providers?.deepseek ?? true,
            providerGapGPT: data.providers?.gapgpt ?? true,
            providerAvalAI: data.providers?.avalai ?? true,
            providerHormouz: data.providers?.hormouz ?? true,
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

  const toggleProvider = (providerKey) => {
    const keyMap = {
      openai: 'providerOpenAI',
      openrouter: 'providerOpenRouter',
      anthropic: 'providerAnthropic',
      google: 'providerGoogle',
      deepseek: 'providerDeepSeek',
      gapgpt: 'providerGapGPT',
      avalai: 'providerAvalAI',
      hormouz: 'providerHormouz',
    };
    const featureKey = keyMap[providerKey];
    if (!featureKey) return;

    const updatedFeatures = { ...features, [featureKey]: !features[featureKey] };
    setFeatures(updatedFeatures);

    if (MOCK_MODE) {
      console.info('[MOCK] Provider toggle updated locally:', providerKey, '->', !features[featureKey]);
      return;
    }

    fetch('http://localhost:8000/v1/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        providers: {
          openai: providerKey === 'openai' ? !features.providerOpenAI : features.providerOpenAI,
          openrouter: providerKey === 'openrouter' ? !features.providerOpenRouter : features.providerOpenRouter,
          anthropic: providerKey === 'anthropic' ? !features.providerAnthropic : features.providerAnthropic,
          google: providerKey === 'google' ? !features.providerGoogle : features.providerGoogle,
          deepseek: providerKey === 'deepseek' ? !features.providerDeepSeek : features.providerDeepSeek,
          gapgpt: providerKey === 'gapgpt' ? !features.providerGapGPT : features.providerGapGPT,
          avalai: providerKey === 'avalai' ? !features.providerAvalAI : features.providerAvalAI,
          hormouz: providerKey === 'hormouz' ? !features.providerHormouz : features.providerHormouz,
        }
      })
    })
    .then(res => res.json())
    .then(data => console.log('Provider toggles synchronized:', data))
    .catch(err => console.error('Failed to sync provider toggles:', err));
  };

  // ارسال پیام جدید به دستیار هوشمند و دریافت پاسخ به صورت Streaming (SSE)
  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = { id: Date.now(), sender: 'user', text: inputText, sources: [] };
    setChatMessages(prev => [...prev, userMessage]);
    const queryText = inputText;
    setInputText('');
    setIsAiLoading(true);

    if (MOCK_MODE) {
      // --- حالت Mock: شبیه‌سازی streaming توکن به توکن از پاسخ نمونه ---
      const mockData = MOCK_ANSWERS[_mockAnswerIdx % MOCK_ANSWERS.length];
      _mockAnswerIdx++;
      const aiMsgId = Date.now() + 1;
      const aiPlaceholder = {
        id: aiMsgId,
        sender: 'ai',
        text: '',
        sources: mockData.sources || [],
        isSafe: mockData.is_safe ?? true,
        isRefusal: mockData.answer === 'منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.'
      };
      setChatMessages(prev => [...prev, aiPlaceholder]);
      setIsAiLoading(false);

      const fullText = mockData.answer;
      let cursor = 0;
      await new Promise(resolve => {
        const interval = setInterval(() => {
          cursor += 3;
          const partial = fullText.slice(0, cursor);
          setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: partial } : m));
          if (cursor >= fullText.length) {
            clearInterval(interval);
            resolve();
          }
        }, 30);
      });
      console.info('[MOCK] Streamed mock answer #', _mockAnswerIdx);
      return;
    }

    // --- حالت واقعی: streaming SSE از /v1/query/stream ---
    const aiMsgId = Date.now() + 1;
    const aiPlaceholder = {
      id: aiMsgId,
      sender: 'ai',
      text: '',
      sources: [],
      isSafe: true,
      isRefusal: false,
    };
    setChatMessages(prev => [...prev, aiPlaceholder]);

    try {
      const res = await fetch('http://localhost:8000/v1/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, session_id: 'react_admin_dashboard_chat' })
      });

      if (!res.body) throw new Error('Streaming not supported by browser');

      setIsAiLoading(false);
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // پردازش هر بلوک کامل SSE که با \n\n جدا شده است
        let sepIdx;
        while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, sepIdx);
          buffer = buffer.slice(sepIdx + 2);

          let eventName = 'message';
          let dataLine = '';
          rawEvent.split('\n').forEach(line => {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLine += line.slice(5).trim();
          });

          // SSE-encoded newlines (\n)
          const decodedData = dataLine.replace(/\\n/g, '\n');

          if (eventName === 'token') {
            accumulated += decodedData;
            setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: accumulated } : m));
          } else if (eventName === 'sources') {
            try {
              const parsedSources = JSON.parse(decodedData);
              setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, sources: parsedSources } : m));
            } catch (_) { /* منابع نامعتبر — نادیده گرفته می‌شود */ }
          } else if (eventName === 'done') {
            try {
              const meta = JSON.parse(decodedData);
              const isRefusal = accumulated === 'منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.';
              setChatMessages(prev => prev.map(m => m.id === aiMsgId
                ? { ...m, isSafe: meta.is_safe ?? true, isRefusal }
                : m));
            } catch (_) { /* meta نامعتبر */ }
          } else if (eventName === 'error') {
            console.error('Stream RAG error:', decodedData);
          }
        }
      }
    } catch (err) {
      console.error('Error streaming from query API:', err);
      setIsAiLoading(false);
      setChatMessages(prev => prev.map(m => m.id === aiMsgId ? {
        ...m,
        text: '⚠️ خطا در برقراری ارتباط با وب‌سرور هوشمند آریونکس. لطفاً اطمینان حاصل فرمایید که بک‌اند بر روی پورت 8000 در حال اجراست.',
        isRefusal: true,
      } : m));
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
            <div className="chat-layout" style={{height: '100%', minHeight: 0}}>
              
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
                        {msg.sender === 'ai' && !msg.isWelcome && (
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
                          .filter(([, v]) => v > 0)
                          .map(([k, v]) => `${PII_KEY_LABELS[k] || k}: ${v} مورد`)
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

              {/* بخش پنجم: حالت محلی Ollama */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>🖥️</span> حالت محلی — Ollama (بدون نیاز به اینترنت)
                </div>
                <div style={{fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: '1.7'}}>
                  با فعال کردن این حالت، بک‌اند آریونکس از مدل زبانی محلی Ollama (مثل Gemma 3) به‌جای API خارجی استفاده می‌کند. مناسب برای محیط‌های کاملاً آفلاین و حریم‌خصوصی حداکثری.
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">فعال‌سازی حالت محلی Ollama</span>
                  <div
                    id="ollama-toggle"
                    className={`toggle ${ollamaEnabled ? 'toggle-on' : 'toggle-off'}`}
                    onClick={() => {
                      const next = !ollamaEnabled;
                      setOllamaEnabled(next);
                      if (!MOCK_MODE) {
                        fetch('http://localhost:8000/v1/config', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ providers: { ollama: next } })
                        }).catch(() => {});
                      }
                    }}
                  />
                </div>
                {ollamaEnabled && (
                  <div style={{marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '12px'}}>
                    <div>
                      <label style={{fontSize: '12.5px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>مدل زبانی محلی:</label>
                      <select
                        id="ollama-model-select"
                        value={ollamaModel}
                        onChange={(e) => {
                          setOllamaModel(e.target.value);
                          if (!MOCK_MODE) {
                            fetch('http://localhost:8000/v1/config', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ ollama_model: e.target.value })
                            }).catch(() => {});
                          }
                        }}
                        style={{width: '100%', padding: '8px 12px', border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', fontSize: '13px', background: 'var(--gray-50)', color: 'var(--text-primary)', fontFamily: 'inherit'}}
                      >
                        {OLLAMA_MODELS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                      </select>
                    </div>
                    <div>
                      <label style={{fontSize: '12.5px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>آدرس Ollama Server:</label>
                      <input
                        id="ollama-endpoint-input"
                        type="text"
                        className="chat-input-box"
                        style={{borderRadius: 'var(--radius)', fontSize: '13px', direction: 'ltr', width: '100%'}}
                        value={ollamaEndpoint}
                        onChange={(e) => setOllamaEndpoint(e.target.value)}
                        placeholder="http://localhost:11434"
                      />
                    </div>
                    <button
                      className="topbar-btn btn-primary"
                      style={{width: '100%', justifyContent: 'center'}}
                      onClick={async () => {
                        try {
                          const res = await fetch(`${ollamaEndpoint}/api/tags`, { signal: AbortSignal.timeout(3000) });
                          const data = await res.json();
                          const modelCount = data?.models?.length ?? 0;
                          alert(`✅ اتصال موفق! ${modelCount} مدل روی Ollama یافت شد.`);
                        } catch {
                          alert('❌ اتصال به Ollama ناموفق. مطمئن شوید سرویس در حال اجراست.');
                        }
                      }}
                    >
                      🔍 آزمون اتصال به Ollama
                    </button>
                    <div style={{background: 'var(--color-info-bg)', border: '1px solid rgba(21, 101, 192, 0.2)', borderRadius: 'var(--radius)', padding: '12px', fontSize: '12px', color: 'var(--color-info)', lineHeight: '1.8'}}>
                      <strong>راهنمای نصب Ollama:</strong><br/>
                      ۱. از <span style={{direction: 'ltr', display: 'inline'}}>ollama.com</span> نصب کنید<br/>
                      ۲. دستور <code style={{background: 'rgba(21,101,192,0.1)', padding: '1px 5px', borderRadius: '3px', direction: 'ltr'}}>ollama pull gemma3:4b</code> را اجرا کنید<br/>
                      ۳. این حالت را فعال کنید و «آزمون اتصال» بزنید
                    </div>
                  </div>
                )}
              </div>

              {/* بخش ششم: وضعیت پروایدرهای هوش مصنوعی فعال */}
              <div className="admin-card">
                <div className="admin-card-title">
                  <span>🧠</span> پروایدرهای هوش مصنوعی فعال (LLM Providers)
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">OpenAI direct (GPT-4o, GPT-4o-mini)</span>
                  <div 
                    className={`toggle ${features.providerOpenAI ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('openai')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">OpenRouter API (دسترسی تجاری متمرکز)</span>
                  <div 
                    className={`toggle ${features.providerOpenRouter ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('openrouter')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">DeepSeek API (مدل ارزان و قدرتمند)</span>
                  <div 
                    className={`toggle ${features.providerDeepSeek ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('deepseek')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">GapGPT API (پروایدر ایرانی بدون تحریم)</span>
                  <div 
                    className={`toggle ${features.providerGapGPT ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('gapgpt')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">AvalAI API (پروایدر ایرانی همکار)</span>
                  <div 
                    className={`toggle ${features.providerAvalAI ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('avalai')}
                  />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">Hormouz API (دروازه ۳۵۰+ مدل · streaming)</span>
                  <div 
                    className={`toggle ${features.providerHormouz ? 'toggle-on' : 'toggle-off'}`} 
                    onClick={() => toggleProvider('hormouz')}
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
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>کلیدهای فعال API</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>{apiKeys.length} عدد</div>
                <div style={{fontSize: '11.5px', color: 'var(--color-success)', marginTop: '4px'}}>جهت دسترسی به سیستم RAG خارج سازمان</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--color-info)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>ابزارک‌های وب‌سایت فعال</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>{widgets.length} وب‌سایت</div>
                <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>سرویس‌دهی پاپ‌آپ فعال روی دامنه‌ها</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--copper)'}}>
                <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>احراز هویت ادغام‌ها</div>
                <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>{features.restApi ? 'فعال و امن' : 'غیرفعال'}</div>
                <div style={{fontSize: '11.5px', color: 'var(--color-success)', marginTop: '4px'}}>کنترل شده توسط کنسول مدیریت</div>
              </div>
            </div>

            <div className="two-col">
              {/* بخش سمت راست: مدیریت کلیدهای API */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                <div className="card">
                  <div className="card-title">🔑 مدیریت کلیدهای دسترسی API (REST API Keys)</div>
                  <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '16px'}}>
                    کلیدهای دسترسی API جهت اتصال امن سیستم‌های خارجی نظیر CRM، پورتال‌های درون‌سازمانی و برنامه‌های اختصاصی به خط لوله پرسش‌و‌پاسخ RAG آریونکس استفاده می‌شوند.
                  </div>

                  {/* فرم ساخت کلید */}
                  <form onSubmit={handleCreateAPIKey} style={{display: 'flex', gap: '10px', marginBottom: '20px'}}>
                    <input
                      type="text"
                      className="chat-input-box"
                      style={{borderRadius: 'var(--radius)', flex: 1}}
                      placeholder="نام یا عنوان کلید جدید (مثلاً: CRM وب‌سایت)"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                    />
                    <button type="submit" className="topbar-btn btn-primary" style={{padding: '10px 20px'}}>
                      + ایجاد کلید جدید
                    </button>
                  </form>

                  {/* نمایش کلید تولید شده */}
                  {generatedKey && (
                    <div style={{background: 'rgba(255, 193, 7, 0.15)', border: '1px solid #ffc107', borderRadius: 'var(--radius)', padding: '14px', marginBottom: '20px', direction: 'rtl'}}>
                      <div style={{color: '#856404', fontWeight: 'bold', fontSize: '13.5px', marginBottom: '6px'}}>⚠️ کلید API با موفقیت تولید شد:</div>
                      <div style={{fontSize: '12px', color: '#666', marginBottom: '10px'}}>این کلید به دلایل امنیتی فقط همین یک بار به شما نمایش داده می‌شود. لطفاً آن را کپی کرده و در محل امنی ذخیره کنید.</div>
                      <div style={{display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', fontFamily: 'monospace', direction: 'ltr'}}>
                        <span style={{flex: 1, color: '#333', fontSize: '13px', overflowX: 'auto', whiteSpace: 'nowrap'}}>{generatedKey}</span>
                        <button 
                          onClick={() => {
                            navigator.clipboard.writeText(generatedKey);
                            alert('کلید API در حافظه کپی شد.');
                          }}
                          className="topbar-btn btn-ghost" 
                          style={{padding: '4px 10px', fontSize: '11px'}}
                        >
                          کپی کلید
                        </button>
                      </div>
                    </div>
                  )}

                  {/* جدول نمایش کلیدها */}
                  <div className="files-table" style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)'}}>
                    <div style={{display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', padding: '10px 14px', background: 'var(--gray-50)', fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', borderBottom: '1px solid var(--gray-100)'}}>
                      <div>نام کلید</div>
                      <div>کلید دسترسی (Masked)</div>
                      <div>تاریخ ایجاد</div>
                      <div>عملیات</div>
                    </div>
                    {apiKeys.length === 0 ? (
                      <div style={{padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px'}}>هیچ کلید API تعریف نشده است. کلیدها پیش از حذف شدن دسترسی آزاد را فراهم می‌کنند.</div>
                    ) : (
                      apiKeys.map(key => (
                        <div key={key.id} style={{display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', padding: '12px 14px', alignItems: 'center', borderBottom: '1px solid var(--gray-50)', fontSize: '12.5px'}}>
                          <div style={{fontWeight: '600', color: 'var(--text-primary)'}}>{key.name}</div>
                          <div style={{fontFamily: 'monospace', direction: 'ltr', color: 'var(--text-secondary)'}}>{key.api_key}</div>
                          <div style={{color: 'var(--text-muted)'}}>{key.created_at}</div>
                          <div>
                            <button 
                              onClick={() => handleDeleteAPIKey(key.id)}
                              style={{background: '#ffebee', color: '#c62828', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold'}}
                            >
                              ابطال کلید
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="card">
                  <div className="card-title">📖 مستندات اتصال و نمونه فراخوانی REST API</div>
                  <div style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px'}}>
                    برای ارسال پرسش‌های هوشمند RAG به سرور از خارج سیستم، درخواست خود را با هدر احراز هویت ارسال کنید:
                  </div>
                  <div style={{background: 'var(--navy-deep)', padding: '14px', borderRadius: 'var(--radius)', color: '#fff', fontSize: '12px', fontFamily: 'monospace', direction: 'ltr', textAlign: 'left', overflowX: 'auto'}}>
                    <pre style={{margin: 0}}>
{`curl -X POST "http://localhost:8000/v1/query" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: anx_live_YOUR_API_KEY_HERE" \\
  -d '{
    "query": "سود خالص شرکت در سال مالی گذشته چقدر بوده است؟",
    "session_id": "external_crm_user"
  }'`}
                    </pre>
                  </div>
                </div>
              </div>

              {/* بخش سمت چپ: ابزارک‌های وب‌سایت */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                <div className="card">
                  <div className="card-title">💬 مدیریت ابزارک چت پاپ‌آپ وب‌سایت‌ها (Web Popup Widget)</div>
                  <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '16px'}}>
                    با استفاده از ابزارک پاپ‌آپ، کاربران و کارمندان شما می‌توانند بدون نیاز به نصب هرگونه برنامه‌ای، مستقیماً به هوش مصنوعی سازمان بر روی هر وب‌سایتی دسترسی داشته باشند.
                  </div>

                  {/* فرم ساخت ابزارک */}
                  <form onSubmit={handleCreateWidget} style={{display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--gray-50)', padding: '16px', borderRadius: 'var(--radius)', border: '1px solid var(--gray-100)', marginBottom: '20px'}}>
                    <div style={{fontWeight: 'bold', fontSize: '13px', color: 'var(--navy)'}}>ثبت دامنه جدید برای قرار دادن پاپ‌آپ:</div>
                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px'}}>
                      <input
                        type="text"
                        className="chat-input-box"
                        style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px'}}
                        placeholder="عنوان سایت (مثلاً: پورتال پشتیبانی)"
                        value={newWidgetName}
                        onChange={(e) => setNewWidgetName(e.target.value)}
                      />
                      <input
                        type="text"
                        className="chat-input-box"
                        style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px'}}
                        placeholder="دامنه یا آدرس (مثلاً: support.company.ir)"
                        value={newWidgetUrl}
                        onChange={(e) => setNewWidgetUrl(e.target.value)}
                      />
                    </div>
                    <input
                      type="text"
                      className="chat-input-box"
                      style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px'}}
                      placeholder="پیام خوش‌آمدگویی پیش‌فرض ابزارک"
                      value={newWidgetMsg}
                      onChange={(e) => setNewWidgetMsg(e.target.value)}
                    />
                    
                    {/* انتخاب رنگ */}
                    <div style={{display: 'flex', gap: '15px', alignItems: 'center', fontSize: '12.5px', color: 'var(--text-secondary)'}}>
                      <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                        <span>رنگ اصلی تم:</span>
                        <input 
                          type="color" 
                          value={newWidgetTheme} 
                          onChange={(e) => setNewWidgetTheme(e.target.value)} 
                          style={{border: 'none', background: 'none', cursor: 'pointer', width: '28px', height: '28px'}}
                        />
                      </div>
                      <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                        <span>رنگ مسی ثانویه:</span>
                        <input 
                          type="color" 
                          value={newWidgetAccent} 
                          onChange={(e) => setNewWidgetAccent(e.target.value)} 
                          style={{border: 'none', background: 'none', cursor: 'pointer', width: '28px', height: '28px'}}
                        />
                      </div>
                    </div>

                    <button type="submit" className="topbar-btn btn-primary" style={{width: '100%', justifyContent: 'center', padding: '10px'}}>
                      + ثبت و تولید کد ابزارک وب‌سایت
                    </button>
                  </form>

                  {/* لیست ابزارک‌های ثبت شده */}
                  <div style={{fontWeight: 'bold', fontSize: '13px', color: 'var(--navy)', marginBottom: '10px'}}>وب‌سایت‌های متصل شده:</div>
                  <div className="files-table" style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', marginBottom: '20px'}}>
                    {widgets.length === 0 ? (
                      <div style={{padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px'}}>هیچ ابزارکی ثبت نشده است.</div>
                    ) : (
                      widgets.map(w => (
                        <div 
                          key={w.id} 
                          className={`ft-row ${widgetPreviewSelected?.id === w.id ? 'active-chat' : ''}`}
                          style={{display: 'flex', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid var(--gray-50)', cursor: 'pointer'}}
                          onClick={() => setWidgetPreviewSelected(w)}
                        >
                          <div>
                            <div style={{fontWeight: '600', color: 'var(--text-primary)'}}>{w.name}</div>
                            <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '2px'}}>{w.url}</div>
                          </div>
                          <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                            <span style={{width: '10px', height: '10px', borderRadius: '50%', background: w.theme_color}} title="رنگ تم"></span>
                            <span style={{width: '10px', height: '10px', borderRadius: '50%', background: w.accent_color}} title="رنگ ثانویه Accent"></span>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteWidget(w.id);
                              }}
                              style={{background: 'none', border: 'none', color: '#c62828', cursor: 'pointer', fontSize: '11px'}}
                            >
                              حذف
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* کد تولید شده برای ابزارک انتخاب شده */}
                  {widgetPreviewSelected && (
                    <div style={{background: 'rgba(26, 39, 68, 0.03)', border: '1px solid rgba(26, 39, 68, 0.08)', borderRadius: 'var(--radius)', padding: '14px', marginBottom: '20px'}}>
                      <div style={{fontWeight: 'bold', fontSize: '13px', color: 'var(--navy)', marginBottom: '8px'}}>📥 کد اسکریپت ابزارک برای سایت «{widgetPreviewSelected.name}»:</div>
                      <div style={{fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '10px'}}>
                        کافیست اسکریپت زیر را کپی کرده و در انتهای تگ <code>&lt;body&gt;</code> سایت خود قرار دهید. این اسکریپت به صورت خودکار تم انتخابی شما را لود می‌کند.
                      </div>
                      <div style={{background: 'var(--navy-deep)', padding: '12px', borderRadius: 'var(--radius)', color: '#fff', fontSize: '11.5px', fontFamily: 'monospace', direction: 'ltr', textAlign: 'left', overflowX: 'auto', marginBottom: '10px'}}>
                        <pre style={{margin: 0}}>
{`<!-- ArioNex Popup Chat Assistant Widget for ${widgetPreviewSelected.url} -->
<script src="http://localhost:8000/v1/widget.js?website=${encodeURIComponent(widgetPreviewSelected.url)}" async></script>`}
                        </pre>
                      </div>
                      <button 
                        onClick={() => {
                          const embedCode = `<!-- ArioNex Popup Chat Assistant Widget for ${widgetPreviewSelected.url} -->\n<script src="http://localhost:8000/v1/widget.js?website=${encodeURIComponent(widgetPreviewSelected.url)}" async></script>`;
                          navigator.clipboard.writeText(embedCode);
                          alert('کد اسکریپت پاپ‌آپ در حافظه کپی شد.');
                        }}
                        className="topbar-btn btn-ghost" 
                        style={{width: '100%', justifyContent: 'center', padding: '6px'}}
                      >
                        کپی کد اسکریپت پاپ‌آپ
                      </button>
                    </div>
                  )}
                </div>

                {/* پیش‌نمایش زنده ابزارک چت */}
                {widgetPreviewSelected && (
                  <div className="card" style={{border: '1px solid rgba(196, 137, 74, 0.25)', overflow: 'hidden', padding: 0}}>
                    <div style={{background: 'var(--navy-deep)', color: '#fff', padding: '12px 16px', fontWeight: 'bold', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                      <span>👀 پیش‌نمایش زنده ابزارک وب‌سایت</span>
                      <span style={{fontSize: '11px', background: widgetPreviewSelected.accent_color, color: '#fff', padding: '2px 8px', borderRadius: '10px'}}>{widgetPreviewSelected.url}</span>
                    </div>

                    <div style={{padding: '20px', background: '#f5f5f5', position: 'relative', height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundImage: 'radial-gradient(#ddd 1px, transparent 1px)', backgroundSize: '16px 16px'}}>
                      <div style={{fontSize: '12px', color: 'var(--text-muted)', zIndex: 1, textShadow: '0 1px 0 #fff'}}>اینجا نمای شبیه‌سازی شده وب‌سایت شماست.</div>

                      {/* شبیه‌سازی ابزارک باز شده */}
                      <div style={{
                        position: 'absolute',
                        bottom: '20px',
                        left: '20px',
                        width: '240px',
                        height: '240px',
                        borderRadius: '12px',
                        backgroundColor: '#fff',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                        border: `1px solid ${widgetPreviewSelected.accent_color}`,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        direction: 'rtl',
                        fontFamily: 'system-ui, sans-serif'
                      }}>
                        <div style={{
                          backgroundColor: widgetPreviewSelected.theme_color,
                          color: '#fff',
                          padding: '8px 12px',
                          fontSize: '11.5px',
                          fontWeight: 'bold',
                          display: 'flex',
                          justifyContent: 'space-between',
                          borderBottom: `2px solid ${widgetPreviewSelected.accent_color}`
                        }}>
                          <span>🛡️ دستیار هوشمند آریونکس</span>
                          <span>✕</span>
                        </div>
                        <div style={{flex: 1, padding: '10px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px'}}>
                          <div style={{
                            alignSelf: 'flex-start',
                            backgroundColor: '#f1f1f1',
                            color: '#333',
                            padding: '6px 10px',
                            borderRadius: '8px',
                            fontSize: '11px',
                            lineHeight: '1.5',
                            maxWidth: '90%'
                          }}>
                            {widgetPreviewSelected.welcome_message || 'سلام! چطور می‌توانم کمک کنم؟'}
                          </div>
                        </div>
                        <div style={{padding: '8px', borderTop: '1px solid #eee', display: 'flex', gap: '6px', background: '#fafafa'}}>
                          <input type="text" disabled style={{flex: 1, border: '1px solid #ddd', borderRadius: '4px', padding: '4px', fontSize: '10.5px'}} placeholder="تایپ کنید..." />
                          <button style={{backgroundColor: widgetPreviewSelected.theme_color, border: 'none', color: '#fff', borderRadius: '4px', padding: '4px 8px', fontSize: '10px'}}>ارسال</button>
                        </div>
                      </div>

                      {/* شبیه‌سازی دکمه شناور پاپ‌آپ */}
                      <div style={{
                        position: 'absolute',
                        bottom: '20px',
                        right: '20px',
                        width: '44px',
                        height: '44px',
                        borderRadius: '50%',
                        background: `linear-gradient(135deg, ${widgetPreviewSelected.theme_color} 0%, #000 100%)`,
                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                        border: `2px solid ${widgetPreviewSelected.accent_color}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: widgetPreviewSelected.accent_color,
                        fontSize: '20px'
                      }}>
                        💬
                      </div>
                    </div>
                  </div>
                )}
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
