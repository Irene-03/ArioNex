import React from 'react';
import {
  Settings2,
  ShieldCheck,
  Users,
  MessageSquare,
  Plug,
  HardDrive,
  Brain,
  UserPlus,
  RefreshCcw,
  Save,
  Zap,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { OLLAMA_MODELS } from '../../constants/models';
import { API_BASE } from '../../api/config';
import { useToast } from '../../components/ui/ToastProvider';
import Switch from '../../components/ui/Switch';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';

const PROVIDER_LABELS = {
  openai: 'OpenAI direct (GPT-4o, GPT-4o-mini)',
  openrouter: 'OpenRouter API (دسترسی تجاری متمرکز)',
  google: 'Google Gemini API (Flash & Pro)',
  anthropic: 'Anthropic Claude API (Sonnet & Haiku)',
  deepseek: 'DeepSeek API (مدل ارزان و قدرتمند)',
  gapgpt: 'GapGPT API (پروایدر ایرانی بدون تحریم)',
  avalai: 'AvalAI API (پروایدر ایرانی همکار)',
  hormouz: 'Hormouz API (دروازه ۳۵۰+ مدل · streaming)',
};

const PROVIDER_KEYS = ['openai', 'openrouter', 'google', 'anthropic', 'deepseek', 'gapgpt', 'avalai', 'hormouz'];

export default function AdminView() {
  const {
    features,
    toggleFeature,
    usersList,
    setShowInviteModal,
    systemInstruction,
    setSystemInstruction,
    saveSystemInstruction,
    resetSystemInstruction,
    ollamaEnabled,
    setOllamaEnabled,
    ollamaModel,
    setOllamaModel,
    ollamaEndpoint,
    setOllamaEndpoint,
    toggleProvider,
    providerApiKeys,
    handleSaveProviderApiKey,
  } = useApp();
  const toast = useToast();

  const [keysInput, setKeysInput] = React.useState({
    openai: '', openrouter: '', anthropic: '', google: '',
    deepseek: '', gapgpt: '', avalai: '', hormouz: '',
  });

  const securityToggles = [
    { key: 'piiRedaction', label: 'پوشش خودکار اطلاعات حساس شخصی (PII Redaction)' },
    { key: 'localGemma', label: 'بازرس ایمنی داده‌ها (مدل محلی Gemma-2b)' },
    { key: 'hallucinationGuard', label: 'محافظت هوشمند در برابر توهم‌پردازی' },
    { key: 'externalApiBlocked', label: 'مسدودسازی فراخوانی‌های API خارجی' },
    { key: 'strictCitation', label: 'الزام به استناد دقیق به خط و شماره صفحه منبع' },
  ];

  const channelToggles = [
    { key: 'telegramBot', label: 'ربات تلگرام سازمانی', desc: 'ارتباط کاربران از طریق پیام‌رسان تلگرام' },
    { key: 'popupWidget', label: 'ابزارک پاپ‌آپ وب‌سایت‌ها', desc: 'چت هوشمند شناور روی دامنه‌ها' },
    { key: 'restApi', label: 'دسترسی از طریق وب‌سرویس REST API', desc: 'اتصال امن سیستم‌های خارجی' },
  ];

  const testOllama = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/config/test-ollama`, {
        method: 'POST',
        signal: AbortSignal.timeout(8000),
      });
      const data = await res.json();
      if (data?.connected) {
        toast.success('اتصال موفق', `${data.model_count} مدل روی سرور Ollama یافت شد.`);
      } else {
        toast.error('اتصال ناموفق', data?.error || 'سرور Ollama در دسترس نیست.');
      }
    } catch {
      toast.error('اتصال ناموفق', 'مطمئن شوید سرویس Ollama در حال اجراست.');
    }
  };

  return (
    <div className="screen fade-in">
      <PageHeader
        icon={<Settings2 size={20} style={{ color: 'var(--copper)' }} />}
        title="کنسول مدیریت سیستم"
      />

      <div className="admin-grid">
        <div className="admin-card">
          <div className="admin-card-title">
            <ShieldCheck size={17} />
            کنترل‌های حریم خصوصی و امنیت
          </div>
          {securityToggles.map(t => (
            <div className="toggle-row" key={t.key}>
              <span className="toggle-label">{t.label}</span>
              <Switch checked={!!features[t.key]} onChange={() => toggleFeature(t.key)} aria-label={t.label} />
            </div>
          ))}
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <Users size={17} />
            دسترسی کاربران و مدیریت مجوزها
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 200, overflowY: 'auto', marginBottom: 16 }}>
            {usersList.map((usr, i) => (
              <div className="permission-row" key={i}>
                <div className="perm-user">
                  <div className="perm-av" style={{ textTransform: 'uppercase' }}>{usr.username.substring(0, 2)}</div>
                  {usr.username}
                </div>
                <Badge variant={usr.role === 'Admin' ? 'warning' : 'info'}>
                  {usr.role === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}
                </Badge>
              </div>
            ))}
          </div>
          <button className="ax-btn ax-btn--secondary ax-btn--block" onClick={() => setShowInviteModal(true)}>
            <UserPlus size={15} /> ثبت کاربر جدید در سازمان
          </button>
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <MessageSquare size={17} />
            مدیریت دستورالعمل پایه دستیار
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.7 }}>
            تعیین لحن، محدودیت‌ها و دستورات پایه برای مدل در تعامل با کاربران.
          </div>
          <textarea
            className="ax-textarea"
            style={{ width: '100%', minHeight: 110, direction: 'rtl' }}
            value={systemInstruction}
            onChange={(e) => setSystemInstruction(e.target.value)}
          />
          <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
            <button className="ax-btn ax-btn--primary" style={{ flex: 1 }} onClick={saveSystemInstruction}>
              <Save size={15} /> ذخیره دستورالعمل
            </button>
            <button className="ax-btn ax-btn--ghost" style={{ flex: 1 }} onClick={resetSystemInstruction}>
              <RefreshCcw size={15} /> بازنشانی به پیش‌فرض
            </button>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <Plug size={17} />
            کانال‌های خروجی فعال
          </div>
          {channelToggles.map(t => (
            <div className="toggle-row" key={t.key}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span className="toggle-label">{t.label}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t.desc}</span>
              </div>
              <Switch checked={!!features[t.key]} onChange={() => toggleFeature(t.key)} aria-label={t.label} />
            </div>
          ))}
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <HardDrive size={17} />
            حالت محلی — Ollama (بدون اینترنت)
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 14, lineHeight: 1.7 }}>
            با فعال‌سازی، بک‌اند از مدل محلی به‌جای API خارجی استفاده می‌کند؛ مناسب محیط‌های کاملاً آفلاین.
          </div>
          <div className="toggle-row">
            <span className="toggle-label">فعال‌سازی حالت محلی Ollama</span>
            <Switch
              checked={ollamaEnabled}
              onChange={() => {
                const next = !ollamaEnabled;
                setOllamaEnabled(next);
                fetch(`${API_BASE}/v1/config`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ providers: { ollama: next } }),
                }).catch(() => {});
              }}
              aria-label="فعال‌سازی حالت محلی"
            />
          </div>
          {ollamaEnabled && (
            <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="ax-field">
                <label className="ax-label">مدل زبانی محلی:</label>
                <select
                  className="ax-select"
                  value={ollamaModel}
                  onChange={(e) => {
                    setOllamaModel(e.target.value);
                    fetch(`${API_BASE}/v1/config`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ ollama_model: e.target.value }),
                    }).catch(() => {});
                  }}
                >
                  {OLLAMA_MODELS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
              </div>
              <div className="ax-field">
                <label className="ax-label">آدرس Ollama Server:</label>
                <input
                  type="text"
                  className="ax-input ax-input--ltr"
                  value={ollamaEndpoint}
                  onChange={(e) => setOllamaEndpoint(e.target.value)}
                  placeholder="http://localhost:11434"
                />
              </div>
              <button className="ax-btn ax-btn--primary ax-btn--block" onClick={testOllama}>
                <Zap size={15} /> آزمون اتصال به Ollama
              </button>
              <div style={{ background: 'var(--color-info-bg)', border: '1px solid rgba(90,156,244,0.3)', borderRadius: 'var(--radius)', padding: 12, fontSize: 12, color: 'var(--color-info)', lineHeight: 1.8 }}>
                <strong>راهنمای نصب:</strong>
                <div>۱. از ollama.com نصب کنید</div>
                <div>۲. <code>ollama pull gemma3:4b</code> را اجرا کنید</div>
                <div>۳. این حالت را فعال کرده و «آزمون اتصال» بزنید</div>
              </div>
            </div>
          )}
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <Brain size={17} />
            پروایدرهای هوش مصنوعی فعال
          </div>
          {PROVIDER_KEYS.map((key, idx) => {
            const featureKey = `provider${key.charAt(0).toUpperCase()}${key.slice(1)}`;
            const enabled = !!features[featureKey];
            const isLast = idx === PROVIDER_KEYS.length - 1;
            return (
              <div key={key}>
                <div className="toggle-row" style={{ borderBottom: enabled || isLast ? 'none' : '1px solid var(--gray-100)', paddingBottom: enabled ? 4 : 14 }}>
                  <span className="toggle-label">{PROVIDER_LABELS[key]}</span>
                  <Switch checked={enabled} onChange={() => toggleProvider(key)} aria-label={PROVIDER_LABELS[key]} />
                </div>
                {enabled && (
                  <div style={{ display: 'flex', gap: 8, padding: '0 10px 14px', borderBottom: isLast ? 'none' : '1px solid var(--gray-100)' }}>
                    <input
                      type="password"
                      className="ax-input"
                      style={{ flex: 1, fontSize: 12, padding: '6px 10px' }}
                      placeholder={providerApiKeys[key] ? '•••••••••••• (کلید ذخیره شده)' : `کلید API برای ${key} را وارد کنید`}
                      value={keysInput[key]}
                      onChange={(e) => setKeysInput(prev => ({ ...prev, [key]: e.target.value }))}
                    />
                    <button className="ax-btn ax-btn--ghost ax-btn--sm" onClick={() => handleSaveProviderApiKey(key, keysInput[key])}>
                      ذخیره
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
