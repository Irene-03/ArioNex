import { UploadCloud, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PII_KEY_LABELS } from '../../constants/models';

export default function UploadView() {
  const { piiPreview, piiAuditCounts, piiChecked, handleFileUpload, documents } = useApp();

  const processingDocs = documents.filter(d => d.status === 'uploading' || (d.progress !== undefined && d.progress < 100));

  return (
    <div className="screen fade-in">
      <div className="ax-page-header">
        <div>
          <div className="ax-page-header__title">
            <UploadCloud size={18} style={{ color: 'var(--copper)' }} />
            آپلود اسناد سازمانی
          </div>
          <div className="ax-page-header__desc">فیلتر حریم خصوصی و درون‌ریزی امن</div>
        </div>
      </div>

      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileUpload}
        onClick={handleFileUpload}
        style={{ cursor: 'pointer' }}
      >
        <div className="upload-icon">
          <UploadCloud />
        </div>
        <div className="upload-title">اسناد سازمان را به اینجا بکشید یا برای انتخاب کلیک کنید</div>
        <div className="upload-sub">
          کدهای ملی، شماره‌های تلفن، حساب‌های مالی و ایمیل‌ها به صورت خودکار شناسایی و ماسک می‌شوند.
        </div>

        <div className="file-type-pills">
          <span className="file-pill">PDF</span>
          <span className="file-pill">Word (DOCX)</span>
          <span className="file-pill">Excel / CSV</span>
          <span className="file-pill">JSON / SQL</span>
          <span className="file-pill">Plain Text</span>
        </div>

        <button
          className="ax-btn ax-btn--primary"
          style={{ marginTop: 20 }}
          onClick={(e) => {
            e.stopPropagation();
            handleFileUpload(e);
          }}
        >
          <UploadCloud size={16} /> انتخاب اسناد از سیستم
        </button>
      </div>

      <div className="grid-2-col">
        <div className="ax-card">
          <div className="ax-card__title">
            <FileText size={16} style={{ color: 'var(--copper)' }} />
            صف نوبت‌دهی پردازش اسناد
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
            {processingDocs.length > 0 ? (
              processingDocs.map(doc => (
                <div key={doc.id} style={{ border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8, fontWeight: 'bold' }}>
                    <span>{doc.name}</span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {doc.size} · {doc.progress < 100 ? 'در حال پردازش...' : 'تکمیل شد'}
                    </span>
                  </div>
                  <div className="prog-bar-wrap" style={{ width: '100%' }}>
                    <div className="prog-bar" style={{ width: `${doc.progress || 0}%` }} />
                  </div>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: 13, fontStyle: 'italic' }}>
                هیچ فایلی در صف پردازش نیست.
              </div>
            )}
          </div>
        </div>

        <div className="ax-card">
          <div className="ax-card__title" style={{ justifyContent: 'space-between', width: '100%' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShieldCheck size={16} style={{ color: 'var(--color-success)' }} />
              پیش‌نمایش قفل حریم خصوصی (PII)
            </span>
            <span className="q-badge qb-done">قفل حریم شخصی فعال</span>
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: '12px 0' }}>
            پیش‌نمایش زنده و هوشمند اقلام ماسک‌شده:
          </div>

          <div className="pii-demo" style={{ whiteSpace: 'pre-wrap' }}>
            {piiPreview ? (
              piiPreview
            ) : (
              <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic', opacity: 0.8 }}>
                هیچ سندی هنوز بارگذاری نشده است. پیش‌نمایش پوشش اطلاعات حساس پس از بارگذاری سند نمایش داده می‌شود.
              </span>
            )}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 10 }}>
            {Object.keys(piiAuditCounts || {}).length > 0 ? (
              <span>
                اقلام حساس فیلتر شده در آخرین فایل:{' '}
                {Object.entries(piiAuditCounts || {})
                  .filter(([, v]) => v > 0)
                  .map(([k, v]) => `${PII_KEY_LABELS[k] || k}: ${v} مورد`)
                  .join(' | ')}
              </span>
            ) : piiChecked ? (
              <span style={{ color: 'var(--color-success)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                <CheckCircle2 size={14} />
                هیچ اطلاعات حساسی در آخرین سند یافت نشد.
              </span>
            ) : piiPreview ? (
              <span>{piiPreview}</span>
            ) : (
              'پیش‌نمایش زنده اقلام'
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
