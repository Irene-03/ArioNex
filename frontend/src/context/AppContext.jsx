import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { createApiClient } from '../api/apiClient';

const AppContext = createContext(null);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const [activeScreen, setActiveScreen] = useState('dashboard');

  // ─── Authentication State ──────────────────────────────────────────────────
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem('arionex_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('arionex_token') || null);
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('arionex_refresh_token') || null);
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

  // API Fetch Wrapper
  const handleLogout = () => {
    setCurrentUser(null);
    setToken(null);
    setRefreshToken(null);
    localStorage.removeItem('arionex_token');
    localStorage.removeItem('arionex_refresh_token');
    localStorage.removeItem('arionex_user');
    setActiveScreen('dashboard');
    setLoginUsername('');
    setLoginPassword('');
    setLoginError('');
  };

  const apiFetch = createApiClient(token, refreshToken, handleLogout, (newToken, newRefreshToken) => {
    setToken(newToken);
    setRefreshToken(newRefreshToken);
  });

  // ─── Auth Handlers ────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
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
        setRefreshToken(data.refresh_token);
        setCurrentUser(data.user);
        localStorage.setItem('arionex_token', data.access_token);
        localStorage.setItem('arionex_refresh_token', data.refresh_token);
        localStorage.setItem('arionex_user', JSON.stringify(data.user));
        
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
    if (e && e.preventDefault) e.preventDefault();
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
    if (e && e.preventDefault) e.preventDefault();
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

  // ─── Prompts and Settings ────────────────────────────────────────────────
  const [systemInstruction, setSystemInstruction] = useState(
    'شما یک دستیار دانش حرفه‌ای برای آریونکس هستید. همیشه منابع را دقیق استناد دهید. هیچ‌گاه فراتر از اسناد ارائه‌شده گمانه‌زنی نکنید. اگر سند مرتبطی یافت نشد، صادقانه بگویید…'
  );

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

  const [features, setFeatures] = useState({
    checkCategories: false,
    piiRedaction: true,
    localGemma: true,
    hallucinationGuard: false,
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

  const toggleFeature = (key) => {
    const updatedFeatures = { ...features, [key]: !features[key] };
    setFeatures(updatedFeatures);

    apiFetch('http://localhost:8000/v1/config', {
      method: 'POST',
      body: JSON.stringify({
        services: {
          safety_auditor: updatedFeatures.localGemma,
          log_processor: updatedFeatures.auditLog,
          web_search: !updatedFeatures.externalApiBlocked,
          check_categories: updatedFeatures.checkCategories
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
          anthropic: providerKey === 'anthropic' ? !features.providerOpenAnthropic : features.providerAnthropic, // Note typo fix
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

  const [telegramBotToken, setTelegramBotToken] = useState('');

  const handleSaveTelegramToken = async (tokenValue) => {
    try {
      const res = await apiFetch('http://localhost:8000/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telegram_bot_token: tokenValue
        })
      });
      if (res.ok) {
        setTelegramBotToken(tokenValue);
        alert('توکن ربات تلگرام با موفقیت به‌روزرسانی و ربات راه‌اندازی شد.');
        return true;
      } else {
        const data = await res.json();
        alert(data.detail || 'خطا در به‌روزرسانی توکن ربات تلگرام');
        return false;
      }
    } catch (err) {
      console.error(err);
      alert('خطا در به‌روزرسانی توکن ربات تلگرام');
      return false;
    }
  };

  const [providerApiKeys, setProviderApiKeys] = useState({
    openai: '',
    openrouter: '',
    anthropic: '',
    google: '',
    deepseek: '',
    gapgpt: '',
    avalai: '',
    hormouz: ''
  });

  const handleSaveProviderApiKey = async (provider, keyValue) => {
    try {
      const res = await apiFetch('http://localhost:8000/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          [`${provider}_api_key`]: keyValue
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.current_config?.api_keys) {
          setProviderApiKeys(data.current_config.api_keys);
        }
        alert('کلید API پروایدر با موفقیت ذخیره شد.');
        return true;
      } else {
        const data = await res.json();
        alert(data.detail || 'خطا در ذخیره کلید API');
        return false;
      }
    } catch (err) {
      console.error(err);
      alert('خطا در ذخیره کلید API');
      return false;
    }
  };

  const [ollamaEnabled, setOllamaEnabled] = useState(false);
  const [ollamaModel, setOllamaModel] = useState('gemma3:4b');
  const [ollamaEndpoint, setOllamaEndpoint] = useState('http://localhost:11434');

  // ─── Chat messages & Sessions ──────────────────────────────────────────────
  const [sessions, setSessions] = useState(() => {
    try {
      const stored = localStorage.getItem('arionex_chat_sessions');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (_) {}
    return [
      {
        id: 'session_default',
        title: 'مکالمه جدید',
        messages: [
          {
            id: 1,
            sender: 'ai',
            text: 'سلام! من دستیار دانش امن شما (آریو) هستم. تمام پرسش‌ها روی داده‌های خصوصی شما اجرا می‌شوند — هیچ اطلاعاتی از زیرساخت شما خارج نمی‌شود. چطور می‌توانم کمک کنم؟',
            isSafe: true,
            isWelcome: true,
            sources: []
          }
        ]
      }
    ];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      const storedActive = localStorage.getItem('arionex_active_session_id');
      if (storedActive) return storedActive;
    } catch (_) {}
    return 'session_default';
  });

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];
  const chatMessages = activeSession ? activeSession.messages : [];

  const setChatMessages = (updater) => {
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        const newMessages = typeof updater === 'function' ? updater(s.messages) : updater;
        
        let title = s.title;
        if (s.title === 'مکالمه جدید') {
          const firstUserMsg = newMessages.find(m => m.sender === 'user');
          if (firstUserMsg) {
            title = firstUserMsg.text.substring(0, 30) + (firstUserMsg.text.length > 30 ? '...' : '');
          }
        }
        return {
          ...s,
          title,
          messages: newMessages
        };
      }
      return s;
    }));
  };

  const [inputText, setInputText] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('arionex_chat_sessions', JSON.stringify(sessions));
    } catch (_) {}
  }, [sessions]);

  useEffect(() => {
    try {
      localStorage.setItem('arionex_active_session_id', activeSessionId);
    } catch (_) {}
  }, [activeSessionId]);

  // Safety sync: Ensure activeSessionId is always a valid existing session ID
  useEffect(() => {
    if (sessions.length > 0) {
      const exists = sessions.some(s => s.id === activeSessionId);
      if (!exists) {
        setActiveSessionId(sessions[0].id);
      }
    }
  }, [sessions, activeSessionId]);

  const createNewSession = () => {
    const newId = `session_${Date.now()}`;
    const newSession = {
      id: newId,
      title: 'مکالمه جدید',
      messages: [
        {
          id: Date.now(),
          sender: 'ai',
          text: 'مکالمه جدید شروع شد. چطور می‌توانم کمک کنم؟',
          isSafe: true,
          isWelcome: true,
          sources: []
        }
      ]
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newId);
  };

  const deleteSession = (id, e) => {
    if (e && e.stopPropagation) e.stopPropagation();
    if (sessions.length <= 1) {
      alert('نمی‌توان تنها مکالمه موجود را حذف کرد.');
      return;
    }
    const nextSessions = sessions.filter(s => s.id !== id);
    setSessions(nextSessions);
    if (activeSessionId === id) {
      const fallbackId = nextSessions[0].id;
      setActiveSessionId(fallbackId);
    }
  };

  // ─── Documents ────────────────────────────────────────────────────────────
  const [documents, setDocuments] = useState([]);
  const [piiPreview, setPiiPreview] = useState('');
  const [piiAuditCounts, setPiiAuditCounts] = useState({});
  const [cosineThreshold, setCosineThreshold] = useState(0.50);
  const [stats, setStats] = useState({
    total_documents: 0,
    total_chunks: 0,
    total_queries_today: 0,
    average_response_time: 1.2,
    total_pii_masked: 0,
    pdf_count: 0,
    csv_excel_count: 0,
    other_count: 0,
    disk_usage_gb: 0.0
  });

  const fetchStats = async () => {
    try {
      const res = await apiFetch('http://localhost:8000/v1/knowledge/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching knowledge stats:', err);
    }
  };

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
            chunks: doc.chunk_count ?? 0,
            date: doc.created_at ? new Date(doc.created_at).toLocaleDateString('fa-IR') : '—',
            status: (doc.chunk_count ?? 0) > 0 ? 'ready' : 'pending',
            progress: (doc.chunk_count ?? 0) > 0 ? 100 : 0,
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

  // ─── Crawler ──────────────────────────────────────────────────────────────
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawlMaxPages, setCrawlMaxPages] = useState(50);
  const [crawlMaxDepth, setCrawlMaxDepth] = useState(3);
  const [crawlJsRender, setCrawlJsRender] = useState(false);
  const [crawlFollowExternal, setCrawlFollowExternal] = useState(false);
  const [crawlRobots, setCrawlRobots] = useState(true);
  const [crawlJobs, setCrawlJobs] = useState([]);
  const [crawlSubmitting, setCrawlSubmitting] = useState(false);
  const [crawlStatusFilter, setCrawlStatusFilter] = useState('');
  const crawlStatusFilterRef = useRef('');

  const fetchCrawlJobs = async () => {
    try {
      let url = 'http://localhost:8000/v1/crawl/jobs?limit=20';
      const currentFilter = crawlStatusFilterRef.current;
      if (currentFilter) {
        url += `&status=${currentFilter}`;
      }
      const res = await apiFetch(url);
      if (res && res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setCrawlJobs(data);
        }
      }
    } catch (err) {
      console.info('Crawl jobs fetch skipped (service may be unavailable):', err.message);
      // Do NOT re-throw — silent failure keeps the UI stable
    }
  };

  // ─── Integrations ─────────────────────────────────────────────────────────
  const [widgets, setWidgets] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [newWidgetName, setNewWidgetName] = useState('');
  const [newWidgetUrl, setNewWidgetUrl] = useState('');
  const [newWidgetMsg, setNewWidgetMsg] = useState('سلام! چطور می‌توانم کمک کنم؟ 💼✨');
  const [newWidgetTheme, setNewWidgetTheme] = useState('#1a2744');
  const [newWidgetAccent, setNewWidgetAccent] = useState('#c4894a');
  
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [widgetPreviewSelected, setWidgetPreviewSelected] = useState(null);

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

  // ─── Sync Config and intervals ───────────────────────────────────────────
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch('http://localhost:8000/v1/config');
        const data = await res.json();
        if (data) {
          setFeatures({
            checkCategories: data.services?.check_categories ?? false,
            piiRedaction: data.security?.pii_redaction ?? true,
            localGemma: data.services?.safety_auditor ?? false,
            hallucinationGuard: data.security?.strict_non_hallucination ?? false,
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
          if (data.cosine_threshold !== undefined) setCosineThreshold(data.cosine_threshold);
          if (data.telegram_bot_token) setTelegramBotToken(data.telegram_bot_token);
          if (data.api_keys) setProviderApiKeys(data.api_keys);
        }
      } catch (err) {
        console.error('Error loading configuration:', err);
      }
    };
    loadConfig();
  }, []);

  useEffect(() => {
    if (!currentUser) return;
    fetchIntegrations();
    if (activeScreen === 'dashboard' || activeScreen === 'knowledge' || activeScreen === 'upload') {
      fetchStats();
    }
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

  // ─── Crawler polling: stable interval using useRef ──────────────────────
  // NOTE: We do NOT put crawlJobs in deps — that caused a race condition where
  // every state update would cancel+recreate the interval, briefly showing an
  // empty list. Instead, we always poll every 4 s when on the crawler screen.
  const crawlPollRef = useRef(null);
  useEffect(() => {
    if (!currentUser || activeScreen !== 'crawler') {
      if (crawlPollRef.current) {
        clearInterval(crawlPollRef.current);
        crawlPollRef.current = null;
      }
      return;
    }
    // Fetch immediately on entering the crawler screen
    fetchCrawlJobs();
    // Then poll every 4 seconds
    crawlPollRef.current = setInterval(() => {
      fetchCrawlJobs();
    }, 4000);
    return () => {
      if (crawlPollRef.current) {
        clearInterval(crawlPollRef.current);
        crawlPollRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeScreen, currentUser]);

  useEffect(() => {
    if (currentUser && currentUser.role !== 'Admin' && (activeScreen === 'admin' || activeScreen === 'integrations')) {
      setActiveScreen('dashboard');
    }
  }, [activeScreen, currentUser]);

  // ─── Upload Process ──────────────────────────────────────────────────────
  const performUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const tempId = Date.now();
    const newDocPlaceholder = {
      id: tempId,
      name: file.name,
      size: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
      chunks: 0,
      date: new Date().toLocaleDateString('fa-IR'),
      status: 'uploading',
      progress: 20,
      ext: file.name.split('.').pop().toUpperCase(),
      min_role_required: 'Analyst'
    };
    
    setDocuments(prev => [newDocPlaceholder, ...prev]);

    try {
      const progressInterval = setInterval(() => {
        setDocuments(prev => prev.map(d => d.id === tempId && d.status === 'uploading'
          ? { ...d, progress: Math.min(d.progress + 15, 90) }
          : d
        ));
      }, 300);

      const res = await apiFetch('http://localhost:8000/v1/upload', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);
      const data = await res.json();

      if (res.ok) {
        setDocuments(prev => prev.map(d => d.id === tempId
          ? {
              ...d,
              id: data.file_id,
              status: 'ready',
              progress: 100,
              chunks: data.chunks_indexed
            }
          : d
        ));
        
        if (data.pii_preview) {
          setPiiPreview(data.pii_preview);
        } else {
          setPiiPreview(`[پیش‌نمایش ماسک شده فایل متنی یا جدول]:\nمحتوای فایل "${file.name}" با موفقیت پردازش شد و اطلاعات حساس PII در صورت وجود ماسک گردیدند.`);
        }
        
        if (data.pii_audit_counts) {
          setPiiAuditCounts(data.pii_audit_counts);
          const totalMasked = Object.values(data.pii_audit_counts).reduce((a, b) => a + b, 0);
          setPiiChecked(totalMasked === 0);
        } else {
          setPiiAuditCounts({});
          setPiiChecked(true);
        }

        alert(`سند "${file.name}" با موفقیت آپلود و در پایگاه دانش ایندکس شد.`);
        fetchDocuments();
        fetchStats();
      } else {
        setDocuments(prev => prev.filter(d => d.id !== tempId));
        alert(data.detail || 'خطا در آپلود و پردازش سند');
      }
    } catch (err) {
      console.error('File upload failed:', err);
      setDocuments(prev => prev.filter(d => d.id !== tempId));
      alert('خطا در ارتباط با سرور آپلود آریونکس.');
    }
  };

  const handleFileUpload = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (e && e.stopPropagation) e.stopPropagation();
    
    let file = null;
    if (e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      file = e.dataTransfer.files[0];
    }
    
    if (file) {
      await performUpload(file);
    } else {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = '.pdf,.docx,.doc,.txt,.csv,.json,.xlsx,.xls';
      fileInput.style.position = 'fixed';
      fileInput.style.top = '-9999px';
      fileInput.style.left = '-9999px';
      fileInput.style.opacity = '0';
      // Append to DOM so browser doesn't block/freeze the render thread
      document.body.appendChild(fileInput);
      fileInput.onchange = async (event) => {
        const selectedFile = event.target.files[0];
        // Remove from DOM immediately after selection
        try { document.body.removeChild(fileInput); } catch (_) {}
        if (selectedFile) {
          await performUpload(selectedFile);
        }
      };
      // Also clean up if dialog is cancelled (focus returns to window)
      const onFocus = () => {
        setTimeout(() => {
          try { document.body.removeChild(fileInput); } catch (_) {}
          window.removeEventListener('focus', onFocus);
        }, 300);
      };
      window.addEventListener('focus', onFocus);
      fileInput.click();
    }
  };

  // ─── Widgets and API keys ────────────────────────────────────────────────
  const handleCreateWidget = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
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
    if (e && e.preventDefault) e.preventDefault();
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

  // ─── Chat Messages Sending Logic ──────────────────────────────────────────
  const handleSendMessage = async (textOverride = null) => {
    const textToSend = textOverride !== null ? textOverride : inputText;
    if (!textToSend.trim()) return;

    const userMessage = { id: Date.now(), sender: 'user', text: textToSend, sources: [] };
    setChatMessages(prev => [...prev, userMessage]);
    const queryText = textToSend;
    if (textOverride === null) {
      setInputText('');
    }
    setIsAiLoading(true);

    const aiMsgId = Date.now() + 1;
    const aiPlaceholder = {
      id: aiMsgId,
      sender: 'ai',
      text: '',
      sources: [],
      isSafe: true,
      isRefusal: false,
      isLoading: true,
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
        body: JSON.stringify({ query: queryText, session_id: activeSessionId })
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
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              let data = line.slice(5);
              if (data.startsWith(' ')) data = data.slice(1);
              dataLine += data;
            }
          });

          const decodedData = dataLine.replace(/\\n/g, '\n');

          if (eventName === 'token') {
            // decodedData قبلاً شامل فاصلههاست، فقط اضافه میکنیم
            accumulated = accumulated + decodedData;
            setChatMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: accumulated, isLoading: false } : m));
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
                ? { ...m, isSafe: meta.is_safe ?? true, isRefusal, isLoading: false }
                : m));
            } catch (_) {}
          } else if (eventName === 'error') {
            console.error('Stream RAG error:', decodedData);
            setChatMessages(prev => prev.map(m => m.id === aiMsgId ? {
              ...m,
              text: `⚠️ خطا: ${decodedData}`,
              isRefusal: true,
              isLoading: false
            } : m));
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
        isLoading: false,
      } : m));
    }
  };

  return (
    <AppContext.Provider value={{
      activeScreen, setActiveScreen,
      currentUser, setCurrentUser,
      token, setToken,
      refreshToken, setRefreshToken,
      loginUsername, setLoginUsername,
      loginPassword, setLoginPassword,
      loginError, setLoginError,
      isLoginLoading, setIsLoginLoading,
      isSignupMode, setIsSignupMode,
      signupUsername, setSignupUsername,
      signupPassword, setSignupPassword,
      signupError, setSignupError,
      isSignupLoading, setIsSignupLoading,
      signupSuccess, setSignupSuccess,
      usersList, setUsersList,
      showInviteModal, setShowInviteModal,
      inviteUsername, setInviteUsername,
      invitePassword, setInvitePassword,
      inviteRole, setInviteRole,
      inviteError, setInviteError,
      piiChecked, setPiiChecked,
      systemInstruction, setSystemInstruction,
      features, setFeatures,
      ollamaEnabled, setOllamaEnabled,
      ollamaModel, setOllamaModel,
      ollamaEndpoint, setOllamaEndpoint,
      sessions, setSessions,
      activeSessionId, setActiveSessionId,
      createNewSession, deleteSession,
      chatMessages, setChatMessages,
      inputText, setInputText,
      isAiLoading, setIsAiLoading,
      documents, setDocuments,
      piiPreview, setPiiPreview,
      piiAuditCounts, setPiiAuditCounts,
      widgets, setWidgets,
      apiKeys, setApiKeys,
      newWidgetName, setNewWidgetName,
      newWidgetUrl, setNewWidgetUrl,
      newWidgetMsg, setNewWidgetMsg,
      newWidgetTheme, setNewWidgetTheme,
      newWidgetAccent, setNewWidgetAccent,
      newKeyName, setNewKeyName,
      generatedKey, setGeneratedKey,
      widgetPreviewSelected, setWidgetPreviewSelected,
      crawlUrl, setCrawlUrl,
      crawlMaxPages, setCrawlMaxPages,
      crawlMaxDepth, setCrawlMaxDepth,
      crawlJsRender, setCrawlJsRender,
      crawlFollowExternal, setCrawlFollowExternal,
      crawlRobots, setCrawlRobots,
      crawlJobs, setCrawlJobs,
      crawlSubmitting, setCrawlSubmitting,
      crawlStatusFilter,
      setCrawlStatusFilter: (val) => {
        crawlStatusFilterRef.current = val;
        setCrawlStatusFilter(val);
      },
      stats, fetchStats,
      cosineThreshold,
            apiFetch,
      handleLogin,
      handleSignup,
      handleLogout,
      fetchUsersList,
      handleInviteUser,
      fetchSystemInstruction,
      saveSystemInstruction,
      resetSystemInstruction,
      toggleFeature,
      toggleProvider,
      fetchDocuments,
      fetchCrawlJobs,
      fetchIntegrations,
      performUpload,
      handleFileUpload,
      handleCreateWidget,
      handleDeleteWidget,
      handleCreateAPIKey,
      handleDeleteAPIKey,
      handleSendMessage,
      telegramBotToken, setTelegramBotToken,
      handleSaveTelegramToken,
      providerApiKeys, setProviderApiKeys,
      handleSaveProviderApiKey
    }}>
      {children}
    </AppContext.Provider>
  );
};
