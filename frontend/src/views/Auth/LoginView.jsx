import React from 'react';
import { useApp } from '../../context/AppContext';

export default function LoginView() {
  const {
    loginUsername,
    setLoginUsername,
    loginPassword,
    setLoginPassword,
    loginError,
    isLoginLoading,
    handleLogin,
    
    isSignupMode,
    setIsSignupMode,
    signupUsername,
    setSignupUsername,
    signupPassword,
    setSignupPassword,
    signupError,
    isSignupLoading,
    signupSuccess,
    handleSignup,
    setSignupError
  } = useApp();

  return (
    <div className="login-overlay">
      <div className="login-card">
        <div className="login-logo">
          <svg className="logo-mark" viewBox="0 0 32 32" fill="none" width="40" height="40">
            <polygon points="16,2 28,26 4,26" fill="none" stroke="#c4894a" strokeWidth="2.5"/>
            <polygon points="16,9 22,26 10,26" fill="none" stroke="#c4894a" strokeWidth="1.5" opacity="0.5"/>
          </svg>
          <span className="logo-text" style={{fontSize: '26px', color: 'white'}}>آریو<span>نکس</span></span>
        </div>
        
        <h2 className="login-title">{isSignupMode ? 'ثبت‌نام در سامانه تجاری آریونکس' : 'ورود به سامانه تجاری آریونکس'}</h2>
        <p className="login-subtitle">سامانه هوشمند مدیریت دانش، ممیزی حریم خصوصی (PII) و تحلیل قوانین انطباق سازمان</p>
        
        {isSignupMode ? (
          <>
            {signupError && <div className="login-error">{signupError}</div>}
            {signupSuccess && <div className="login-success">ثبت‌نام با موفقیت انجام شد!</div>}
            
            <form onSubmit={handleSignup}>
              <div className="login-form-group">
                <label className="login-label">نام کاربری</label>
                <input 
                  type="text" 
                  className="login-input" 
                  value={signupUsername} 
                  onChange={e => setSignupUsername(e.target.value)}
                  placeholder="username"
                  required
                />
              </div>
              
              <div className="login-form-group">
                <label className="login-label">رمز عبور</label>
                <input 
                  type="password" 
                  className="login-input" 
                  value={signupPassword} 
                  onChange={e => setSignupPassword(e.target.value)}
                  placeholder="••••••"
                  required
                />
              </div>
              
              <button type="submit" className="login-btn" disabled={isSignupLoading}>
                {isSignupLoading ? '⏳ در حال ثبت‌نام...' : 'ثبت‌نام کاربر جدید'}
              </button>
            </form>
            
            <div className="login-toggle-mode" style={{marginTop: '15px', fontSize: '13px'}}>
              قبلاً ثبت‌نام کرده‌اید؟ {' '}
              <span 
                style={{color: '#c4894a', cursor: 'pointer', textDecoration: 'underline'}} 
                onClick={() => {
                  setIsSignupMode(false);
                  setSignupError('');
                }}
              >
                ورود به سیستم
              </span>
            </div>
          </>
        ) : (
          <>
            {loginError && <div className="login-error">{loginError}</div>}
            
            <form onSubmit={handleLogin}>
              <div className="login-form-group">
                <label className="login-label">نام کاربری</label>
                <input 
                  type="text" 
                  className="login-input" 
                  value={loginUsername} 
                  onChange={e => setLoginUsername(e.target.value)}
                  placeholder="username"
                  required
                />
              </div>
              
              <div className="login-form-group">
                <label className="login-label">رمز عبور</label>
                <input 
                  type="password" 
                  className="login-input" 
                  value={loginPassword} 
                  onChange={e => setLoginPassword(e.target.value)}
                  placeholder="••••••"
                  required
                />
              </div>
              
              <button type="submit" className="login-btn" disabled={isLoginLoading}>
                {isLoginLoading ? '⏳ در حال ورود...' : 'ورود به سیستم'}
              </button>
            </form>
            
            <div className="login-toggle-mode" style={{marginTop: '15px', fontSize: '13px'}}>
              کاربر جدید هستید؟ {' '}
              <span 
                style={{color: '#c4894a', cursor: 'pointer', textDecoration: 'underline'}} 
                onClick={() => {
                  setIsSignupMode(true);
                  setLoginError('');
                }}
              >
                ایجاد حساب کاربری (تحلیل‌گر)
              </span>
            </div>
          </>
        )}
        
        <div style={{fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '24px'}}>
          ArioNex Commercial AI Platform · Version 1.0.0
        </div>
      </div>
    </div>
  );
}
