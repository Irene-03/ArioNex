import React from 'react';
import {
  LayoutDashboard,
  FileText,
  MessageSquareText,
  Timer,
  ShieldCheck,
  Cpu,
  Download,
  Lock,
  Settings,
  Database,
  CheckCircle2,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

function DonutChart({ segments, size = 120 }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  const visibleSegments = segments.filter(s => s.value > 0);
  const arcs = visibleSegments.reduce((acc, seg, i) => {
    const prev = i === 0 ? 0 : acc[i - 1].offset + acc[i - 1].dash;
    const dash = (seg.value / total) * circumference;
    acc.push({ seg, dash, offset: prev });
    return acc;
  }, []);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--gray-100)" strokeWidth={stroke} />
      {arcs.map(({ seg, dash, offset }, i) => (
        <circle
          key={i}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={seg.color}
          strokeWidth={stroke}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={-offset}
          strokeLinecap="butt"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      ))}
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fill="var(--heading)" fontSize="18" fontWeight="800" fontFamily="inherit">
        {total}
      </text>
    </svg>
  );
}

export default function DashboardView() {
  const { documents, stats, chatMessages, setActiveScreen } = useApp();

  const queryHistory = chatMessages.filter(m => m.sender === 'user');

  const fileSegments = [
    { label: 'اسناد PDF', value: stats.pdf_count, color: 'var(--brand)' },
    { label: 'صفحات مالی و CSV', value: stats.csv_excel_count, color: 'var(--copper)' },
    { label: 'متنی و سایر', value: stats.other_count, color: 'var(--color-info)' },
  ];

  const total = stats.total_documents || 1;

  const statCards = [
    {
      label: 'اسناد ایندکس‌شده',
      value: stats.total_documents,
      change: 'کل اسناد پایگاه دانش',
      icon: FileText,
      up: true,
    },
    {
      label: 'پرسش‌های امروز',
      value: stats.total_queries_today,
      change: 'در کل سیستم',
      icon: MessageSquareText,
      up: true,
    },
    {
      label: 'میانگین زمان پاسخ RAG',
      value: `${stats.average_response_time}s`,
      change: 'پایدار و ایمن',
      icon: Timer,
    },
    {
      label: 'پوشش اطلاعات شخصی (PII)',
      value: `${stats.total_pii_masked} مورد`,
      change: 'ماسک‌شده در تمام فایل‌ها',
      icon: ShieldCheck,
      up: true,
    },
    {
      label: 'توکن‌های ورودی',
      value: stats.input_tokens_used ? stats.input_tokens_used.toLocaleString() : 0,
      icon: Cpu,
    },
    {
      label: 'توکن‌های خروجی',
      value: stats.output_tokens_used ? stats.output_tokens_used.toLocaleString() : 0,
      icon: Cpu,
    },
  ];

  const activeDoc = documents.find(d => d.status === 'uploading' || (d.progress !== undefined && d.progress < 100));
  const prog = activeDoc ? (activeDoc.progress || 0) : (documents.length > 0 ? 100 : -1);
  const s1 = prog >= 0 ? (prog >= 30 ? 'pipe-done' : 'pipe-active') : 'pipe-idle';
  const s2 = prog >= 30 ? (prog >= 60 ? 'pipe-done' : 'pipe-active') : 'pipe-idle';
  const s3 = prog >= 60 ? (prog >= 85 ? 'pipe-done' : 'pipe-active') : 'pipe-idle';
  const s4 = prog >= 85 ? (prog >= 100 ? 'pipe-done' : 'pipe-active') : 'pipe-idle';
  const s5 = prog >= 100 ? 'pipe-done' : 'pipe-idle';

  const pipelineSteps = [
    { state: s1, icon: Download, label: 'دریافت منبع' },
    { state: s2, icon: Lock, label: 'ایرلاک حریم خصوصی' },
    { state: s3, icon: Settings, label: 'تقطیع و پردازش' },
    { state: s4, icon: Database, label: 'ذخیره برداری' },
    { state: s5, icon: CheckCircle2, label: 'آماده بهره‌برداری' },
  ];

  return (
    <div className="screen fade-in">
      <div className="ax-page-header">
        <div>
          <div className="ax-page-header__title">
            <LayoutDashboard size={20} style={{ color: 'var(--copper)' }} />
            نمای کلی سامانه
          </div>
        </div>
      </div>

      <div className="stats-row">
        {statCards.map(card => {
          const Icon = card.icon;
          return (
            <div className={`stat-card ${card.label.startsWith('اسناد') ? 'stat-accent' : ''}`} key={card.label}>
              <div className="stat-label">
                <Icon />
                {card.label}
              </div>
              <div className="stat-value">{card.value}</div>
              <div className={`stat-change ${card.up ? 'stat-up' : ''}`} style={!card.up ? { color: 'var(--text-muted)' } : undefined}>
                {card.change}
              </div>
            </div>
          );
        })}
      </div>

      <div className="two-col">
        <div>
          <div className="card">
            <div className="card-title">
              وضعیت زنده خط پردازش اسناد
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-success)', fontWeight: 'normal' }}>
                <div className="pulse" style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--color-success)' }} />
                زنده
              </div>
            </div>

            <div className="pipeline">
              {pipelineSteps.map((step, i) => (
                <React.Fragment key={step.label}>
                  <div className="pipe-step">
                    <div className={`pipe-node ${step.state}`}>
                      <step.icon size={22} />
                      {step.state === 'pipe-done' && <div className="pipe-check">✓</div>}
                    </div>
                    <div className="pipe-label" style={step.state === 'pipe-active' ? { color: 'var(--copper-dark)', fontWeight: 'bold' } : {}}>
                      {step.label}
                    </div>
                  </div>
                  {i < pipelineSteps.length - 1 && <div className="pipe-arrow">←</div>}
                </React.Fragment>
              ))}
            </div>

            {activeDoc ? (
              <div style={{ background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>در حال پردازش:</strong> {activeDoc.name} — (پیشرفت {activeDoc.progress}٪)
                <div style={{ marginTop: 10, background: 'var(--gray-100)', borderRadius: 999, height: 6, overflow: 'hidden' }}>
                  <div style={{ width: `${activeDoc.progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--copper), var(--copper-light))', borderRadius: 999 }} />
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '12px 16px', fontSize: '12.5px', color: 'var(--text-muted)', textAlign: 'center' }}>
                خط پردازش اسناد آماده به کار است. سندی در صف نیست.
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">
              آخرین پرسش‌های اعضای سازمان
              <span className="card-link" onClick={() => setActiveScreen('chat')}>
                مشاهده همه چت‌ها ←
              </span>
            </div>
            {queryHistory.length > 0 ? (
              queryHistory
                .slice(-3)
                .reverse()
                .map(msg => (
                  <div key={msg.id} className="query-row">
                    <div className="query-dot q-green" />
                    <div className="q-text" style={{ maxWidth: 380 }}>{msg.text}</div>
                    <span className="q-badge qb-done">پاسخ داده شد</span>
                  </div>
                ))
            ) : (
              <div style={{ fontSize: 12.5, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '16px 0' }}>
                هیچ پرسشی در این نشست مطرح نشده است.
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">روند فعالیت پرسش و پاسخ</div>
            <div style={{ fontSize: 12.5, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '16px 0' }}>
              نمودار روند پس از ثبت آمار فعالیت در لاگ حسابرسی سامانه نمایش داده می‌شود.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-title">توزیع منابع دانش سازمان</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <DonutChart segments={fileSegments} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12.5 }}>
                {fileSegments.map(seg => (
                  <div key={seg.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: seg.color, flexShrink: 0 }} />
                    <span style={{ color: 'var(--text-secondary)' }}>{seg.label}</span>
                    <strong style={{ color: 'var(--text-primary)', marginRight: 'auto' }}>
                      {Math.round((seg.value / total) * 100)}٪
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">فعالیت‌های زنده حریم خصوصی</div>
            {documents.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {documents.slice(0, 3).map(doc => (
                  <div key={doc.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', fontSize: 12.5 }}>
                    <span
                      style={{
                        color: doc.status === 'ready' ? 'var(--color-success)' : 'var(--copper)',
                        background: doc.status === 'ready' ? 'var(--color-success-bg)' : 'var(--copper-pale)',
                        padding: '2px 6px',
                        borderRadius: 4,
                        fontWeight: 'bold',
                      }}
                    >
                      {doc.status === 'ready' ? '✓' : '⏳'}
                    </span>
                    <div>
                      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                        {doc.status === 'ready' ? 'سند با موفقیت ایندکس شد' : 'در حال پردازش سند'}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                        محتوای سند «{doc.name}» پردازش گردید و اطلاعات حساس ماسک شدند.
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{doc.date}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12.5, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '16px 0' }}>
                هیچ سند یا فعالیتی هنوز ثبت نشده است.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
