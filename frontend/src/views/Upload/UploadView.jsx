import React from 'react';
import { useApp } from '../../context/AppContext';
import { PII_KEY_LABELS } from '../../constants/models';

export default function UploadView() {
  const {
    piiPreview,
    piiAuditCounts,
    piiChecked,
    handleFileUpload
  } = useApp();

  return (
    <div className="screen fade-in">
      <div className="upload-zone" onDragOver={(e) => e.preventDefault()} onDrop={handleFileUpload}>
        <div className="upload-icon">📂</div>
        <div className="upload-title">اسناد سازمان را به اینجا بکشید یا برای انتخاب کلیک کنید</div>
        <div className="upload-sub">
          اسناد پیش از تحلیل و ذخیره‌سازی، به صورت خودکار از سیستم امنیتی «قفل حریم خصوصی آریونکس» عبور کرده و تمامی کدهای ملی، شماره‌های تلفن، شماره حساب‌های مالی و نام‌های خاص بدون خروج از زیرساخت ماسک می‌شوند.
        </div>
        
        <div className="file-type-pills">
          <span className="file-pill">PDF Document</span>
          <span className="file-pill">Microsoft Word (DOCX)</span>
          <span className="file-pill">Excel / CSV Spreadsheet</span>
          <span className="file-pill">JSON / SQL Dumps</span>
          <span className="file-pill">Plain Text (TXT)</span>
        </div>

        <button className="topbar-btn btn-primary" style={{marginTop: '20px'}} onClick={handleFileUpload}>
          انتخاب اسناد از سیستم
        </button>
      </div>

      <div className="grid-2-col">
        <div className="card">
          <div className="card-title">صف نوبت‌دهی پردازش اسناد (Ingestion Queue)</div>
          <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
            <div style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '12px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px', fontWeight: 'bold'}}>
                <span>Q3_Financial_Report.pdf</span>
                <span style={{color: 'var(--text-muted)'}}>۲.۹ MB · چانک‌سازی...</span>
              </div>
              <div className="prog-bar-wrap" style={{width: '100%'}}>
                <div className="prog-bar" style={{width: '39%'}}></div>
              </div>
            </div>
            <div style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '12px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px', fontWeight: 'bold'}}>
                <span>HR_Policy_Manual_v2.docx</span>
                <span style={{color: 'var(--text-muted)'}}>۱.۸ MB · بررسی حریم شخصی...</span>
              </div>
              <div className="prog-bar-wrap" style={{width: '100%'}}>
                <div className="prog-bar" style={{width: '62%'}}></div>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            🔒 پیش‌نمایش قفل حریم خصوصی (PII Masking Preview)
            <span className="q-badge qb-done">قفل حریم شخصی فعال</span>
          </div>
          <div style={{fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '12px'}}>پیش‌نمایش زنده و هوشمند اقلام ماسک‌شده:</div>
          
          <div className="pii-demo" style={{whiteSpace: 'pre-wrap'}}>
            {piiPreview ? (
              piiPreview
            ) : (
              <span style={{color: 'var(--text-secondary)', fontStyle: 'italic', opacity: 0.8}}>
                هیچ سندی هنوز بارگذاری نشده است. پیش‌نمایش پوشش اطلاعات حساس (PII) پس از بارگذاری سند در اینجا نمایش داده خواهد شد.
              </span>
            )}
          </div>
          <div style={{fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px'}}>
            {Object.keys(piiAuditCounts).length > 0 ? (
              <span>
                اقلام حساس فیلتر شده در آخرین فایل: {
                  Object.entries(piiAuditCounts)
                    .filter(([, v]) => v > 0)
                    .map(([k, v]) => `${PII_KEY_LABELS[k] || k}: ${v} مورد`)
                    .join(' | ')
                }
              </span>
            ) : piiChecked ? (
              <span style={{color: 'var(--color-success)', fontWeight: '600'}}>
                ✓ هیچ اطلاعات حساسی (مانند کد ملی، تلفن همراه، حساب بانکی و ایمیل) در آخرین سند بارگذاری شده یافت نشد.
              </span>
            ) : piiPreview ? (
              <span>{piiPreview}</span>
            ) : (
              "پیش‌نمایش زنده اقلام"
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
