import {
  Database,
  Gauge,
  HardDrive,
  FileText,
  Plus,
  Trash2,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';
import { useToast, useConfirm } from '../../components/ui/ToastProvider';
import Table from '../../components/ui/Table';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';

export default function KnowledgeView() {
  const { documents, setDocuments, currentUser, apiFetch, setActiveScreen, stats, cosineThreshold } = useApp();
  const toast = useToast();
  const confirmDialog = useConfirm();

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
        icon={<Database size={20} style={{ color: 'var(--copper)' }} />}
        title="پایگاه دانش"
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
            <div className="stat-card" key={card.label} style={{ borderRight: `4px solid ${card.color}` }}>
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
    </div>
  );
}
