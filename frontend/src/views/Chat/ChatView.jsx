import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useApp } from '../../context/AppContext';

export default function ChatView() {
  const {
    chatMessages,
    inputText,
    setInputText,
    isAiLoading,
    handleSendMessage,
    sessions,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    deleteSession
  } = useApp();

  return (
    <div className="screen fade-in" style={{padding: '16px'}}>
      <div className="chat-layout" style={{height: '100%', minHeight: 0}}>
        
        {/* لیست تاریخچه جلسات چت */}
        <div className="chat-sidebar" style={{display: 'flex', flexDirection: 'column'}}>
          <button className="topbar-btn btn-primary" style={{width: '100%', justifyContent: 'center', gap: '8px'}} onClick={createNewSession}>
            + مکالمه جدید
          </button>
          <div style={{fontSize: '11.5px', color: 'var(--text-muted)', fontWeight: '700', marginTop: '14px', padding: '0 4px'}}>مکالمات اخیر</div>
          
          <div style={{display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px', overflowY: 'auto', flex: 1}}>
            {sessions.map(s => {
              const userMsgsCount = s.messages.filter(m => m.sender === 'user').length;
              return (
                <div 
                  key={s.id} 
                  className={`chat-history-item ${activeSessionId === s.id ? 'active-chat' : ''}`}
                  onClick={() => setActiveSessionId(s.id)}
                  style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', borderRadius: 'var(--radius)', cursor: 'pointer', position: 'relative'}}
                >
                  <div style={{overflow: 'hidden', flex: 1, minWidth: 0, textAlign: 'right', direction: 'rtl'}}>
                    <div className="chi-title" style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px', fontWeight: activeSessionId === s.id ? '700' : '400', color: activeSessionId === s.id ? 'var(--navy)' : 'var(--text-primary)'}}>
                      {s.title}
                    </div>
                    <div className="chi-sub" style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>{userMsgsCount} پیام</div>
                  </div>
                  {sessions.length > 1 && (
                    <button 
                      onClick={(e) => deleteSession(s.id, e)} 
                      style={{background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '16px', cursor: 'pointer', padding: '2px 6px', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'color 0.2s'}}
                      title="حذف مکالمه"
                      onMouseEnter={(e) => e.target.style.color = 'var(--color-danger)'}
                      onMouseLeave={(e) => e.target.style.color = 'var(--text-muted)'}
                    >
                      ×
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* پنجره چت اصلی */}
        <div className="chat-main">
          <div className="chat-header">
            <div className="chat-header-icon">🤖</div>
            <div style={{flex: 1}}>
              <div style={{fontWeight: '700', fontSize: '14.5px', color: 'var(--navy)'}}>دستیار هوش سازمانی آریونکس</div>
              <div style={{fontSize: '11.5px', color: 'var(--color-success)', fontWeight: '600'}}>● آنلاین · RAG فعال و امن</div>
            </div>
            <div style={{display: 'flex', gap: '8px'}}>
              <span className="q-badge qb-done" style={{fontSize: '12px'}}>مخزن متصل</span>
            </div>
          </div>

          {/* نمایش لیست پیام‌ها */}
          <div className="chat-messages">
            {chatMessages.map(msg => (
              <div key={msg.id} className={`msg ${msg.sender === 'user' ? 'msg-user' : 'msg-ai'}`}>
                <div className={`msg-avatar ${msg.sender === 'user' ? 'user-av' : 'ai-av'}`}>
                  {msg.sender === 'user' ? 'AK' : 'AN'}
                </div>
                
                <div style={{flex: 1, minWidth: 0}}>
                  {msg.sender === 'ai' && !msg.isWelcome && msg.text && (
                    <div className="safety-tag">
                      <span>🔒</span> {msg.isRefusal ? 'حفاظت عدم توهم فعال' : 'پاسخ معتبر RAG · تأیید شده توسط مخزن دانش'}
                    </div>
                  )}
                  
                  {/* فقط اگر متن وجود دارد نمایش بده */}
                  {msg.text && (
                    <div className={`msg-bubble ${msg.sender === 'user' ? 'user-bubble' : 'ai-bubble'}`}>
                      {msg.sender === 'ai' ? (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.text}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        msg.text
                      )}
                    </div>
                  )}

                  {/* اگر متن خالی است و در حال بارگذاری است، نشانگر تایپ نمایش داده شود */}
                  {!msg.text && msg.isLoading && (
                    <div className="ai-bubble loading-bubble">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                      <span className="loading-text">دستیار در حال فکر...</span>
                    </div>
                  )}

                  {/* نمایش استناد به منابع در چت */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="source-tags">
                      {msg.sources.map((src, i) => (
                        <span key={i} className="source-tag">
                          📄 {src.name} · {src.page}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* فیلد ارسال پیام چت */}
          <div className="chat-input-area">
            <textarea 
              className="chat-input-box" 
              placeholder="هر چیزی درباره اسناد خود بپرسید..." 
              rows="1"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
            />
            <button className="send-btn" onClick={handleSendMessage}>
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
