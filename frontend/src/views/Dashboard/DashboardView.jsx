import React from 'react';
import { useApp } from '../../context/AppContext';

export default function DashboardView() {
  const { documents, setActiveScreen } = useApp();

  return (
    <div className="screen fade-in">
      <div className="stats-row">
        <div className="stat-card stat-accent">
          <div className="stat-label">اسناد ایندکس‌شده</div>
          <div className="stat-value">{documents.length + 1204}</div>
          <div className="stat-change stat-up">↑ ۱۴ اسناد جدید این هفته</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">پرسش‌های امروز</div>
          <div className="stat-value">384</div>
          <div className="stat-change stat-up">↑ ۱۲٪ نسبت به دیروز</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">میاگین زمان پاسخ RAG</div>
          <div className="stat-value">1.4s</div>
          <div className="stat-change" style={{color: 'var(--text-muted)'}}>پایدار و ایمن</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">پوشش اطلاعات شخصی (PII)</div>
          <div className="stat-value">91 مورد</div>
          <div className="stat-change stat-up">↑ ۸ ماسک موفق امروز</div>
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

            <div style={{background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-secondary)'}}>
              <strong style={{color: 'var(--text-primary)'}}>در حال پردازش:</strong> Q3_Financial_Report.pdf — قطعه ۴۷ از ۱۲۰ (۳۹٪ پیشرفت)
              <div style={{marginTop: '10px', background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                <div style={{width: '39%', height: '100%', background: 'linear-gradient(90deg, var(--copper), var(--copper-light))', borderRadius: '4px'}}></div>
              </div>
            </div>
          </div>

          {/* پرسش‌های اخیر */}
          <div className="card">
            <div className="card-title">آخرین پرسش‌های اعضای سازمان <span className="card-link" onClick={() => setActiveScreen('chat')}>مشاهده همه چت‌ها →</span></div>
            <div className="query-row">
              <div className="query-dot q-green"></div>
              <div className="q-text">حاشیه سود ناخالص خط محصول B در Q2 چقدر بود؟</div>
              <span className="q-badge qb-done">پاسخ داده شد</span>
            </div>
            <div className="query-row">
              <div className="query-dot q-green"></div>
              <div className="q-text">خلاصه اسناد HR مربوط به مرخصی‌های زایمان جدید</div>
              <span className="q-badge qb-done">پاسخ داده شد</span>
            </div>
            <div className="query-row">
              <div className="query-dot q-amber"></div>
              <div className="q-text">استخراج بندهای حقوقی از contract_draft_v3.pdf</div>
              <span className="q-badge qb-proc">در پردازش RAG</span>
            </div>
            <div className="query-row">
              <div className="query-dot q-green"></div>
              <div className="q-text">مسئول انطباق بر اساس چارت سازمانی مصوب کیست؟</div>
              <span className="q-badge qb-done">پاسخ داده شد</span>
            </div>
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
                  <strong style={{color: 'var(--text-primary)'}}>1,204 سند</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: '72%', height: '100%', background: 'var(--navy)', borderRadius: '4px'}}></div>
                </div>
              </div>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                  <span style={{color: 'var(--text-secondary)'}}>صفحات مالی و CSV</span>
                  <strong style={{color: 'var(--text-primary)'}}>387 فایل</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: '42%', height: '100%', background: 'var(--copper)', borderRadius: '4px'}}></div>
                </div>
              </div>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px'}}>
                  <span style={{color: 'var(--text-secondary)'}}>لاگ‌های پشتیبانی سازمان</span>
                  <strong style={{color: 'var(--text-primary)'}}>918 لاگ</strong>
                </div>
                <div style={{background: 'var(--gray-100)', borderRadius: '4px', height: '6px', overflow: 'hidden'}}>
                  <div style={{width: '58%', height: '100%', background: 'var(--color-info)', borderRadius: '4px'}}></div>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">فعالیت‌های زنده حریم خصوصی</div>
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start', fontSize: '12.5px'}}>
                <span style={{color: 'var(--color-success)', background: 'var(--color-success-bg)', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold'}}>✓</span>
                <div>
                  <div style={{color: 'var(--text-primary)', fontWeight: '600'}}>قفل حریم خصوصی فعال</div>
                  <div style={{color: 'var(--text-secondary)', marginTop: '2px'}}>۳ کدملی از فایل legal_doc_091.pdf پوشش داده شد.</div>
                  <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>۲ دقیقه پیش</div>
                </div>
              </div>
              <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start', fontSize: '12.5px'}}>
                <span style={{color: 'var(--color-info)', background: 'var(--color-info-bg)', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold'}}>↑</span>
                <div>
                  <div style={{color: 'var(--text-primary)', fontWeight: '600'}}>آپلود سند جدید</div>
                  <div style={{color: 'var(--text-secondary)', marginTop: '2px'}}>سعید م. ۴ قرارداد جدید تأمین‌کنندگان را آپلود نمود.</div>
                  <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px'}}>۱۴ دقیقه پیش</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
