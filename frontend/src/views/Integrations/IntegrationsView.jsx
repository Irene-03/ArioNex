import React from 'react';
import { useApp } from '../../context/AppContext';

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
    handleSaveTelegramToken
  } = useApp();

  const [localToken, setLocalToken] = React.useState('');

  React.useEffect(() => {
    if (telegramBotToken) {
      setLocalToken(telegramBotToken);
    }
  }, [telegramBotToken]);

  return (
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

          {/* ربات تلگرام سازمانی */}
          <div className="card">
            <div className="card-title">🤖 ربات تلگرام سازمانی (Telegram Bot Integration)</div>
            <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '16px'}}>
              با فعال‌سازی ربات تلگرام، کاربران و کارکنان سازمان می‌توانند مستقیماً از طریق پیام‌رسان تلگرام با هوش مصنوعی و پایگاه دانش آریونکس گفتگو کنند.
            </div>

            {/* نمایش وضعیت ربات */}
            <div style={{
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              background: 'var(--gray-50)', 
              padding: '12px 14px', 
              borderRadius: 'var(--radius)', 
              marginBottom: '16px',
              border: '1px solid var(--gray-100)'
            }}>
              <span style={{fontSize: '12.5px', fontWeight: 'bold', color: 'var(--navy)'}}>وضعیت ربات تلگرام:</span>
              {!features.telegramBot ? (
                <span style={{fontSize: '12px', background: 'var(--color-danger-bg)', color: 'var(--color-danger)', padding: '2px 8px', borderRadius: '10px', fontWeight: '600'}}>
                  ❌ غیرفعال در تنظیمات سیستم
                </span>
              ) : !telegramBotToken ? (
                <span style={{fontSize: '12px', background: 'var(--color-warning-bg)', color: 'var(--color-warning)', padding: '2px 8px', borderRadius: '10px', fontWeight: '600'}}>
                  ⚠️ نیاز به پیکربندی توکن ربات
                </span>
              ) : (
                <span style={{fontSize: '12px', background: 'var(--color-success-bg)', color: 'var(--color-success)', padding: '2px 8px', borderRadius: '10px', fontWeight: '600'}}>
                  ✅ فعال و آماده به کار
                </span>
              )}
            </div>

            {/* فرم تنظیم توکن ربات */}
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--gray-50)', padding: '16px', borderRadius: 'var(--radius)', border: '1px solid var(--gray-100)'}}>
              <div style={{fontWeight: 'bold', fontSize: '13px', color: 'var(--navy)'}}>پیکربندی توکن تلگرام ربات:</div>
              <div style={{display: 'flex', gap: '10px'}}>
                <input
                  type="text"
                  className="chat-input-box"
                  style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px', flex: 1, minWidth: 0}}
                  placeholder="توکن ربات (مثال: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)"
                  value={localToken}
                  onChange={(e) => setLocalToken(e.target.value)}
                />
                <button 
                  onClick={() => handleSaveTelegramToken(localToken)} 
                  className="topbar-btn btn-primary" 
                  style={{padding: '10px 20px'}}
                  disabled={!features.telegramBot}
                >
                  ذخیره و فعال‌سازی
                </button>
              </div>

              {/* دستورالعمل راه‌اندازی */}
              <div style={{fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: '1.6', borderTop: '1px dashed var(--gray-200)', paddingTop: '10px', marginTop: '4px'}}>
                <div style={{fontWeight: 'bold', marginBottom: '6px', color: 'var(--navy)'}}>راهنمای راه‌اندازی ربات تلگرام:</div>
                <div style={{marginBottom: '4px'}}>۱. در تلگرام به شناسه <a href="https://t.me/BotFather" target="_blank" rel="noreferrer" style={{color: 'var(--copper)', textDecoration: 'none', fontWeight: 'bold'}}>BotFather@</a> پیام داده و دستور <code>/newbot</code> را ارسال کنید.</div>
                <div style={{marginBottom: '4px'}}>۲. نام و شناسه کاربری دلخواه خود را تعیین کرده و در نهایت <b>API Token</b> دریافتی را در فیلد بالا کپی کنید.</div>
                <div>۳. دکمه «ذخیره و فعال‌سازی» را بزنید. سپس کاربران با وارد شدن به شناسه ربات شما می‌توانند چت RAG را آغاز کنند.</div>
              </div>
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
                  style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px', minWidth: 0}}
                  placeholder="عنوان سایت (مثلاً: پورتال پشتیبانی)"
                  value={newWidgetName}
                  onChange={(e) => setNewWidgetName(e.target.value)}
                />
                <input
                  type="text"
                  className="chat-input-box"
                  style={{borderRadius: 'var(--radius)', fontSize: '12.5px', padding: '8px 12px', minWidth: 0}}
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
                  <span>رنگ ثانویه:</span>
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
  );
}
