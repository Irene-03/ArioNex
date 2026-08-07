import React from 'react';
import {
  KeyRound,
  Globe,
  ShieldCheck,
  Plus,
  Trash2,
  Copy,
  BookOpen,
  Bot,
  MessageSquareText,
  X,
  Eye,
  Clipboard,
  CheckCircle2,
  AlertTriangle,
  CircleX,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';
import { useToast, useConfirm } from '../../components/ui/ToastProvider';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';

export default function IntegrationsView() {
  const {
    apiKeys,
    newKeyName,
    setNewKeyName,
    generatedKey,
    widgets,
    newWidgetName,
    setNewWidgetName,
    newWidgetUrl,
    setNewWidgetUrl,
    newWidgetMsg,
    setNewWidgetMsg,
    newWidgetTheme,
    setNewWidgetTheme,
    newWidgetAccent,
    setNewWidgetAccent,
    widgetPreviewSelected,
    setWidgetPreviewSelected,
    features,
    handleCreateAPIKey,
    handleDeleteAPIKey,
    handleCreateWidget,
    handleDeleteWidget,
    telegramBotToken,
    handleSaveTelegramToken,
  } = useApp();
  const toast = useToast();
  const confirmDialog = useConfirm();
  const [localToken, setLocalToken] = React.useState('');

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (telegramBotToken) setLocalToken(telegramBotToken);
  }, [telegramBotToken]);

  const copyText = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success('کپی شد', `${label} در حافظه کپی شد.`);
  };

  const onDeleteKey = async (key) => {
    const confirmed = await confirmDialog({
      title: 'ابطال کلید API',
      desc: `با ابطال کلید «${key.name}»، سیستم‌های متصل با آن از دسترسی خارج می‌شوند.`,
      confirmLabel: 'ابطال کلید',
      cancelLabel: 'انصراف',
    });
    if (!confirmed) return;
    await handleDeleteAPIKey(key.id);
  };

  const onDeleteWidget = async (w) => {
    const confirmed = await confirmDialog({
      title: 'حذف ابزارک',
      desc: `آیا از حذف ابزارک «${w.name}» اطمینان دارید؟`,
      confirmLabel: 'حذف',
      cancelLabel: 'انصراف',
    });
    if (!confirmed) return;
    await handleDeleteWidget(w.id);
  };

  const telegramStatus = !features.telegramBot
    ? { variant: 'danger', label: 'غیرفعال', icon: CircleX }
    : !telegramBotToken
      ? { variant: 'warning', label: 'نیاز به پیکربندی توکن', icon: AlertTriangle }
      : { variant: 'success', label: 'فعال و آماده به کار', icon: CheckCircle2 };

  const TelegramIcon = telegramStatus.icon;

  const statCards = [
    { label: 'کلیدهای فعال API', value: `${apiKeys.length} عدد`, hint: 'دسترسی امن به سیستم RAG خارج سازمان', icon: KeyRound, color: 'var(--color-success)' },
    { label: 'ابزارک‌های وب‌سایت فعال', value: `${widgets.length} وب‌سایت`, hint: 'سرویس‌دهی پاپ‌آپ روی دامنه‌ها', icon: Globe, color: 'var(--color-info)' },
    { label: 'احراز هویت ادغام‌ها', value: features.restApi ? 'فعال و امن' : 'غیرفعال', hint: 'کنترل‌شده توسط کنسول مدیریت', icon: ShieldCheck, color: 'var(--copper)' },
  ];

  return (
    <div className="screen fade-in">
      <PageHeader
        icon={<KeyRound size={20} style={{ color: 'var(--copper)' }} />}
        title="یکپارچه‌سازی و کانال‌های خروجی"
      />

      <div className="stats-row">
        {statCards.map(card => {
          const Icon = card.icon;
          return (
            <div className="stat-card" key={card.label} style={{ borderTop: `3px solid ${card.color}` }}>
              <div className="stat-label">
                <Icon />
                {card.label}
              </div>
              <div className="stat-value">{card.value}</div>
              <div className="stat-change" style={{ color: 'var(--text-muted)' }}>{card.hint}</div>
            </div>
          );
        })}
      </div>

      <div className="two-col">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* API Keys */}
          <div className="ax-card">
            <div className="ax-card__title">
              <KeyRound size={16} style={{ color: 'var(--copper)' }} />
              مدیریت کلیدهای دسترسی API
            </div>
            <div className="ax-card__desc" style={{ marginBottom: 16 }}>
              کلیدهای دسترسی جهت اتصال امن سیستم‌های خارجی نظیر CRM و پورتال‌های درون‌سازمانی به خط لوله RAG استفاده می‌شوند.
            </div>

            <form onSubmit={handleCreateAPIKey} style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
              <input
                type="text"
                className="ax-input"
                style={{ flex: 1 }}
                placeholder="نام یا عنوان کلید جدید (مثلاً: CRM وب‌سایت)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
              <button type="submit" className="ax-btn ax-btn--primary">
                <Plus size={15} /> ایجاد کلید
              </button>
            </form>

            {generatedKey && (
              <div style={{ background: 'var(--color-warning-bg)', border: '1px solid rgba(180,83,9,0.25)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 20 }}>
                <div style={{ color: 'var(--color-warning)', fontWeight: 'bold', fontSize: 13, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <KeyRound size={14} /> کلید API با موفقیت تولید شد
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                  این کلید فقط همین یک بار نمایش داده می‌شود؛ لطفاً آن را در محل امنی ذخیره کنید.
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#fff', padding: '8px 12px', borderRadius: 4, border: '1px solid var(--gray-200)', fontFamily: 'monospace', direction: 'ltr' }}>
                  <span style={{ flex: 1, color: 'var(--text-primary)', fontSize: 13, overflowX: 'auto', whiteSpace: 'nowrap' }}>{generatedKey}</span>
                  <button className="ax-btn ax-btn--ghost ax-btn--sm" onClick={() => copyText(generatedKey, 'کلید API')}>
                    <Copy size={13} /> کپی
                  </button>
                </div>
              </div>
            )}

            <div className="ax-table-wrap">
              <table className="ax-table">
                <thead>
                  <tr>
                    <th>نام کلید</th>
                    <th>کلید دسترسی (Masked)</th>
                    <th>تاریخ ایجاد</th>
                    <th style={{ textAlign: 'center' }}>عملیات</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '24px 16px', color: 'var(--text-muted)', fontSize: 13 }}>
                        هیچ کلید API تعریف نشده است.
                      </td>
                    </tr>
                  ) : (
                    apiKeys.map(key => (
                      <tr key={key.id}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{key.name}</td>
                        <td style={{ fontFamily: 'monospace', direction: 'ltr', fontSize: 12 }}>{key.api_key}</td>
                        <td style={{ color: 'var(--text-muted)' }}>{key.created_at}</td>
                        <td style={{ textAlign: 'center' }}>
                          <button className="ax-btn ax-btn--danger-ghost ax-btn--sm" onClick={() => onDeleteKey(key)}>
                            <Trash2 size={13} /> ابطال
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* REST API docs */}
          <div className="ax-card">
            <div className="ax-card__title">
              <BookOpen size={16} style={{ color: 'var(--copper)' }} />
              مستندات اتصال REST API
            </div>
            <div className="ax-card__desc" style={{ marginBottom: 12 }}>
              برای ارسال پرسش‌های هوشمند از خارج سیستم، درخواست را با هدر احراز هویت ارسال کنید:
            </div>
            <div style={{ background: 'var(--navy-deep)', padding: 14, borderRadius: 'var(--radius)', color: '#fff', fontSize: 12, fontFamily: 'monospace', direction: 'ltr', textAlign: 'left', overflowX: 'auto' }}>
              <pre style={{ margin: 0 }}>
{`curl -X POST "${API_BASE}/v1/query" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: anx_live_YOUR_API_KEY_HERE" \\
  -d '{
    "query": "سود خالص شرکت در سال مالی گذشته چقدر بوده است؟",
    "session_id": "external_crm_user"
  }'`}
              </pre>
            </div>
          </div>

          {/* Telegram bot */}
          <div className="ax-card">
            <div className="ax-card__title">
              <Bot size={16} style={{ color: 'var(--color-info)' }} />
              ربات تلگرام سازمانی
            </div>
            <div className="ax-card__desc" style={{ marginBottom: 16 }}>
              کارکنان سازمان می‌توانند مستقیماً از طریق تلگرام با هوش مصنوعی و پایگاه دانش گفتگو کنند.
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'var(--gray-50)', padding: '12px 14px', borderRadius: 'var(--radius)', marginBottom: 16, border: '1px solid var(--gray-100)' }}>
              <span style={{ fontSize: 12.5, fontWeight: 'bold', color: 'var(--heading)' }}>وضعیت ربات:</span>
              <Badge variant={telegramStatus.variant}>
                <TelegramIcon size={12} /> {telegramStatus.label}
              </Badge>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, background: 'var(--gray-50)', padding: 16, borderRadius: 'var(--radius)', border: '1px solid var(--gray-100)' }}>
              <div style={{ fontWeight: 'bold', fontSize: 13, color: 'var(--heading)' }}>پیکربندی توکن ربات:</div>
              <div style={{ display: 'flex', gap: 10 }}>
                <input
                  type="text"
                  className="ax-input"
                  style={{ flex: 1, fontSize: 12.5 }}
                  placeholder="توکن ربات (مثال: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)"
                  value={localToken}
                  onChange={(e) => setLocalToken(e.target.value)}
                />
                <button className="ax-btn ax-btn--primary" onClick={() => handleSaveTelegramToken(localToken)} disabled={!features.telegramBot}>
                  ذخیره و فعال‌سازی
                </button>
              </div>

              <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.8, borderTop: '1px dashed var(--gray-200)', paddingTop: 10 }}>
                <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--heading)' }}>راهنمای راه‌اندازی:</div>
                <div>۱. در تلگرام به BotFather پیام داده و دستور <code>/newbot</code> را ارسال کنید.</div>
                <div>۲. نام و شناسه ربات را تعیین کرده و API Token را کپی کنید.</div>
                <div>۳. دکمه «ذخیره و فعال‌سازی» را بزنید.</div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Widgets */}
          <div className="ax-card">
            <div className="ax-card__title">
              <MessageSquareText size={16} style={{ color: 'var(--copper)' }} />
              مدیریت ابزارک چت پاپ‌آپ
            </div>
            <div className="ax-card__desc" style={{ marginBottom: 16 }}>
              کاربران می‌توانند بدون نصب برنامه، بر روی هر وب‌سایتی به هوش مصنوعی سازمان دسترسی داشته باشند.
            </div>

            <form onSubmit={handleCreateWidget} style={{ display: 'flex', flexDirection: 'column', gap: 12, background: 'var(--gray-50)', padding: 16, borderRadius: 'var(--radius)', border: '1px solid var(--gray-100)', marginBottom: 20 }}>
              <div style={{ fontWeight: 'bold', fontSize: 13, color: 'var(--heading)' }}>ثبت دامنه جدید برای پاپ‌آپ:</div>
              <div className="grid-2-col" style={{ gap: 10 }}>
                <input type="text" className="ax-input" style={{ fontSize: 12.5 }} placeholder="عنوان سایت (مثلاً: پورتال پشتیبانی)" value={newWidgetName} onChange={(e) => setNewWidgetName(e.target.value)} />
                <input type="text" className="ax-input" style={{ fontSize: 12.5 }} placeholder="دامنه یا آدرس (مثلاً: support.company.ir)" value={newWidgetUrl} onChange={(e) => setNewWidgetUrl(e.target.value)} />
              </div>
              <input type="text" className="ax-input" style={{ fontSize: 12.5 }} placeholder="پیام خوش‌آمدگویی پیش‌فرض ابزارک" value={newWidgetMsg} onChange={(e) => setNewWidgetMsg(e.target.value)} />

              <div style={{ display: 'flex', gap: 15, alignItems: 'center', fontSize: 12.5, color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>رنگ اصلی تم:</span>
                  <input type="color" value={newWidgetTheme} onChange={(e) => setNewWidgetTheme(e.target.value)} style={{ border: 'none', background: 'none', cursor: 'pointer', width: 28, height: 28 }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>رنگ ثانویه:</span>
                  <input type="color" value={newWidgetAccent} onChange={(e) => setNewWidgetAccent(e.target.value)} style={{ border: 'none', background: 'none', cursor: 'pointer', width: 28, height: 28 }} />
                </div>
              </div>

              <button type="submit" className="ax-btn ax-btn--primary" style={{ width: '100%' }}>
                <Plus size={15} /> ثبت و تولید کد ابزارک
              </button>
            </form>

            <div style={{ fontWeight: 'bold', fontSize: 13, color: 'var(--heading)', marginBottom: 10 }}>وب‌سایت‌های متصل:</div>
            <div className="ax-table-wrap" style={{ marginBottom: 20 }}>
              {widgets.length === 0 ? (
                <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>هیچ ابزارکی ثبت نشده است.</div>
              ) : (
                widgets.map(w => (
                  <div
                    key={w.id}
                    className={`ft-row ${widgetPreviewSelected?.id === w.id ? 'active-chat' : ''}`}
                    style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 14px', cursor: 'pointer' }}
                    onClick={() => setWidgetPreviewSelected(w)}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{w.name}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{w.url}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: w.theme_color }} title="رنگ تم" />
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: w.accent_color }} title="رنگ ثانویه" />
                      <button className="icon-btn icon-btn--danger" onClick={(e) => { e.stopPropagation(); onDeleteWidget(w); }} title="حذف ابزارک" aria-label="حذف ابزارک">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {widgetPreviewSelected && (
              <div style={{ background: 'var(--gray-50)', border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: 14 }}>
                <div style={{ fontWeight: 'bold', fontSize: 13, color: 'var(--heading)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Clipboard size={14} style={{ color: 'var(--copper)' }} /> کد اسکریپت برای «{widgetPreviewSelected.name}»
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 10 }}>
                  اسکریپت زیر را در انتهای تگ <code>&lt;body&gt;</code> سایت قرار دهید.
                </div>
                <div style={{ background: 'var(--navy-deep)', padding: 12, borderRadius: 'var(--radius)', color: '#fff', fontSize: 11.5, fontFamily: 'monospace', direction: 'ltr', textAlign: 'left', overflowX: 'auto', marginBottom: 10 }}>
                  <pre style={{ margin: 0 }}>
{`<!-- ArioNex Popup Chat Assistant Widget for ${widgetPreviewSelected.url} -->
<script src="${API_BASE}/v1/widget.js?website=${encodeURIComponent(widgetPreviewSelected.url)}" async></script>`}
                  </pre>
                </div>
                <button
                  className="ax-btn ax-btn--ghost ax-btn--block ax-btn--sm"
                  onClick={() => {
                    const embedCode = `<!-- ArioNex Popup Chat Assistant Widget for ${widgetPreviewSelected.url} -->\n<script src="${API_BASE}/v1/widget.js?website=${encodeURIComponent(widgetPreviewSelected.url)}" async></script>`;
                    copyText(embedCode, 'کد اسکریپت پاپ‌آپ');
                  }}
                >
                  <Copy size={13} /> کپی کد اسکریپت
                </button>
              </div>
            )}
          </div>

          {/* Live widget preview */}
          {widgetPreviewSelected && (
            <div className="ax-card" style={{ border: '1px solid var(--border-copper)', overflow: 'hidden', padding: 0 }}>
              <div style={{ background: 'var(--navy-deep)', color: '#fff', padding: '12px 16px', fontWeight: 'bold', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Eye size={15} /> پیش‌نمایش زنده ابزارک
                </span>
                <span style={{ fontSize: 11, background: widgetPreviewSelected.accent_color, color: '#fff', padding: '2px 8px', borderRadius: 999 }}>{widgetPreviewSelected.url}</span>
              </div>

              <div style={{ padding: 20, background: '#f5f5f5', position: 'relative', height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundImage: 'radial-gradient(#ddd 1px, transparent 1px)', backgroundSize: '16px 16px' }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', zIndex: 1, textShadow: '0 1px 0 #fff' }}>نمای شبیه‌سازی‌شده وب‌سایت شما</div>

                <div style={{ position: 'absolute', bottom: 20, left: 20, width: 240, height: 240, borderRadius: 12, backgroundColor: '#fff', boxShadow: '0 8px 24px rgba(0,0,0,0.15)', border: `1px solid ${widgetPreviewSelected.accent_color}`, display: 'flex', flexDirection: 'column', overflow: 'hidden', direction: 'rtl', fontFamily: "'Vazirmatn', 'Inter', sans-serif" }}>
                  <div style={{ backgroundColor: widgetPreviewSelected.theme_color, color: '#fff', padding: '8px 12px', fontSize: 11.5, fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', borderBottom: `2px solid ${widgetPreviewSelected.accent_color}` }}>
                    <span>🛡️ دستیار هوشمند آریونکس</span>
                    <X size={12} />
                  </div>
                  <div style={{ flex: 1, padding: 10, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ alignSelf: 'flex-start', backgroundColor: '#f1f1f1', color: '#333', padding: '6px 10px', borderRadius: 8, fontSize: 11, lineHeight: 1.5, maxWidth: '90%' }}>
                      {widgetPreviewSelected.welcome_message || 'سلام! چطور می‌توانم کمک کنم؟'}
                    </div>
                  </div>
                  <div style={{ padding: 8, borderTop: '1px solid #eee', display: 'flex', gap: 6, background: '#fafafa' }}>
                    <input type="text" disabled style={{ flex: 1, border: '1px solid #ddd', borderRadius: 4, padding: 4, fontSize: 10.5 }} placeholder="تایپ کنید..." />
                    <button style={{ backgroundColor: widgetPreviewSelected.theme_color, border: 'none', color: '#fff', borderRadius: 4, padding: '4px 8px', fontSize: 10 }}>ارسال</button>
                  </div>
                </div>

                <div style={{ position: 'absolute', bottom: 20, right: 20, width: 44, height: 44, borderRadius: '50%', background: `linear-gradient(135deg, ${widgetPreviewSelected.theme_color} 0%, #000 100%)`, boxShadow: '0 4px 12px rgba(0,0,0,0.2)', border: `2px solid ${widgetPreviewSelected.accent_color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: widgetPreviewSelected.accent_color, fontSize: 20 }}>
                  💬
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
