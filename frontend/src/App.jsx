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
// ⚙️  REAL MODE ONLY
// ─────────────────────────────────────────────────────────────────────────────

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
  { id: 'gemma2:9b', label: 'Gemma 2 9B (پیشنهادی)' },
  { id: 'gemma2:2b', label: 'Gemma 2 2B (سبک‌ترین)' },
  { id: 'gemma2:27b', label: 'Gemma 2 27B (قدرتمند)' },
  { id: 'gemma:2b', label: 'Gemma 1 2B' },
  { id: 'gemma:7b', label: 'Gemma 1 7B' },
  { id: 'gemma3:4b', label: 'Gemma 3 4B (سریع)' },
  { id: 'llama3.2:3b', label: 'Llama 3.2 3B' },
  { id: 'qwen2.5:3b', label: 'Qwen 2.5 3B' },
];

const MOCK_MODE = false;
const mockDelay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export default function App() {
  // صفحه فعال جاری در داشبورد
  const [activeScreen, setActiveScreen] = useState('dashboard');

  // ─── Authentication State ──────────────────────────────────────────────────
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoginLoading, setIsLoginLoading] = useState(false);
  
  const [isSignupMode, setIsSignupMode] = useState(false);
  const [signupUsername, setSignupUsername] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupError, setSignupError] = useState('');
  const [isSignupLoading, setIsSignupLoading] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState(false);

  // ─── User Management State ────────────────────────────────────────────────
  const [usersList, setUsersList] = useState([]);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteUsername, setInviteUsername] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteRole, setInviteRole] = useState('Analyst');
  const [inviteError, setInviteError] = useState('');

  // ─── PII Checked State ────────────────────────────────────────────────────
  const [piiChecked, setPiiChecked] = useState(false);

  // ─── secure API fetch wrapper ──────────────────────────────────────────────
  const apiFetch = async (url, options = {}) => {
    const headers = {
      ...options.headers,
    };
    
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    const currentToken = token || localStorage.getItem('arionex_token');
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      handleLogout();
      throw new Error('جلسه شما منقضی شده است. لطفاً مجدداً وارد شوید.');
    }
    
    return response;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginUsername.trim() || !loginPassword.trim()) {
      setLoginError('لطفاً نام کاربری و رمز عبور را وارد کنید.');
      return;
    }
    
    setLoginError('');
    setIsLoginLoading(true);
    
    try {
      const res = await fetch('http://localhost:8000/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginUsername,
          password: loginPassword
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setToken(data.access_token);
        setCurrentUser(data.user);
        localStorage.setItem('arionex_token', data.access_token);
        localStorage.setItem('arionex_user', JSON.stringify(data.user));
        
        // Refresh configurations and documents
        fetchDocuments();
        fetchIntegrations();
        fetchSystemInstruction();
      } else {
        setLoginError(data.detail || 'نام کاربری یا رمز عبور اشتباه است.');
      }
    } catch (err) {
      console.error('Login failed:', err);
      setLoginError('خطا در اتصال به سرور احراز هویت آریونکس.');
    } finally {
      setIsLoginLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!signupUsername.trim() || !signupPassword.trim()) {
      setSignupError('لطفاً نام کاربری و رمز عبور را وارد کنید.');
      return;
    }
    if (signupUsername.length < 3) {
      setSignupError('نام کاربری باید حداقل ۳ کاراکتر باشد.');
      return;
    }
    if (signupPassword.length < 6) {
      setSignupError('رمز عبور باید حداقل ۶ کاراکتر باشد.');
      return;
    }

    setSignupError('');
    setSignupSuccess(false);
    setIsSignupLoading(true);

    try {
      const res = await fetch('http://localhost:8000/v1/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: signupUsername,
          password: signupPassword
        })
      });

      const data = await res.json();

      if (res.ok) {
        setSignupSuccess(true);
        setLoginUsername(signupUsername);
        setLoginPassword(signupPassword);
        alert('ثبت‌نام با موفقیت انجام شد. می‌توانید اکنون وارد شوید.');
        setIsSignupMode(false);
        setSignupUsername('');
        setSignupPassword('');
      } else {
        setSignupError(data.detail || 'خطا در ثبت‌نام کاربر.');
      }
    } catch (err) {
      console.error('Signup failed:', err);
      setSignupError('خطا در اتصال به سرور احراز هویت آریونکس.');
    } finally {
      setIsSignupLoading(false);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setToken(null);
    localStorage.removeItem('arionex_token');
    localStorage.removeItem('arionex_user');
    setActiveScreen('dashboard');
    setLoginUsername('');
    setLoginPassword('');
    setLoginError('');
  };

  const fetchUsersList = async () => {
    try {
      const res = await apiFetch('http://localhost:8000/v1/auth/users');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setUsersList(data);
      }
    } catch (err) {
      console.error('Error fetching users:', err);
    }
  };

  const handleInviteUser = async (e) => {
    e.preventDefault();
    if (!inviteUsername.trim() || !invitePassword.trim()) {
      setInviteError('لطفاً نام کاربری و رمز عبور را وارد نمایید.');
      return;
    }
    setInviteError('');
    try {
      const res = await apiFetch('http://localhost:8000/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          username: inviteUsername,
          password: invitePassword,
          role: inviteRole
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert(`کاربر "${data.username}" با موفقیت ثبت شد.`);
        setShowInviteModal(false);
        setInviteUsername('');
        setInvitePassword('');
        setInviteRole('Analyst');
        fetchUsersList();
      } else {
        setInviteError(data.detail || 'خطا در ثبت کاربر');
      }
    } catch (err) {
      console.error(err);
      setInviteError('خطا در ارتباط با سرور.');
    }
  };

  const fetchSystemInstruction = async () => {
    try {
      const res = await fetch('http://localhost:8000/v1/config/prompts');
      if (res.ok) {
        const data = await res.json();
        if (data && data.prompt) {
          setSystemInstruction(data.prompt);
        }
      }
    } catch (err) {
      console.error('Error fetching system instruction:', err);
    }
  };

  const saveSystemInstruction = async () => {
    try {
      const res = await apiFetch('http://localhost:8000/v1/config/prompts', {
        method: 'POST',
        body: JSON.stringify({ prompt: systemInstruction })
      });
      if (res.ok) {
        alert('دستورالعمل سیستم با موفقیت به‌روزرسانی شد.');
      } else {
        const data = await res.json();
        alert(data.detail || 'خطا در به‌روزرسانی دستورالعمل سیستم');
      }
    } catch (err) {
      console.error('Error saving system instruction:', err);
      alert('خطا در ارتباط با سرور');
    }
  };

  const resetSystemInstruction = () => {
    const defaultPrompt = "شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید.";
    setSystemInstruction(defaultPrompt);
  };
  
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
      const res = await apiFetch('http://localhost:8000/v1/knowledge/documents');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const mappedDocs = data.map(doc => ({
            id: doc.id,
            name: doc.filename,
            size: 'دیتابیس',
            chunks: 0,
            date: doc.created_at ? new Date(doc.created_at).toLocaleDateString('fa-IR') : '—',
            status: 'ready',
            progress: 100,
            ext: doc.file_type ? doc.file_type.toUpperCase() : 'DOC',
            min_role_required: doc.min_role_required
          }));
          setDocuments(mappedDocs);
        }
      }
    } catch (err) {
      console.info('Documents endpoint not available yet:', err.message);
    }
  };

  // ─── Crawler State ─────────────────────────────────────────────────────────
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawlMaxPages, setCrawlMaxPages] = useState(50);
  const [crawlMaxDepth, setCrawlMaxDepth] = useState(3);
  const [crawlJsRender, setCrawlJsRender] = useState(false);
  const [crawlFollowExternal, setCrawlFollowExternal] = useState(false);
  const [crawlRobots, setCrawlRobots] = useState(true);
  const [crawlJobs, setCrawlJobs] = useState([]);
  const [crawlSubmitting, setCrawlSubmitting] = useState(false);
  const [crawlStatusFilter, setCrawlStatusFilter] = useState('');

  const fetchIntegrations = async () => {
    try {
      const resWidgets = await apiFetch('http://localhost:8000/v1/integrations/widgets');
      const dataWidgets = await resWidgets.json();
      setWidgets(dataWidgets);
      if (dataWidgets.length > 0 && !widgetPreviewSelected) {
        setWidgetPreviewSelected(dataWidgets[0]);
      } else if (dataWidgets.length === 0) {
        setWidgetPreviewSelected(null);
      }

      const resKeys = await apiFetch('http://localhost:8000/v1/integrations/apikeys');
      const dataKeys = await resKeys.json();
      setApiKeys(dataKeys);
    } catch (err) {
      console.error('Error fetching integrations:', err);
    }
  };

  useEffect(() => {
    if (!currentUser) return;
    fetchIntegrations();
    if (activeScreen === 'knowledge' || activeScreen === 'upload') {
      fetchDocuments();
    }
    if (activeScreen === 'crawler') {
      fetchCrawlJobs();
    }
    if (activeScreen === 'admin' && currentUser.role === 'Admin') {
      fetchUsersList();
      fetchSystemInstruction();
    }
  }, [activeScreen, currentUser]);

  useEffect(() => {
    if (!currentUser || activeScreen !== 'crawler') return;
    const hasRunningOrQueued = crawlJobs.some(j => j.status === 'running' || j.status === 'queued');
    if (!hasRunningOrQueued) return;
    const interval = setInterval(() => {
      fetchCrawlJobs();
    }, 3000);
    return () => clearInterval(interval);
  }, [crawlJobs, activeScreen, currentUser]);

  // redirect Analyst away from admin panels
  useEffect(() => {
    if (currentUser && currentUser.role !== 'Admin' && (activeScreen === 'admin' || activeScreen === 'integrations')) {
      setActiveScreen('dashboard');
    }
  }, [activeScreen, currentUser]);

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
      const res = await apiFetch('http://localhost:8000/v1/integrations/widgets', {
        method: 'POST',
        body: JSON.stringify(widgetData)
      });
      const data = await res.json();
      if (res.ok) {
        setWidgets(prev => [data, ...prev]);
        setWidgetPreviewSelected(data);
      } else {
        alert(data.detail || 'خطا در ثبت ابزارک');
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
      const res = await apiFetch(`http://localhost:8000/v1/integrations/widgets/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setWidgets(prev => prev.filter(w => w.id !== id));
        if (widgetPreviewSelected?.id === id) {
          setWidgetPreviewSelected(null);
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
      const res = await apiFetch('http://localhost:8000/v1/integrations/apikeys', {
        method: 'POST',
        body: JSON.stringify({ name: newKeyName })
      });
      const data = await res.json();
      if (res.ok) {
        setApiKeys(prev => [data, ...prev]);
        setGeneratedKey(data.api_key);
      }
      setNewKeyName('');
    } catch (err) {
      console.error('Error creating API key:', err);
    }
  };

  const handleDeleteAPIKey = async (id) => {
    if (!confirm('آیا از ابطال این کلید API اطمینان دارید؟')) return;
    try {
      const res = await apiFetch(`http://localhost:8000/v1/integrations/apikeys/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setApiKeys(prev => prev.filter(k => k.id !== id));
      }
    } catch (err) {
      console.error('Error deleting API key:', err);
    }
  };

  // همگام‌سازی فیچر تاگل‌ها با روشن شدن فرانت‌اند
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch('http://localhost:8000/v1/config');
        const data = await res.json();
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
          setOllamaEnabled(data.llm_provider === 'ollama');
          if (data.ollama_model) setOllamaModel(data.ollama_model);
          if (data.ollama_base_url) setOllamaEndpoint(data.ollama_base_url);
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

    apiFetch('http://localhost:8000/v1/config', {
      method: 'POST',
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

    apiFetch('http://localhost:8000/v1/config', {
      method: 'POST',
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
      const savedToken = token || localStorage.getItem('arionex_token');
      const res = await fetch('http://localhost:8000/v1/query/stream', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(savedToken ? { 'Authorization': `Bearer ${savedToken}` } : {})
        },
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

          const decodedData = dataLine.replace(/\\n/g, '\n');

          if (eventName === 'token') {
            accumulated += decodedData;
            setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: accumulated } : m));
          } else if (eventName === 'sources') {
            try {
              const parsedSources = JSON.parse(decodedData);
              setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, sources: parsedSources } : m));
            } catch (_) {}
          } else if (eventName === 'done') {
            try {
              const meta = JSON.parse(decodedData);
              const isRefusal = accumulated === 'منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند.';
              setChatMessages(prev => prev.map(m => m.id === aiMsgId
                ? { ...m, isSafe: meta.is_safe ?? true, isRefusal }
                : m));
            } catch (_) {}
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

  if (!currentUser) {
    return (
      <div className="login-overlay">
        <div className="login-card">
          <div className="login-logo">
            <svg className="logo-mark" viewBox="0 0 32 32" fill="none" width="40" height="40">
              <polygon points="16,2 28,26 4,26" fill="none" stroke="#c4894a" strokeWidth="2.5"/>
              <polygon points="16,9 22,26 10,26" fill="none" stroke="#c4894a" strokeWidth="1.5" opacity="0.5"/>
            </svg>
            <span className="logo-text" style={{fontSize: '26px', color: 'white'}}>آریو<span>نکس</span></span>
          </div>
          
          <h2 className="login-title">{isSignupMode ? 'ثبت‌نام در سامانه تجاری آریونکس' : 'ورود به سامانه تجاری آریونکس'}</h2>
          <p className="login-subtitle">سامانه هوشمند مدیریت دانش، ممیزی حریم خصوصی (PII) و تحلیل قوانین انطباق سازمان</p>
          
          {isSignupMode ? (
            <>
              {signupError && <div className="login-error">{signupError}</div>}
              {signupSuccess && <div className="login-success">ثبت‌نام با موفقیت انجام شد!</div>}
              
              <form onSubmit={handleSignup}>
                <div className="login-form-group">
                  <label className="login-label">نام کاربری</label>
                  <input 
                    type="text" 
                    className="login-input" 
                    value={signupUsername} 
                    onChange={e => setSignupUsername(e.target.value)}
                    placeholder="username"
                    required
                  />
                </div>
                
                <div className="login-form-group">
                  <label className="login-label">رمز عبور</label>
                  <input 
                    type="password" 
                    className="login-input" 
                    value={signupPassword} 
                    onChange={e => setSignupPassword(e.target.value)}
                    placeholder="••••••"
                    required
                  />
                </div>
                
                <button type="submit" className="login-btn" disabled={isSignupLoading}>
                  {isSignupLoading ? '⏳ در حال ثبت‌نام...' : 'ثبت‌نام کاربر جدید'}
                </button>
              </form>
              
              <div className="login-toggle-mode" style={{marginTop: '15px', fontSize: '13px'}}>
                قبلاً ثبت‌نام کرده‌اید؟ {' '}
                <span 
                  style={{color: '#c4894a', cursor: 'pointer', textDecoration: 'underline'}} 
                  onClick={() => {
                    setIsSignupMode(false);
                    setSignupError('');
                  }}
                >
                  ورود به سیستم
                </span>
              </div>
            </>
          ) : (
            <>
              {loginError && <div className="login-error">{loginError}</div>}
              
              <form onSubmit={handleLogin}>
                <div className="login-form-group">
                  <label className="login-label">نام کاربری</label>
                  <input 
                    type="text" 
                    className="login-input" 
                    value={loginUsername} 
                    onChange={e => setLoginUsername(e.target.value)}
                    placeholder="username"
                    required
                  />
                </div>
                
                <div className="login-form-group">
                  <label className="login-label">رمز عبور</label>
                  <input 
                    type="password" 
                    className="login-input" 
                    value={loginPassword} 
                    onChange={e => setLoginPassword(e.target.value)}
                    placeholder="••••••"
                    required
                  />
                </div>
                
                <button type="submit" className="login-btn" disabled={isLoginLoading}>
                  {isLoginLoading ? '⏳ در حال ورود...' : 'ورود به سیستم'}
                </button>
              </form>
              
              <div className="login-toggle-mode" style={{marginTop: '15px', fontSize: '13px'}}>
                کاربر جدید هستید؟ {' '}
                <span 
                  style={{color: '#c4894a', cursor: 'pointer', textDecoration: 'underline'}} 
                  onClick={() => {
                    setIsSignupMode(true);
                    setLoginError('');
                  }}
                >
                  ایجاد حساب کاربری (تحلیل‌گر)
                </span>
              </div>
            </>
          )}
          
          <div style={{fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '24px'}}>
            ArioNex Commercial AI Platform · Version 1.0.0
          </div>
        </div>
      </div>
    );
  }

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
          <div 
            className={`nav-item ${activeScreen === 'crawler' ? 'active' : ''}`}
            onClick={() => setActiveScreen('crawler')}
          >
            <span>🕷️</span> کرالر وب‌سایت
          </div>
        </div>

        {/* بخش منوی مدیریتی ادمین */}
        {currentUser?.role === 'Admin' && (
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
        )}

        {/* پروفایل کاربر در پایین سایدبار */}
        <div className="sidebar-bottom">
          <div className="user-card" style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
              <div className="user-avatar" style={{textTransform: 'uppercase'}}>{currentUser?.username?.substring(0, 2) || 'UR'}</div>
              <div className="user-info">
                <div className="user-name">{currentUser?.username}</div>
                <div className="user-role">{currentUser?.role === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}</div>
              </div>
            </div>
            <button 
              onClick={handleLogout} 
              style={{
                background: 'none', 
                border: 'none', 
                color: 'var(--copper-dark)', 
                cursor: 'pointer', 
                fontSize: '18px', 
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'color var(--transition-fast)'
              }}
              title="خروج از حساب"
            >
              🚪
            </button>
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
            {activeScreen === 'crawler' && 'کرالر هوشمند وب‌سایت — استخراج دانش'}
          </div>
          
          <div className="topbar-search">
            <span className="search-icon">🔍</span>
            <span className="search-placeholder">جستجو در پایگاه دانش…</span>
          </div>

          <button className="topbar-btn btn-ghost" onClick={() => setActiveScreen('chat')}>
            <span>+</span> <span className="btn-text">پرسش جدید</span>
          </button>
          
          <button className="topbar-btn btn-primary" onClick={() => setActiveScreen('upload')}>
            <span>↑</span> <span className="btn-text">آپلود سریع</span>
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
                    isWelcome: true,
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
            <div className="grid-3-col">
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
                <div className="ft-header" style={{gridTemplateColumns: '2fr 1fr 1fr 1.2fr 1.2fr'}}>
                  <div>نام سند</div>
                  <div>حجم فیزیکی</div>
                  <div>تاریخ پردازش</div>
                  <div>سطح دسترسی</div>
                  <div>وضعیت و عملیات</div>
                </div>
                
                {documents.map(doc => (
                  <div key={doc.id} className="ft-row" style={{gridTemplateColumns: '2fr 1fr 1fr 1.2fr 1.2fr'}}>
                    <div className="ft-filename">
                      <span className={`ft-ext ext-${doc.ext.toLowerCase()}`}>{doc.ext}</span>
                      {doc.name}
                    </div>
                    <div style={{color: 'var(--text-secondary)'}}>{doc.size}</div>
                    <div style={{color: 'var(--text-muted)'}}>{doc.date}</div>
                    <div>
                      {currentUser?.role === 'Admin' ? (
                        <select
                          value={doc.min_role_required || 'Analyst'}
                          onChange={async (e) => {
                            const newRole = e.target.value;
                            try {
                              const res = await apiFetch(`http://localhost:8000/v1/knowledge/documents/${doc.id}/role`, {
                                method: 'PUT',
                                body: JSON.stringify({ min_role_required: newRole })
                              });
                              if (res.ok) {
                                setDocuments(prev => prev.map(d => d.id === doc.id ? { ...d, min_role_required: newRole } : d));
                              } else {
                                const errData = await res.json();
                                alert(errData.detail || 'خطا در تغییر سطح دسترسی');
                              }
                            } catch (err) {
                              console.error(err);
                              alert('خطا در تغییر سطح دسترسی');
                            }
                          }}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '6px',
                            border: '1px solid var(--gray-200)',
                            fontSize: '12px',
                            background: 'var(--gray-50)',
                            color: 'var(--text-primary)',
                            fontFamily: 'inherit',
                            cursor: 'pointer'
                          }}
                        >
                          <option value="Analyst">تحلیل‌گر (Analyst)</option>
                          <option value="Admin">مدیر سیستم (Admin)</option>
                        </select>
                      ) : (
                        <span className={`perm-badge ${doc.min_role_required === 'Admin' ? 'p-admin' : 'p-analyst'}`}>
                          {doc.min_role_required === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}
                        </span>
                      )}
                    </div>
                    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px'}}>
                      {doc.status === 'ready' ? (
                        <span className="q-badge qb-done">✓ ایندکس شده</span>
                      ) : (
                        <div style={{display: 'flex', alignItems: 'center', gap: '8px', flex: 1}}>
                          <div className="prog-bar-wrap" style={{width: '60px'}}>
                            <div className="prog-bar" style={{width: `${doc.progress}%`}}></div>
                          </div>
                          <span style={{fontSize: '11px', color: 'var(--copper-dark)', fontWeight: 'bold'}}>{doc.progress}%</span>
                        </div>
                      )}
                      
                      {currentUser?.role === 'Admin' && (
                        <button
                          onClick={async () => {
                            if (!confirm(`آیا از حذف سند "${doc.name}" و تمامی بردارهای مرتبط با آن اطمینان دارید؟`)) return;
                            try {
                              const res = await apiFetch(`http://localhost:8000/v1/knowledge/documents/${doc.id}`, {
                                method: 'DELETE'
                              });
                              if (res.ok) {
                                setDocuments(prev => prev.filter(d => d.id !== doc.id));
                              } else {
                                const errData = await res.json();
                                alert(errData.detail || 'خطا در حذف سند');
                              }
                            } catch (err) {
                              console.error(err);
                              alert('خطا در ارتباط با سرور');
                            }
                          }}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#c62828',
                            cursor: 'pointer',
                            fontSize: '15px',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'transform var(--transition-fast)'
                          }}
                          title="حذف سند"
                        >
                          🗑️
                        </button>
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

            <div className="grid-2-col">
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
                    <span style={{color: 'var(--text-secondary)', fontStyle: 'italic', opacity: 0.8}}>
                      هیچ سندی هنوز بارگذاری نشده است. پیش‌نمایش پوشش اطلاعات حساس (PII) پس از بارگذاری سند در اینجا نمایش داده خواهد شد.
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
                  ) : piiChecked ? (
                    <span style={{color: 'var(--color-success)', fontWeight: '600'}}>
                      ✓ هیچ اطلاعات حساسی (مانند کد ملی، تلفن همراه، حساب بانکی و ایمیل) در آخرین سند بارگذاری شده یافت نشد.
                    </span>
                  ) : piiPreview ? (
                    <span>{piiPreview}</span>
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
                
                <div style={{display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '200px', overflowY: 'auto', marginBottom: '16px'}}>
                  {usersList.map((usr, i) => (
                    <div key={i} className="permission-row">
                      <div className="perm-user">
                        <div className="perm-av" style={{textTransform: 'uppercase'}}>{usr.username.substring(0, 2)}</div>
                        {usr.username}
                      </div>
                      <span className={`perm-badge ${usr.role === 'Admin' ? 'p-admin' : 'p-analyst'}`}>
                        {usr.role === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}
                      </span>
                    </div>
                  ))}
                </div>

                <button 
                  className="topbar-btn btn-ghost" 
                  style={{width: '100%', justifyContent: 'center'}}
                  onClick={() => setShowInviteModal(true)}
                >
                  + ثبت کاربر جدید در سازمان
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
                  <button className="topbar-btn btn-primary" style={{flex: 1, justifyContent: 'center'}} onClick={saveSystemInstruction}>ذخیره دستورالعمل جدید</button>
                  <button className="topbar-btn btn-ghost" style={{flex: 1, justifyContent: 'center'}} onClick={resetSystemInstruction}>بازنشانی به پیش‌فرض</button>
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
                      fetch('http://localhost:8000/v1/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ providers: { ollama: next } })
                      }).catch(() => {});
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
                          fetch('http://localhost:8000/v1/config', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ollama_model: e.target.value })
                          }).catch(() => {});
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
            <div className="grid-3-col">
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
                    <div className="api-keys-grid" style={{padding: '10px 14px', background: 'var(--gray-50)', fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', borderBottom: '1px solid var(--gray-100)'}}>
                      <div>نام کلید</div>
                      <div>کلید دسترسی (Masked)</div>
                      <div>تاریخ ایجاد</div>
                      <div>عملیات</div>
                    </div>
                    {apiKeys.length === 0 ? (
                      <div style={{padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px'}}>هیچ کلید API تعریف نشده است. کلیدها پیش از حذف شدن دسترسی آزاد را فراهم می‌کنند.</div>
                    ) : (
                      apiKeys.map(key => (
                        <div key={key.id} className="api-keys-grid" style={{padding: '12px 14px', alignItems: 'center', borderBottom: '1px solid var(--gray-50)', fontSize: '12.5px'}}>
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
                    <div className="grid-2-col" style={{gap: '10px'}}>
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

        {/* ─── صفحه کرالر وب‌سایت ──────────────────────────────────────────── */}
        {activeScreen === 'crawler' && (
          <div className="screen fade-in">
            {/* آمار کلی job‌ها */}
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px'}}>
              <div className="card" style={{borderTop: '3px solid var(--navy)'}}>
                <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>کل job‌های کرال</div>
                <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--navy)'}}>{crawlJobs.length}</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--color-success)'}}>
                <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>تکمیل‌شده</div>
                <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--color-success)'}}>{crawlJobs.filter(j => j.status === 'completed').length}</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--copper)'}}>
                <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>در حال اجرا</div>
                <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--copper)'}}>{crawlJobs.filter(j => j.status === 'running').length}</div>
              </div>
              <div className="card" style={{borderTop: '3px solid var(--color-info)'}}>
                <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>کل chunk‌های ایندکس</div>
                <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--navy)'}}>{crawlJobs.reduce((s, j) => s + j.chunks_indexed, 0)}</div>
              </div>
            </div>

            <div className="two-col">
              {/* فرم ایجاد job جدید */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                <div className="card">
                  <div className="card-title">🕷️ شروع کرال وب‌سایت جدید</div>
                  <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '16px'}}>
                    آدرس وب‌سایت را وارد کنید. سیستم تمام صفحات را به صورت async کرال کرده، محتوا را chunk و در پایگاه دانش ایندکس می‌کند.
                  </div>

                  <form onSubmit={async (e) => {
                    e.preventDefault();
                    if (!crawlUrl.trim() || crawlSubmitting) return;
                    setCrawlSubmitting(true);
                    try {
                      if (MOCK_MODE) {
                        await mockDelay(800);
                        const newJob = {
                          job_id: `job-${Date.now()}`,
                          url: crawlUrl,
                          status: 'queued',
                          pages_crawled: 0,
                          chunks_indexed: 0,
                          pages_failed: 0,
                          max_pages: crawlMaxPages,
                          max_depth: crawlMaxDepth,
                          js_render: crawlJsRender,
                          follow_external_domains: crawlFollowExternal,
                          label: null,
                          widget_id: null,
                          error_message: null,
                          created_at: new Date().toISOString(),
                          updated_at: new Date().toISOString(),
                        };
                        setCrawlJobs(prev => [newJob, ...prev]);
                        setCrawlUrl('');
                      } else {
                        const res = await fetch('http://localhost:8000/v1/crawl/start', {
                          method: 'POST',
                          headers: {'Content-Type': 'application/json'},
                          body: JSON.stringify({
                            url: crawlUrl,
                            max_pages: crawlMaxPages,
                            max_depth: crawlMaxDepth,
                            js_render: crawlJsRender,
                            follow_external_domains: crawlFollowExternal,
                            respect_robots: crawlRobots,
                          }),
                        });
                        const data = await res.json();
                        if (res.ok) {
                          setCrawlJobs(prev => [data, ...prev]);
                          setCrawlUrl('');
                        } else {
                          alert(data.detail || 'خطا در شروع کرال');
                        }
                      }
                    } catch(err) {
                      alert('خطا در اتصال به سرور');
                    } finally {
                      setCrawlSubmitting(false);
                    }
                  }} style={{display: 'flex', flexDirection: 'column', gap: '14px'}}>

                    <div>
                      <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>آدرس وب‌سایت (URL ریشه)</label>
                      <input
                        type="url"
                        id="crawl-url-input"
                        className="chat-input-box"
                        style={{borderRadius: 'var(--radius)', width: '100%', direction: 'ltr', fontSize: '13px'}}
                        placeholder="https://example.com"
                        value={crawlUrl}
                        onChange={e => setCrawlUrl(e.target.value)}
                        required
                      />
                    </div>

                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
                      <div>
                        <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>حداکثر صفحات</label>
                        <input
                          type="number" min="1" max="500"
                          id="crawl-max-pages"
                          className="chat-input-box"
                          style={{borderRadius: 'var(--radius)', width: '100%'}}
                          value={crawlMaxPages}
                          onChange={e => setCrawlMaxPages(Number(e.target.value))}
                        />
                      </div>
                      <div>
                        <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>حداکثر عمق</label>
                        <input
                          type="number" min="1" max="10"
                          id="crawl-max-depth"
                          className="chat-input-box"
                          style={{borderRadius: 'var(--radius)', width: '100%'}}
                          value={crawlMaxDepth}
                          onChange={e => setCrawlMaxDepth(Number(e.target.value))}
                        />
                      </div>
                    </div>

                    {/* toggle‌های پیشرفته */}
                    <div style={{background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '14px', border: '1px solid var(--gray-100)'}}>
                      <div style={{fontSize: '12px', fontWeight: '700', color: 'var(--navy)', marginBottom: '12px'}}>تنظیمات پیشرفته کرالر</div>

                      <div className="toggle-row" style={{marginBottom: '10px'}}>
                        <div>
                          <span className="toggle-label" style={{display: 'block'}}>رندر JavaScript (Playwright)</span>
                          <span style={{fontSize: '11px', color: 'var(--text-muted)'}}>برای سایت‌های React/Vue/Angular — نیاز به playwright</span>
                        </div>
                        <div
                          id="toggle-js-render"
                          className={`toggle ${crawlJsRender ? 'toggle-on' : 'toggle-off'}`}
                          onClick={() => setCrawlJsRender(p => !p)}
                        />
                      </div>

                      <div className="toggle-row" style={{marginBottom: '10px'}}>
                        <div>
                          <span className="toggle-label" style={{display: 'block'}}>دنبال کردن دامنه‌های خارجی</span>
                          <span style={{fontSize: '11px', color: 'var(--text-muted)'}}>با سختگیری زیاد — فقط subdomain‌های همان سازمان</span>
                        </div>
                        <div
                          id="toggle-follow-external"
                          className={`toggle ${crawlFollowExternal ? 'toggle-on' : 'toggle-off'}`}
                          onClick={() => setCrawlFollowExternal(p => !p)}
                        />
                      </div>

                      <div className="toggle-row">
                        <span className="toggle-label">رعایت robots.txt سایت هدف</span>
                        <div
                          id="toggle-robots"
                          className={`toggle ${crawlRobots ? 'toggle-on' : 'toggle-off'}`}
                          onClick={() => setCrawlRobots(p => !p)}
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      id="crawl-start-btn"
                      className="topbar-btn btn-primary"
                      style={{justifyContent: 'center', padding: '12px 24px', fontSize: '14px', opacity: crawlSubmitting ? 0.7 : 1}}
                      disabled={crawlSubmitting}
                    >
                      {crawlSubmitting ? '⏳ در حال ایجاد job...' : '🕷️ شروع کرال'}
                    </button>
                  </form>
                </div>

                {/* راهنمای API */}
                <div className="card">
                  <div className="card-title">📖 فراخوانی مستقیم API کرالر</div>
                  <div style={{background: 'var(--navy-deep)', padding: '14px', borderRadius: 'var(--radius)', color: '#fff', fontSize: '12px', fontFamily: 'monospace', direction: 'ltr', textAlign: 'left', overflowX: 'auto'}}>
                    <pre style={{margin: 0}}>{`curl -X POST "http://localhost:8000/v1/crawl/start" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: YOUR_API_KEY" \\
  -d '{
    "url": "https://your-website.com",
    "max_pages": 100,
    "max_depth": 4,
    "js_render": false,
    "follow_external_domains": false
  }'`}</pre>
                  </div>
                </div>
              </div>

              {/* لیست job‌ها */}
              <div className="card">
                <div className="card-title" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <span>📋 لیست job‌های کرال</span>
                  <div style={{display: 'flex', gap: '8px'}}>
                    {['', 'queued', 'running', 'completed', 'failed'].map(s => (
                      <button
                        key={s}
                        onClick={() => setCrawlStatusFilter(s)}
                        style={{
                          fontSize: '11px',
                          padding: '3px 10px',
                          borderRadius: '12px',
                          border: '1px solid',
                          cursor: 'pointer',
                          fontWeight: crawlStatusFilter === s ? '700' : '400',
                          background: crawlStatusFilter === s ? 'var(--navy)' : 'transparent',
                          color: crawlStatusFilter === s ? '#fff' : 'var(--text-muted)',
                          borderColor: crawlStatusFilter === s ? 'var(--navy)' : 'var(--gray-100)',
                        }}
                      >
                        {s === '' ? 'همه' : s === 'queued' ? 'صف' : s === 'running' ? 'در حال اجرا' : s === 'completed' ? 'تکمیل' : 'خطا'}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px'}}>
                  {crawlJobs
                    .filter(j => !crawlStatusFilter || j.status === crawlStatusFilter)
                    .map(job => {
                      const statusColor = {
                        queued: 'var(--text-muted)',
                        running: 'var(--copper)',
                        completed: 'var(--color-success)',
                        failed: '#c62828',
                        cancelled: 'var(--text-muted)',
                      }[job.status] || 'var(--text-muted)';

                      const statusLabel = {
                        queued: '⏳ در صف',
                        running: '⚡ در حال کرال',
                        completed: '✅ تکمیل',
                        failed: '❌ خطا',
                        cancelled: '🚫 لغو شد',
                      }[job.status] || job.status;

                      const progress = job.max_pages > 0 ? Math.round((job.pages_crawled / job.max_pages) * 100) : 0;

                      return (
                        <div key={job.job_id} style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '14px', background: 'var(--gray-50)'}}>
                          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px'}}>
                            <div style={{flex: 1, minWidth: 0}}>
                              <div style={{fontWeight: '600', fontSize: '13px', color: 'var(--navy)', direction: 'ltr', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                                {job.url}
                              </div>
                              <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px', direction: 'ltr'}}>
                                {job.job_id.substring(0, 20)}...
                              </div>
                            </div>
                            <div style={{display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0, marginRight: '10px'}}>
                              <span style={{fontSize: '12px', fontWeight: '700', color: statusColor}}>{statusLabel}</span>
                              {(job.status === 'queued' || job.status === 'running') && (
                                <button
                                  onClick={async () => {
                                    if (MOCK_MODE) {
                                      setCrawlJobs(prev => prev.map(j => j.job_id === job.job_id ? {...j, status: 'cancelled'} : j));
                                    } else {
                                      const res = await fetch(`http://localhost:8000/v1/crawl/${job.job_id}`, {method: 'DELETE'});
                                      if (res.ok) {
                                        setCrawlJobs(prev => prev.map(j => j.job_id === job.job_id ? {...j, status: 'cancelled'} : j));
                                      }
                                    }
                                  }}
                                  style={{background: '#ffebee', color: '#c62828', border: 'none', borderRadius: '4px', padding: '3px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold'}}
                                >
                                  لغو
                                </button>
                              )}
                            </div>
                          </div>

                          {/* نوار پیشرفت */}
                          {(job.status === 'running' || job.status === 'completed') && (
                            <div style={{marginBottom: '10px'}}>
                              <div className="prog-bar-wrap" style={{width: '100%'}}>
                                <div className="prog-bar" style={{width: `${Math.min(progress, 100)}%`, background: job.status === 'completed' ? 'var(--color-success)' : 'linear-gradient(90deg, var(--copper), var(--copper-light))'}} />
                              </div>
                            </div>
                          )}

                          {/* آمار */}
                          <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '11.5px'}}>
                            <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                              <div style={{fontWeight: '700', color: 'var(--navy)'}}>{job.pages_crawled}</div>
                              <div style={{color: 'var(--text-muted)'}}>صفحه کرال شد</div>
                            </div>
                            <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                              <div style={{fontWeight: '700', color: 'var(--copper)'}}>{job.chunks_indexed}</div>
                              <div style={{color: 'var(--text-muted)'}}>chunk ایندکس</div>
                            </div>
                            <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                              <div style={{fontWeight: '700', color: job.pages_failed > 0 ? '#c62828' : 'var(--color-success)'}}>{job.pages_failed}</div>
                              <div style={{color: 'var(--text-muted)'}}>صفحه ناموفق</div>
                            </div>
                          </div>

                          {/* تگ‌های تنظیمات */}
                          <div style={{display: 'flex', gap: '6px', marginTop: '10px', flexWrap: 'wrap'}}>
                            <span style={{fontSize: '10.5px', background: 'var(--gray-100)', padding: '2px 8px', borderRadius: '8px', color: 'var(--text-muted)'}}>عمق: {job.max_depth}</span>
                            {job.js_render && <span style={{fontSize: '10.5px', background: 'rgba(196, 137, 74, 0.15)', padding: '2px 8px', borderRadius: '8px', color: 'var(--copper-dark)'}}>JS Render</span>}
                            {job.follow_external_domains && <span style={{fontSize: '10.5px', background: 'rgba(13, 71, 161, 0.1)', padding: '2px 8px', borderRadius: '8px', color: 'var(--navy)'}}>دامنه خارجی</span>}
                            {job.label && <span style={{fontSize: '10.5px', background: 'var(--gray-100)', padding: '2px 8px', borderRadius: '8px', color: 'var(--text-muted)', fontFamily: 'monospace', direction: 'ltr'}}>{job.label}</span>}
                          </div>

                          {job.error_message && (
                            <div style={{marginTop: '8px', fontSize: '11.5px', color: '#c62828', background: '#ffebee', padding: '6px 10px', borderRadius: '4px'}}>
                              ⚠️ {job.error_message}
                            </div>
                          )}
                        </div>
                      );
                    })}

                  {crawlJobs.filter(j => !crawlStatusFilter || j.status === crawlStatusFilter).length === 0 && (
                    <div style={{textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', fontSize: '13px'}}>
                      🕷️ هیچ job کرالی یافت نشد. یک URL را کرال کنید تا اینجا نمایش داده شود.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* برچسب اصالت و برندینگ در گوشه داشبورد */}
        <div className="wf-tag">ArioNex Commercial AI — v1.0.0</div>
      </div>

      {/* مدال دعوت کاربر جدید */}
      {showInviteModal && (
        <div className="login-overlay" style={{background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(8px)'}}>
          <div className="login-card" style={{maxWidth: '400px', padding: '30px'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
              <h3 style={{color: 'white', margin: 0, fontSize: '18px'}}>ثبت کاربر جدید</h3>
              <button 
                onClick={() => setShowInviteModal(false)}
                style={{background: 'none', border: 'none', color: 'white', fontSize: '18px', cursor: 'pointer'}}
              >
                ✕
              </button>
            </div>
            
            {inviteError && <div className="login-error">{inviteError}</div>}
            
            <form onSubmit={handleInviteUser}>
              <div className="login-form-group">
                <label className="login-label">نام کاربری</label>
                <input 
                  type="text" 
                  className="login-input" 
                  value={inviteUsername} 
                  onChange={e => setInviteUsername(e.target.value)}
                  placeholder="username"
                  required
                />
              </div>
              
              <div className="login-form-group">
                <label className="login-label">رمز عبور</label>
                <input 
                  type="password" 
                  className="login-input" 
                  value={invitePassword} 
                  onChange={e => setInvitePassword(e.target.value)}
                  placeholder="••••••"
                  required
                />
              </div>
              
              <div className="login-form-group">
                <label className="login-label">نقش کاربر</label>
                <select 
                  value={inviteRole} 
                  onChange={e => setInviteRole(e.target.value)}
                  className="login-input"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    color: 'white',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '12px',
                    fontFamily: 'inherit',
                    direction: 'rtl',
                    textAlign: 'right'
                  }}
                >
                  <option value="Analyst" style={{background: '#1a2744'}}>تحلیل‌گر (Analyst)</option>
                  <option value="Admin" style={{background: '#1a2744'}}>مدیر سیستم (Admin)</option>
                </select>
              </div>
              
              <button type="submit" className="login-btn" style={{marginTop: '15px'}}>
                ثبت کاربر
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
