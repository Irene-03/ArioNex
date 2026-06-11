import React from 'react';
import { useApp } from '../../context/AppContext';

export default function KnowledgeView() {
  const {
    documents,
    setDocuments,
    currentUser,
    apiFetch,
    fetchDocuments,
    setActiveScreen,
    stats,
    cosineThreshold
  } = useApp();

  return (
    <div className="screen fade-in">
      <div className="grid-3-col">
        <div className="card" style={{borderRight: '4px solid var(--navy)'}}>
          <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>تعداد کل قطعات و بردارها (Chunks)</div>
          <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>{stats.total_chunks} قطعه</div>
          <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>مستقر در افزونه PostgreSQL pgvector</div>
        </div>
        <div className="card" style={{borderRight: '4px solid var(--copper)'}}>
          <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>حد آستانه شباهت بازیابی (Threshold)</div>
          <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>Cosine {cosineThreshold.toFixed(2)}</div>
          <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>قابل تنظیم جهت ممانعت از توهم و ورود داده کاذب</div>
        </div>
        <div className="card" style={{borderRight: '4px solid var(--color-success)'}}>
          <div style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px'}}>حجم دیسک اشغال شده</div>
          <div style={{fontSize: '26px', fontWeight: '800', color: 'var(--navy)'}}>{stats.disk_usage_gb >= 1 ? `${stats.disk_usage_gb.toFixed(2)} GB` : `${(stats.disk_usage_gb * 1024).toFixed(0)} MB`}</div>
          <div style={{fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px'}}>فضای تخمینی دیتابیس و استوریج</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          لیست اسناد و دیتای متصل به پایگاه دانش
          <span className="card-link" onClick={() => setActiveScreen('upload')}>+ افزودن فایل جدید</span>
        </div>
        
        <div className="files-table">
          <div className="ft-header" style={{gridTemplateColumns: '2fr 1fr 1fr 1.2fr 1.2fr'}}>
            <div>نام سند</div>
            <div>حجم فیزیکی</div>
            <div>تاریخ پردازش</div>
            <div>سطح دسترسی</div>
            <div>وضعیت و عملیات</div>
          </div>
          
          {documents.map(doc => (
            <div key={doc.id} className="ft-row" style={{gridTemplateColumns: '2fr 1fr 1fr 1.2fr 1.2fr'}}>
              <div className="ft-filename">
                <span className={`ft-ext ext-${doc.ext.toLowerCase()}`}>{doc.ext}</span>
                {doc.name}
              </div>
              <div style={{color: 'var(--text-secondary)'}}>{doc.size}</div>
              <div style={{color: 'var(--text-muted)'}}>{doc.date}</div>
              <div>
                {currentUser?.role === 'Admin' ? (
                  <select
                    value={doc.min_role_required || 'Analyst'}
                    onChange={async (e) => {
                      const newRole = e.target.value;
                      try {
                        const res = await apiFetch(`http://localhost:8000/v1/knowledge/documents/${doc.id}/role`, {
                          method: 'PUT',
                          body: JSON.stringify({ min_role_required: newRole })
                        });
                        if (res.ok) {
                          setDocuments(prev => prev.map(d => d.id === doc.id ? { ...d, min_role_required: newRole } : d));
                        } else {
                          const errData = await res.json();
                          alert(errData.detail || 'خطا در تغییر سطح دسترسی');
                        }
                      } catch (err) {
                        console.error(err);
                        alert('خطا در تغییر سطح دسترسی');
                      }
                    }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      border: '1px solid var(--gray-200)',
                      fontSize: '12px',
                      background: 'var(--gray-50)',
                      color: 'var(--text-primary)',
                      fontFamily: 'inherit',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="Analyst">تحلیل‌گر (Analyst)</option>
                    <option value="Admin">مدیر سیستم (Admin)</option>
                  </select>
                ) : (
                  <span className={`perm-badge ${doc.min_role_required === 'Admin' ? 'p-admin' : 'p-analyst'}`}>
                    {doc.min_role_required === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}
                  </span>
                )}
              </div>
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px'}}>
                {doc.status === 'ready' ? (
                  <span className="q-badge qb-done">✓ ایندکس شده</span>
                ) : (
                  <div style={{display: 'flex', alignItems: 'center', gap: '8px', flex: 1}}>
                    <div className="prog-bar-wrap" style={{width: '60px'}}>
                      <div className="prog-bar" style={{width: `${doc.progress}%`}}></div>
                    </div>
                    <span style={{fontSize: '11px', color: 'var(--copper-dark)', fontWeight: 'bold'}}>{doc.progress}%</span>
                  </div>
                )}
                
                {currentUser?.role === 'Admin' && (
                  <button
                    onClick={async () => {
                      if (!confirm(`آیا از حذف سند "${doc.name}" و تمامی بردارهای مرتبط با آن اطمینان دارید؟`)) return;
                      try {
                        const res = await apiFetch(`http://localhost:8000/v1/knowledge/documents/${doc.id}`, {
                          method: 'DELETE'
                        });
                        if (res.ok) {
                          setDocuments(prev => prev.filter(d => d.id !== doc.id));
                        } else {
                          const errData = await res.json();
                          alert(errData.detail || 'خطا در حذف سند');
                        }
                      } catch (err) {
                        console.error(err);
                        alert('خطا در ارتباط با سرور');
                      }
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#c62828',
                      cursor: 'pointer',
                      fontSize: '15px',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'transform var(--transition-fast)'
                    }}
                    title="حذف سند"
                  >
                    🗑️
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
