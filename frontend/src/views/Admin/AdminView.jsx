import React from 'react';
import { useApp } from '../../context/AppContext';
import { OLLAMA_MODELS } from '../../constants/models';

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
    toggleProvider
  } = useApp();

  return (
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
  );
}
