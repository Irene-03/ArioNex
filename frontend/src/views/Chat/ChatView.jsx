import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';
import {
  Plus,
  ShieldCheck,
  ShieldAlert,
  FileText,
  Send,
  Trash2,
  Bot,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function ChatView() {
  const {
    chatMessages,
    inputText,
    setInputText,
    handleSendMessage,
    sessions,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    deleteSession,
    setChatMessages,
  } = useApp();

  const [copiedId, setCopiedId] = useState(null);

  const copyText = async (id, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1600);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  const setFeedback = (id, feedback) => {
    setChatMessages(prev => prev.map(m => {
      if (m.id === id) {
        return { ...m, feedback: feedback === m.feedback ? null : feedback };
      }
      return m;
    }));
  };

  return (
    <div className="screen fade-in" style={{ padding: 16 }}>
      <div className="chat-layout" style={{ height: '100%', minHeight: 0 }}>
        <div className="chat-sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
          <button className="ax-btn ax-btn--primary ax-btn--block" onClick={createNewSession}>
            <Plus size={16} /> مکالمه جدید
          </button>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', fontWeight: 700, marginTop: 14, padding: '0 4px' }}>
            مکالمات اخیر
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10, overflowY: 'auto', flex: 1 }}>
            {sessions.map(s => {
              const userMsgsCount = s.messages.filter(m => m.sender === 'user').length;
              return (
                <div
                  key={s.id}
                  className={`chat-history-item ${activeSessionId === s.id ? 'active-chat' : ''}`}
                  onClick={() => setActiveSessionId(s.id)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', cursor: 'pointer', position: 'relative' }}
                >
                  <div style={{ overflow: 'hidden', flex: 1, minWidth: 0, textAlign: 'right', direction: 'rtl' }}>
                    <div
                      className="chi-title"
                      style={{
                        fontSize: 13,
                        fontWeight: activeSessionId === s.id ? '700' : '400',
                        color: activeSessionId === s.id ? 'var(--heading)' : 'var(--text-primary)',
                      }}
                    >
                      {s.title}
                    </div>
                    <div className="chi-sub" style={{ fontSize: 11, marginTop: 2 }}>{userMsgsCount} پیام</div>
                  </div>
                  {sessions.length > 1 && (
                    <button className="icon-btn icon-btn--danger" onClick={(e) => deleteSession(s.id, e)} title="حذف مکالمه" aria-label="حذف مکالمه">
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="chat-main">
          <div className="chat-header">
            <div className="chat-header-icon">
              <Bot size={18} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14.5, color: 'var(--heading)' }}>دستیار هوش سازمانی آریونکس</div>
              <div style={{ fontSize: 11.5, color: 'var(--color-success)', fontWeight: 600 }}>● آنلاین · RAG فعال و امن</div>
            </div>
            <span className="q-badge qb-done" style={{ fontSize: 12 }}>مخزن متصل</span>
          </div>

          <div className="chat-messages">
            {chatMessages.map(msg => (
              <div key={msg.id} className={`msg ${msg.sender === 'user' ? 'msg-user' : 'msg-ai'}`}>
                <div className={`msg-avatar ${msg.sender === 'user' ? 'user-av' : 'ai-av'}`}>
                  {msg.sender === 'user' ? 'AK' : 'AN'}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {msg.sender === 'ai' && !msg.isWelcome && msg.text && (
                    <div className="safety-tag">
                      {msg.isRefusal ? <ShieldAlert size={12} /> : <ShieldCheck size={12} />}
                      {msg.isRefusal ? 'حفاظت عدم توهم فعال' : 'پاسخ معتبر RAG · تأیید شده توسط مخزن دانش'}
                    </div>
                  )}

                  {msg.text && (
                    <div className={`msg-bubble ${msg.sender === 'user' ? 'user-bubble' : 'ai-bubble'}`}>
                      {msg.sender === 'ai' ? (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                        </div>
                      ) : (
                        msg.text
                      )}
                    </div>
                  )}

                  {!msg.text && msg.isLoading && (
                    <div className="ai-bubble loading-bubble">
                      <div className="typing-indicator">
                        <span />
                        <span />
                        <span />
                      </div>
                      <span className="loading-text">دستیار در حال فکر...</span>
                    </div>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="source-tags">
                      {msg.sources.map((src, i) => (
                        <span key={i} className="source-tag">
                          <FileText size={12} /> {src.name} · {src.page}
                        </span>
                      ))}
                    </div>
                  )}

                  {msg.sender === 'ai' && !msg.isWelcome && msg.text && !msg.isLoading && (
                    <div className="msg-actions">
                      <button
                        className="msg-action"
                        title="کپی پاسخ"
                        aria-label="کپی پاسخ"
                        onClick={() => copyText(msg.id, msg.text)}
                        style={{ color: copiedId === msg.id ? 'var(--color-success)' : undefined }}
                      >
                        {copiedId === msg.id ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                      <button
                        className={`msg-action ${msg.feedback === 'up' ? 'msg-action--active' : ''}`}
                        title="پاسخ مفید بود"
                        aria-label="پاسخ مفید بود"
                        onClick={() => setFeedback(msg.id, 'up')}
                      >
                        <ThumbsUp size={14} />
                      </button>
                      <button
                        className={`msg-action ${msg.feedback === 'down' ? 'msg-action--active msg-action--danger' : ''}`}
                        title="پاسخ مفید نبود"
                        aria-label="پاسخ مفید نبود"
                        onClick={() => setFeedback(msg.id, 'down')}
                      >
                        <ThumbsDown size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

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
            <button className="send-btn" onClick={handleSendMessage} aria-label="ارسال پیام">
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
