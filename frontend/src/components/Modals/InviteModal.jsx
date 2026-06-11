import React from 'react';
import { useApp } from '../../context/AppContext';

export default function InviteModal() {
  const {
    showInviteModal,
    setShowInviteModal,
    inviteUsername,
    setInviteUsername,
    invitePassword,
    setInvitePassword,
    inviteRole,
    setInviteRole,
    inviteError,
    handleInviteUser
  } = useApp();

  if (!showInviteModal) return null;

  return (
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
  );
}
