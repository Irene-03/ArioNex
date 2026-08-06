import { useState } from 'react';
import { Search, Plus, UploadCloud, Circle } from 'lucide-react';
import { useApp } from '../../context/AppContext';

const pageMeta = {
  dashboard: { title: 'داشبورد اصلی', subtitle: 'نمای کلی وضعیت سامانه و دانش سازمانی' },
  chat: { title: 'دستیار دانش هوشمند', subtitle: 'حالت RAG امن — پاسخ مبتنی بر اسناد سازمان' },
  knowledge: { title: 'پایگاه دانش', subtitle: 'مدیریت و توزیع منابع دانش' },
  upload: { title: 'آپلود اسناد', subtitle: 'فیلتر حریم خصوصی و درون‌ریزی امن' },
  categories: { title: 'دسته‌بندی‌ها', subtitle: 'مدیریت عامل دسته‌بندی اسناد' },
  crawler: { title: 'کرالر وب‌سایت', subtitle: 'استخراج خودکار دانش از وب' },
  admin: { title: 'پنل مدیریت', subtitle: 'حریم خصوصی، امنیت و تنظیمات سامانه' },
  integrations: { title: 'یکپارچه‌سازی', subtitle: 'کانال‌های خروجی و مستندات اتصال' },
};

export default function Topbar() {
  const { activeScreen, setActiveScreen, handleSendMessage } = useApp();
  const [searchVal, setSearchVal] = useState('');
  const meta = pageMeta[activeScreen] || pageMeta.dashboard;

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && searchVal.trim()) {
      handleSendMessage(searchVal.trim());
      setActiveScreen('chat');
      setSearchVal('');
    }
  };

  return (
    <div className="topbar">
      <div style={{ minWidth: 0, flex: 1 }}>
        <div className="page-title">{meta.title}</div>
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {meta.subtitle}
        </div>
      </div>

      <div className="topbar-search">
        <Search size={14} className="search-icon" style={{ color: 'var(--gray-400)' }} />
        <input
          type="text"
          style={{
            border: 'none',
            background: 'transparent',
            outline: 'none',
            width: '100%',
            fontSize: '12.5px',
            color: 'var(--text-primary)',
            fontFamily: 'inherit',
          }}
          placeholder="جستجو در پایگاه دانش…"
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          onKeyDown={handleKeyDown}
        />
      </div>

      <button className="topbar-btn btn-ghost" onClick={() => setActiveScreen('chat')}>
        <Plus size={15} /> <span className="btn-text">پرسش جدید</span>
      </button>

      <button className="topbar-btn btn-primary" onClick={() => setActiveScreen('upload')}>
        <UploadCloud size={15} /> <span className="btn-text">آپلود سریع</span>
      </button>

      <Circle size={10} fill="var(--color-success)" color="var(--color-success)" title="سیستم آنلاین" aria-label="سیستم آنلاین" />
    </div>
  );
}
