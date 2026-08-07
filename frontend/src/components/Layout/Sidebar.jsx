import {
  LayoutDashboard,
  MessageSquareText,
  Database,
  UploadCloud,
  FolderTree,
  Radar,
  Settings2,
  Plug,
  ScrollText,
  LogOut,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function Sidebar() {
  const { activeScreen, setActiveScreen, currentUser, handleLogout } = useApp();

  const navItems = [
    {
      section: 'فضای کاری',
      items: [
        { key: 'dashboard', label: 'داشبورد', icon: LayoutDashboard },
        { key: 'chat', label: 'دستیار هوش مصنوعی', icon: MessageSquareText },
        { key: 'knowledge', label: 'پایگاه دانش', icon: Database },
        { key: 'upload', label: 'آپلود اسناد', icon: UploadCloud },
        { key: 'categories', label: 'دسته‌بندی‌ها', icon: FolderTree },
        { key: 'crawler', label: 'کرالر وب‌سایت', icon: Radar },
      ],
    },
    ...(currentUser?.role === 'Admin'
      ? [
          {
            section: 'مدیریت سیستم',
            items: [
              { key: 'admin', label: 'پنل مدیریت', icon: Settings2 },
              { key: 'audit', label: 'لاگ حسابرسی', icon: ScrollText },
              { key: 'integrations', label: 'یکپارچه‌سازی', icon: Plug },
            ],
          },
        ]
      : []),
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <svg className="logo-mark" viewBox="0 0 32 32" fill="none" width="28" height="28">
          <polygon points="16,2 28,26 4,26" fill="none" stroke="#c4894a" strokeWidth="2.5" />
          <polygon points="16,9 22,26 10,26" fill="none" stroke="#c4894a" strokeWidth="1.5" opacity="0.5" />
        </svg>
        <span className="logo-text">آریو<span>نکس</span></span>
      </div>

      {navItems.map(group => (
        <div className="sidebar-section" key={group.section}>
          <div className="sidebar-label">{group.section}</div>
          {group.items.map(item => {
            const Icon = item.icon;
            return (
              <div
                key={item.key}
                className={`nav-item ${activeScreen === item.key ? 'active' : ''}`}
                onClick={() => setActiveScreen(item.key)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveScreen(item.key); }}
              >
                <Icon />
                {item.label}
              </div>
            );
          })}
        </div>
      ))}

      <div className="sidebar-bottom">
        <div className="user-card">
          <div className="user-avatar" style={{ textTransform: 'uppercase' }}>
            {currentUser?.username?.substring(0, 2) || 'UR'}
          </div>
          <div className="user-info">
            <div className="user-name">{currentUser?.username}</div>
            <div className="user-role">{currentUser?.role === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}</div>
          </div>
          <button
            className="icon-btn"
            onClick={handleLogout}
            style={{ color: 'var(--copper-light)', fontSize: '16px', padding: '4px' }}
            title="خروج از حساب"
            aria-label="خروج از حساب"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
