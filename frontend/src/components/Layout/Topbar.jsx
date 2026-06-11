import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';

export default function Topbar() {
  const { activeScreen, setActiveScreen, handleSendMessage } = useApp();
  const [searchVal, setSearchVal] = useState('');

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && searchVal.trim()) {
      handleSendMessage(searchVal.trim());
      setActiveScreen('chat');
      setSearchVal('');
    }
  };

  return (
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
        <input
          type="text"
          style={{
            border: 'none',
            background: 'transparent',
            outline: 'none',
            width: '100%',
            fontSize: '12.5px',
            color: 'var(--text-primary)',
            fontFamily: 'inherit'
          }}
          placeholder="جستجو در پایگاه دانش…"
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          onKeyDown={handleKeyDown}
        />
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
  );
}
