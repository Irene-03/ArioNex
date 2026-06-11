import React from 'react';
import { useApp } from '../../context/AppContext';

export default function DashboardView() {
  const { documents, stats, chatMessages, setActiveScreen } = useApp();

  return (
    <div className="screen fade-in">
      <div className="stats-row">
        <div className="stat-card stat-accent">
          <div className="stat-label">اسناد ایندکس‌شده</div>
          <div className="stat-value">{stats.total_documents}</div>
          <div className="stat-change stat-up">تعداد کل اسناد پایگاه دانش</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">پرسش‌های امروز</div>
          <div className="stat-value">{stats.total_queries_today}</div>
          <div className="stat-change stat-up">در کل سیستم</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">میانگین زمان پاسخ RAG</div>
          <div className="stat-value">{stats.average_response_time}s</div>
          <div className="stat-change" style={{color: 'var(--text-muted)'}}>پایدار و ایمن</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">پوشش اطلاعات شخصی (PII)</div>
          <div className="stat-value">{stats.total_pii_masked} مورد</div>
          <div className="stat-change stat-up">ماسک شده در تمام فایل‌ها</div>
        </div>
      </div>

      <div className="two-col">
        <div>
          {/* وضعیت پایپ لاین زنده پردازش */}
          <div className="card">
            <div className="card-title">
              وضعیت زنده خط پردازش اسناد (Pipeline Progress)
              <div style={{display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-success)', fontWeight: 'normal'}}>
                <div className="pulse" style={{width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-success)'}}></div> زنده
              </div>
            </div>
            
            <div className="pipeline">
              <div className="pipe-step">
                <div className="pipe-node pipe-done">📥<div className="pipe-check">✓</div></div>
                <div className="pipe-label">دریافت منبع</div>
              </div>
              <div className="pipe-arrow">←</div>
              <div className="pipe-step">
                <div className="pipe-node pipe-done">🔒<div className="pipe-check">✓</div></div>
                <div className="pipe-label">ایرلاک حریم خصوصی</div>
              </div>
              <div className="pipe-arrow">←</div>
              <div className="pipe-step">
                <div className="pipe-node pipe-active">⚙️</div>
                <div className="pipe-label" style={{color: 'var(--copper-dark)', fontWeight: 'bold'}}>تقطیع و پردازش</div>
              </div>
              <div className="pipe-arrow">←</div>
              <div className="pipe-step">
                <div className="pipe-node pipe-idle">🗄</div>
                <div className="pipe-label">ذخیره برداری</div>
              </div>
              <div className="pipe-arrow">←</div>
              <div className="pipe-step">
                <div className="pipe-node pipe-idle">✅</div>
                <div className="pipe-label">آماده بهره‌برداری</div>
              </div>
            </div>

            {documents.some(d => d.status === 'uploading' || d.progress < 100) ? (
              documents
                .filter(d => d.status === 'uploading' || d.progress < 100)
                .slice(0, 1)
                .map(d => (
                  <div key={d.id} style={{background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-secondary)'}}>
                    <strong style={{color: 'var(--text-primary)'}}>در حال پردازش:</strong> {d.name} — (پیشرفت {d.progress}٪)
                    <div style={{marginTop: '10px', background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                      <div style={{width: `${d.progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--copper), var(--copper-light))', borderRadius: '4px'}}></div>
                    </div>
                  </div>
                ))
            ) : (
              <div style={{background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-secondary)', textAlign: 'center'}}>
                <span style={{fontStyle: 'italic', opacity: 0.8}}>خط پردازش اسناد در حال حاضر آماده به کار است. سندی در صف نیست.</span>
              </div>
            )}
          </div>

          {/* پرسش‌های اخیر */}
          <div className="card">
            <div className="card-title">آخرین پرسش‌های اعضای سازمان <span className="card-link" onClick={() => setActiveScreen('chat')}>مشاهده همه چت‌ها →</span></div>
            {chatMessages.filter(m => m.sender === 'user').length > 0 ? (
              chatMessages
                .filter(m => m.sender === 'user')
                .slice(-3)
                .reverse()
                .map(msg => (
                  <div key={msg.id} className="query-row">
                    <div className="query-dot q-green"></div>
                    <div className="q-text" style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '380px'}}>
                      {msg.text}
                    </div>
                    <span className="q-badge qb-done">پاسخ داده شد</span>
                  </div>
                ))
            ) : (
              <div style={{fontSize: '12.5px', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '16px 0'}}>
                هیچ پرسشی در این نشست مطرح نشده است.
              </div>
            )}
          </div>
        </div>

        {/* سایدبار سمت چپ اطلاعات پایگاه دانش */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
          <div className="card">
            <div className="card-title">توزیع منابع دانش سازمان</div>
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px'}}>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                  <span style={{color: 'var(--text-secondary)'}}>اسناد PDF</span>
                  <strong style={{color: 'var(--text-primary)'}}>{stats.pdf_count} سند</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: `${stats.total_documents > 0 ? (stats.pdf_count / stats.total_documents) * 100 : 0}%`, height: '100%', background: 'var(--navy)', borderRadius: '4px'}}></div>
                </div>
              </div>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                  <span style={{color: 'var(--text-secondary)'}}>صفحات مالی و CSV</span>
                  <strong style={{color: 'var(--text-primary)'}}>{stats.csv_excel_count} فایل</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: `${stats.total_documents > 0 ? (stats.csv_excel_count / stats.total_documents) * 100 : 0}%`, height: '100%', background: 'var(--copper)', borderRadius: '4px'}}></div>
                </div>
              </div>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                  <span style={{color: 'var(--text-secondary)'}}>اسناد متنی و غیره</span>
                  <strong style={{color: 'var(--text-primary)'}}>{stats.other_count} سند</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: `${stats.total_documents > 0 ? (stats.other_count / stats.total_documents) * 100 : 0}%`, height: '100%', background: 'var(--color-info)', borderRadius: '4px'}}></div>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">فعالیت‌های زنده حریم خصوصی</div>
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              {documents.length > 0 ? (
                documents.slice(0, 2).map((doc) => (
                  <div key={doc.id} style={{display: 'flex', gap: '12px', alignItems: 'flex-start', fontSize: '12.5px'}}>
                    <span style={{color: doc.status === 'ready' ? 'var(--color-success)' : 'var(--copper)', background: doc.status === 'ready' ? 'var(--color-success-bg)' : 'rgba(196, 137, 74, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold'}}>
                      {doc.status === 'ready' ? '✓' : '⏳'}
                    </span>
                    <div>
                      <div style={{color: 'var(--text-primary)', fontWeight: '600'}}>
                        {doc.status === 'ready' ? 'سند با موفقیت ایندکس شد' : 'در حال پردازش سند'}
                      </div>
                      <div style={{color: 'var(--text-secondary)', marginTop: '2px'}}>
                        محتوای سند "{doc.name}" پردازش گردید و اطلاعات حساس در صورت وجود ماسک شدند.
                      </div>
                      <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>{doc.date}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{fontSize: '12.5px', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '16px 0'}}>
                  هیچ سند یا فعالیتی هنوز ثبت نشده است.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
