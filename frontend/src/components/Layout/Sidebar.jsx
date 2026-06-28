import React from 'react';
import { useApp } from '../../context/AppContext';

export default function Sidebar() {
  const { activeScreen, setActiveScreen, currentUser, handleLogout } = useApp();

  return (
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
          className={`nav-item ${activeScreen === 'categories' ? 'active' : ''}`}
          onClick={() => setActiveScreen('categories')}
        >
          <span>🗂️</span> دسته‌بندی‌ها
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
  );
}
