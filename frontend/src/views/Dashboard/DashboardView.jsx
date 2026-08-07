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
  ArrowLeft,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import Badge from '../../components/ui/Badge';

function DonutChart({ segments, size = 110 }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const stroke = 16;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const gap = 3;

  const visibleSegments = segments.filter(s => s.value > 0);
  const arcs = visibleSegments.reduce((acc, seg, i) => {
    const prev = i === 0 ? 0 : acc[i - 1].offset + acc[i - 1].dash + gap;
    const dash = (seg.value / total) * (circumference - gap * visibleSegments.length);
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
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      ))}
      <text x="50%" y="48%" dominantBaseline="central" textAnchor="middle" fill="var(--heading)" fontSize="20" fontWeight="700" fontFamily="inherit">
        {total}
      </text>
      <text x="50%" y="62%" dominantBaseline="central" textAnchor="middle" fill="var(--text-muted)" fontSize="9" fontWeight="500" fontFamily="inherit">
        سند
      </text>
    </svg>
  );
}

export default function DashboardView() {
  const { documents, stats, chatMessages, setActiveScreen } = useApp();

  const queryHistory = chatMessages.filter(m => m.sender === 'user');

  const fileSegments = [
    { label: 'اسناد PDF', value: stats.pdf_count, color: 'var(--navy)' },
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
      accent: true,
    },
    {
      label: 'پرسش‌های امروز',
      value: stats.total_queries_today,
      change: 'در کل سیستم',
      icon: MessageSquareText,
    },
    {
      label: 'میانگین زمان پاسخ',
      value: `${stats.average_response_time}s`,
      change: 'پایدار و ایمن',
      icon: Timer,
    },
    {
      label: 'اطلاعات حساس ماسک‌شده',
      value: `${stats.total_pii_masked}`,
      change: 'مورد در تمام فایل‌ها',
      icon: ShieldCheck,
    },
    {
      label: 'توکن‌های ورودی',
      value: stats.input_tokens_used ? stats.input_tokens_used.toLocaleString() : '0',
      icon: Cpu,
    },
    {
      label: 'توکن‌های خروجی',
      value: stats.output_tokens_used ? stats.output_tokens_used.toLocaleString() : '0',
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
    { state: s2, icon: Lock, label: 'حریم خصوصی' },
    { state: s3, icon: Settings, label: 'پردازش' },
    { state: s4, icon: Database, label: 'ذخیره برداری' },
    { state: s5, icon: CheckCircle2, label: 'آماده بهره‌برداری' },
  ];

  return (
    <div className="screen fade-in">
      <div className="ax-page-header">
        <div>
          <div className="ax-page-header__title">
            <LayoutDashboard size={18} style={{ color: 'var(--copper)' }} />
            نمای کلی سامانه
          </div>
          <div className="ax-page-header__desc">نمای کلی وضعیت سامانه و دانش سازمانی</div>
        </div>
      </div>

      <div className="stats-row">
        {statCards.map(card => {
          const Icon = card.icon;
          return (
            <div className={`stat-card ${card.accent ? 'stat-accent' : ''}`} key={card.label}>
              <div className="stat-label">
                <Icon />
                {card.label}
              </div>
              <div className="stat-value">{card.value}</div>
              {card.change && (
                <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
                  {card.change}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="two-col">
        <div>
          <div className="card">
            <div className="card-title">
              وضعیت زنده خط پردازش اسناد
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--color-success)', fontWeight: 500 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: 'var(--color-success)' }} />
                زنده
              </div>
            </div>

            <div className="pipeline">
              {pipelineSteps.map((step, i) => (
                <React.Fragment key={step.label}>
                  <div className="pipe-step">
                    <div className={`pipe-node ${step.state}`}>
                      <step.icon size={18} />
                      {step.state === 'pipe-done' && (
                        <div className="pipe-check">
                          <CheckCircle2 size={10} />
                        </div>
                      )}
                    </div>
                    <div className="pipe-label" style={step.state === 'pipe-active' ? { color: 'var(--copper-dark)', fontWeight: 600 } : {}}>
                      {step.label}
                    </div>
                  </div>
                  {i < pipelineSteps.length - 1 && (
                    <div className="pipe-arrow">
                      <ArrowLeft size={16} />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>

            {activeDoc ? (
              <div style={{ background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>در حال پردازش:</strong> {activeDoc.name} — (پیشرفت {activeDoc.progress}٪)
                <div style={{ marginTop: 8, background: 'var(--gray-100)', borderRadius: 999, height: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${activeDoc.progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--copper), var(--copper-light))', borderRadius: 999 }} />
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
                خط پردازش اسناد آماده به کار است. سندی در صف نیست.
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">
              آخرین پرسش‌های اعضای سازمان
              <span className="card-link" onClick={() => setActiveScreen('chat')}>
                مشاهده همه <ArrowLeft size={12} style={{ display: 'inline' }} />
              </span>
            </div>
            {queryHistory.length > 0 ? (
              queryHistory
                .slice(-3)
                .reverse()
                .map(msg => (
                  <div key={msg.id} className="query-row">
                    <div className="query-dot q-green" />
                    <div className="q-text" style={{ maxWidth: 340 }}>{msg.text}</div>
                    <Badge variant="success" style={{ fontSize: 10, padding: '2px 8px' }}>پاسخ داده شد</Badge>
                  </div>
                ))
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '14px 0' }}>
                هیچ پرسشی در این نشست مطرح نشده است.
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">روند فعالیت پرسش و پاسخ</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '14px 0' }}>
              نمودار روند پس از ثبت آمار فعالیت در لاگ حسابرسی سامانه نمایش داده می‌شود.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-title">توزیع منابع دانش سازمان</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <DonutChart segments={fileSegments} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12 }}>
                {fileSegments.map(seg => (
                  <div key={seg.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: seg.color, flexShrink: 0 }} />
                    <span style={{ color: 'var(--text-secondary)' }}>{seg.label}</span>
                    <strong style={{ color: 'var(--text-primary)', marginRight: 'auto', fontVariantNumeric: 'tabular-nums' }}>
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {documents.slice(0, 3).map(doc => (
                  <div key={doc.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 12, padding: '8px 10px', borderRadius: 'var(--radius)', background: 'var(--gray-50)' }}>
                    <Badge variant={doc.status === 'ready' ? 'success' : 'copper'} style={{ fontSize: 10, padding: '2px 8px', flexShrink: 0 }}>
                      {doc.status === 'ready' ? 'تکمیل' : 'در حال پردازش'}
                    </Badge>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 12 }}>
                        {doc.name}
                      </div>
                      <div style={{ color: 'var(--text-muted)', marginTop: 2, fontSize: 11 }}>
                        {doc.date}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '14px 0' }}>
                هیچ سند یا فعالیتی هنوز ثبت نشده است.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
