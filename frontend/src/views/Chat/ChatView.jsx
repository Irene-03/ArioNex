import React from 'react';
import { useApp } from '../../context/AppContext';

export default function ChatView() {
  const {
    chatMessages,
    setChatMessages,
    inputText,
    setInputText,
    isAiLoading,
    handleSendMessage
  } = useApp();

  return (
    <div className="screen fade-in" style={{padding: '16px'}}>
      <div className="chat-layout" style={{height: '100%', minHeight: 0}}>
        
        {/* لیست تاریخچه جلسات چت */}
        <div className="chat-sidebar">
          <button className="topbar-btn btn-primary" style={{width: '100%', justifyContent: 'center', gap: '8px'}} onClick={() => {
            setChatMessages([{
              id: Date.now(),
              sender: 'ai',
              text: 'مکالمه جدید شروع شد. چطور می‌توانم کمک کنم؟',
              isSafe: true,
              isWelcome: true,
              sources: []
            }]);
          }}>
            + مکالمه جدید
          </button>
          <div style={{fontSize: '11.5px', color: 'var(--text-muted)', fontWeight: '700', marginTop: '10px', padding: '0 4px'}}>مکالمات اخیر</div>
          
          <div className="chat-history-item active-chat">
            <div className="chi-title">تحلیل سود خالص Q2</div>
            <div className="chi-sub">۴ پیام · ۸ دقیقه پیش</div>
          </div>
          <div className="chat-history-item">
            <div className="chi-title">سیاست مرخصی کارمندان</div>
            <div className="chi-sub">۲ پیام · ۲ ساعت پیش</div>
          </div>
          <div className="chat-history-item">
            <div className="chi-title">بندهای فسخ قرارداد Q3</div>
            <div className="chi-sub">۷ پیام · دیروز</div>
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
                
                <div>
                  {msg.sender === 'ai' && !msg.isWelcome && (
                    <div className="safety-tag">
                      <span>🔒</span> {msg.isRefusal ? 'حفاظت عدم توهم فعال' : 'پاسخ معتبر RAG · تأیید شده توسط مخزن دانش'}
                    </div>
                  )}
                  
                  <div className={`msg-bubble ${msg.sender === 'user' ? 'user-bubble' : 'ai-bubble'}`} style={{whiteSpace: 'pre-line'}}>
                    {msg.text}
                  </div>

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
            
            {isAiLoading && (
              <div className="msg msg-ai">
                <div className="msg-avatar ai-av">AN</div>
                <div>
                  <div className="ai-bubble pulse" style={{padding: '12px 24px'}}>
                    در حال بررسی و بازیابی پاسخ امن از پایگاه اسناد آریونکس...
                  </div>
                </div>
              </div>
            )}
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
