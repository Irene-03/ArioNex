import { useState } from 'react';
import {
  Database,
  Gauge,
  HardDrive,
  FileText,
  Plus,
  Trash2,
  CheckCircle2,
  ShieldCheck,
  Eye,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';
import { useToast, useConfirm } from '../../components/ui/ToastProvider';
import Table from '../../components/ui/Table';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';

export default function KnowledgeView() {
  const { documents, setDocuments, currentUser, apiFetch, setActiveScreen, stats, cosineThreshold } = useApp();
  const toast = useToast();
  const confirmDialog = useConfirm();

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handleChangeRole = async (doc, newRole) => {
    try {
      const res = await apiFetch(`${API_BASE}/v1/knowledge/documents/${doc.id}/role`, {
        method: 'PUT',
        body: JSON.stringify({ min_role_required: newRole }),
      });
      if (res.ok) {
        setDocuments(prev => prev.map(d => (d.id === doc.id ? { ...d, min_role_required: newRole } : d)));
        toast.success('سطح دسترسی به‌روزرسانی شد', `سند «${doc.name}»`);
      } else {
        const errData = await res.json();
        toast.error('خطا در تغییر سطح دسترسی', errData.detail);
      }
    } catch (err) {
      console.error(err);
      toast.error('خطا در تغییر سطح دسترسی', 'خطا در ارتباط با سرور');
    }
  };

  const handleDelete = async (doc) => {
    const confirmed = await confirmDialog({
      title: 'حذف سند',
      desc: `آیا از حذف سند «${doc.name}» و تمامی بردارهای مرتبط با آن اطمینان دارید؟`,
      confirmLabel: 'حذف سند',
      cancelLabel: 'انصراف',
    });
    if (!confirmed) return;
    try {
      const res = await apiFetch(`${API_BASE}/v1/knowledge/documents/${doc.id}`, { method: 'DELETE' });
      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.id !== doc.id));
        toast.success('سند حذف شد', `سند «${doc.name}» حذف شد.`);
      } else {
        const errData = await res.json();
        toast.error('خطا در حذف سند', errData.detail);
      }
    } catch (err) {
      console.error(err);
      toast.error('خطا در حذف سند', 'خطا در ارتباط با سرور');
    }
  };

  const handlePreview = async (doc) => {
    setPreviewDoc(doc);
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewContent(null);
    try {
      const res = await apiFetch(`${API_BASE}/v1/knowledge/documents/${doc.id}/content`);
      if (res.ok) {
        const data = await res.json();
        setPreviewContent(data);
      } else {
        const errData = await res.json();
        toast.error('خطا در دریافت محتوا', errData.detail);
        setPreviewOpen(false);
      }
    } catch (err) {
      console.error(err);
      toast.error('خطا در دریافت محتوا', 'خطا در ارتباط با سرور');
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const statCards = [
    {
      label: 'تعداد کل قطعات و بردارها',
      value: `${stats.total_chunks} قطعه`,
      hint: 'مستقر در افزونه PostgreSQL pgvector',
      icon: Database,
      color: 'var(--brand)',
    },
    {
      label: 'حد آستانه شباهت بازیابی',
      value: `Cosine ${cosineThreshold.toFixed(2)}`,
      hint: 'قابل تنظیم جهت ممانعت از توهم',
      icon: Gauge,
      color: 'var(--copper)',
    },
    {
      label: 'حجم دیسک اشغال شده',
      value: stats.disk_usage_gb >= 1 ? `${stats.disk_usage_gb.toFixed(2)} GB` : `${(stats.disk_usage_gb * 1024).toFixed(0)} MB`,
      hint: 'فضای تخمینی دیتابیس و استوریج',
      icon: HardDrive,
      color: 'var(--color-success)',
    },
  ];

  const columns = [
    {
      key: 'name',
      label: 'نام سند',
      render: doc => (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-primary)', fontWeight: 600 }}>
          <FileText size={15} style={{ color: 'var(--gray-400)' }} />
          {doc.name}
        </span>
      ),
    },
    { key: 'size', label: 'حجم فیزیکی', render: doc => <span style={{ color: 'var(--text-secondary)' }}>{doc.size}</span> },
    { key: 'date', label: 'تاریخ پردازش', render: doc => <span style={{ color: 'var(--text-muted)' }}>{doc.date}</span> },
    {
      key: 'role',
      label: 'سطح دسترسی',
      render: doc =>
        currentUser?.role === 'Admin' ? (
          <select
            value={doc.min_role_required || 'Analyst'}
            onChange={(e) => handleChangeRole(doc, e.target.value)}
            className="ax-select"
            style={{ padding: '5px 10px', fontSize: 12, width: 'auto' }}
            aria-label="سطح دسترسی سند"
          >
            <option value="Analyst">تحلیل‌گر</option>
            <option value="Admin">مدیر سیستم</option>
          </select>
        ) : (
          <Badge variant={doc.min_role_required === 'Admin' ? 'warning' : 'info'}>
            {doc.min_role_required === 'Admin' ? 'مدیر سیستم' : 'تحلیلگر'}
          </Badge>
        ),
    },
    {
      key: 'status',
      label: 'وضعیت و عملیات',
      render: doc => (
        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          {doc.status === 'ready' ? (
            <Badge variant="success">
              <CheckCircle2 size={12} /> ایندکس شده
            </Badge>
          ) : (
            <span style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
              <span className="prog-bar-wrap" style={{ width: 60 }}>
                <span className="prog-bar" style={{ display: 'block', width: `${doc.progress}%` }} />
              </span>
              <span style={{ fontSize: 11, color: 'var(--copper-dark)', fontWeight: 'bold' }}>{doc.progress}%</span>
            </span>
          )}
          <button className="icon-btn" onClick={() => handlePreview(doc)} title="پیش‌نمایش سند" aria-label="پیش‌نمایش سند">
            <Eye size={15} />
          </button>
          {currentUser?.role === 'Admin' && (
            <button className="icon-btn icon-btn--danger" onClick={() => handleDelete(doc)} title="حذف سند" aria-label="حذف سند">
              <Trash2 size={15} />
            </button>
          )}
        </span>
      ),
    },
  ];

  return (
    <div className="screen fade-in">
      <PageHeader
        icon={<Database size={18} style={{ color: 'var(--copper)' }} />}
        title="پایگاه دانش"
        desc="مدیریت و توزیع منابع دانش"
        actions={
          <button className="ax-btn ax-btn--primary" onClick={() => setActiveScreen('upload')}>
            <Plus size={16} /> افزودن فایل جدید
          </button>
        }
      />

      <div className="stats-row" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        {statCards.map(card => {
          const Icon = card.icon;
          return (
            <div className="stat-card stat-accent" key={card.label}>
              <div className="stat-label">
                <Icon />
                {card.label}
              </div>
              <div className="stat-value">{card.value}</div>
              <div className="stat-change" style={{ color: 'var(--text-muted)' }}>{card.hint}</div>
            </div>
          );
        })}
      </div>

      <div className="ax-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="ax-card__header" style={{ padding: '18px 20px 12px', margin: 0 }}>
          <div className="ax-card__title">
            <ShieldCheck size={16} style={{ color: 'var(--copper)' }} />
            لیست اسناد و دیتای متصل به پایگاه دانش
          </div>
        </div>
        <Table
          columns={columns}
          rows={documents}
          rowKey="id"
          emptyTitle="سندی ثبت نشده است"
          emptyDesc="برای افزودن اولین سند، از دکمه «افزودن فایل جدید» استفاده کنید."
        />
      </div>

      <Modal
        open={previewOpen}
        title={previewDoc ? `پیش‌نمایش: ${previewDoc.name}` : 'پیش‌نمایش سند'}
        onClose={() => { setPreviewOpen(false); setPreviewContent(null); setPreviewDoc(null); }}
        maxWidth={720}
      >
        {previewLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
            در حال بارگذاری محتوا...
          </div>
        )}
        {!previewLoading && previewContent && (
          <div style={{ maxHeight: '65vh', overflow: 'auto' }}>
            {previewContent.file_type === 'pdf' ? (
              <iframe
                src={`data:application/pdf;base64,${previewContent.content}`}
                style={{ width: '100%', height: '60vh', border: 'none', borderRadius: 6 }}
                title={previewContent.filename}
              />
            ) : previewContent.file_type === 'csv' ? (
              <PreviewCSV content={previewContent.content} />
            ) : previewContent.file_type === 'docx' || previewContent.file_type === 'doc' ? (
              <pre style={preStyle}>{previewContent.content}</pre>
            ) : previewContent.file_type === 'txt' || previewContent.file_type === 'json' || previewContent.file_type === 'xml' ? (
              <pre style={preStyle}>{previewContent.content}</pre>
            ) : previewContent.file_type === 'jpg' || previewContent.file_type === 'jpeg' || previewContent.file_type === 'png' ? (
              <img
                src={`data:${previewContent.mime_type};base64,${previewContent.content}`}
                alt={previewContent.filename}
                style={{ maxWidth: '100%', borderRadius: 6 }}
              />
            ) : (
              <pre style={preStyle}>{previewContent.content || '[محتوای این نوع فایل قابل نمایش نیست]'}</pre>
            )}
            <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 16 }}>
              <span>نوع فایل: {previewContent.file_type.toUpperCase()}</span>
              <span>حجم: {previewContent.size_bytes > 1024 * 1024
                ? `${(previewContent.size_bytes / (1024 * 1024)).toFixed(2)} MB`
                : `${(previewContent.size_bytes / 1024).toFixed(1)} KB`}</span>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

const preStyle = {
  margin: 0,
  padding: 16,
  background: 'var(--bg-secondary, #f5f5f5)',
  borderRadius: 6,
  fontSize: 13,
  lineHeight: 1.8,
  direction: 'rtl',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  fontFamily: 'Vazirmatn, monospace',
  maxHeight: '60vh',
  overflow: 'auto',
};

function PreviewCSV({ content }) {
  const lines = content.split('\n').filter(l => l.trim());
  if (lines.length === 0) return <pre style={preStyle}>فایل خالی است</pre>;

  const parseCSVLine = (line) => {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    result.push(current.trim());
    return result;
  };

  const headers = parseCSVLine(lines[0]);
  const rows = lines.slice(1).map(parseCSVLine);

  return (
    <div style={{ overflow: 'auto', maxHeight: '55vh' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, direction: 'rtl' }}>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} style={{ padding: '8px 12px', background: 'var(--bg-tertiary, #e8e8e8)', borderBottom: '2px solid var(--border, #ddd)', textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ padding: '6px 12px', borderBottom: '1px solid var(--border, #eee)', textAlign: 'right', whiteSpace: 'nowrap' }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
