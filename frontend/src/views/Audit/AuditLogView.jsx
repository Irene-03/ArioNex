import { useEffect, useState } from 'react';
import {
  ScrollText,
  ChevronLeft,
  ChevronRight,
  Search,
  ShieldAlert,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';

const PAGE_SIZE = 20;

export default function AuditLogView() {
  const { apiFetch } = useApp();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [userFilter, setUserFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (userFilter.trim()) params.set('user', userFilter.trim());
      if (statusFilter) params.set('status', statusFilter);
      const res = await apiFetch(`${API_BASE}/v1/audit/logs?${params.toString()}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'خطا در دریافت لاگ');
      }
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Audit fetch failed:', err);
      setError(err.message || 'خطا در دریافت لاگ حسابرسی');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, userFilter, statusFilter]);

  const handleFilterChange = (setter, value) => {
    setter(value);
    setPage(0);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const statusBadge = (st) => {
    const key = String(st || '').toLowerCase();
    if (key === 'success') {
      return { cls: 'ax-badge--success', icon: CheckCircle2, label: 'موفق' };
    }
    if (key.includes('refus')) {
      return { cls: 'ax-badge--warning', icon: ShieldAlert, label: 'امتناع' };
    }
    if (key === 'error') {
      return { cls: 'ax-badge--danger', icon: XCircle, label: 'خطا' };
    }
    return { cls: 'ax-badge--neutral', icon: null, label: st || '—' };
  };

  const formatTime = (iso) => {
    try {
      return new Date(iso).toLocaleString('fa-IR');
    } catch {
      return iso;
    }
  };

  return (
    <div className="screen fade-in">
      <div className="ax-page-header">
        <div>
          <div className="ax-page-header__title">
            <ScrollText size={20} style={{ color: 'var(--copper)' }} />
            لاگ حسابرسی سامانه
          </div>
          <div className="ax-page-header__desc">
            ثبت کامل پرسش‌ها و پاسخ‌ها در تمام کانال‌ها (REST، وب‌ویجت، تلگرام) به همراه زمان پاسخ و مصرف توکن.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="topbar-search" style={{ width: 200 }}>
            <Search size={14} className="search-icon" style={{ color: 'var(--gray-400)' }} />
            <input
              type="text"
              style={{ border: 'none', background: 'transparent', outline: 'none', width: '100%', fontSize: '12.5px', color: 'var(--text-primary)', fontFamily: 'inherit' }}
              placeholder="فیلتر نام کاربر…"
              value={userFilter}
              onChange={(e) => handleFilterChange(setUserFilter, e.target.value)}
            />
          </div>
          <select className="ax-select" style={{ width: 'auto' }} value={statusFilter} onChange={(e) => handleFilterChange(setStatusFilter, e.target.value)} aria-label="فیلتر وضعیت">
            <option value="">همه وضعیت‌ها</option>
            <option value="success">موفق</option>
            <option value="refusal">امتناع</option>
            <option value="error">خطا</option>
          </select>
        </div>
      </div>

      {error && (
        <div style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger)', padding: '12px 16px', borderRadius: 'var(--radius)', marginBottom: 16, fontSize: 13 }}>
          {error}
        </div>
      )}

      <div className="ax-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="ax-table-wrap" style={{ border: 'none', borderRadius: 0, boxShadow: 'none' }}>
          <table className="ax-table">
            <thead>
              <tr>
                <th>زمان</th>
                <th>کاربر</th>
                <th>نقش</th>
                <th>پرسش</th>
                <th>وضعیت</th>
                <th>زمان پاسخ</th>
                <th>توکن (ورودی/خروجی)</th>
              </tr>
            </thead>
            <tbody>
              {items.map(row => {
                const b = statusBadge(row.status);
                const Icon = b.icon;
                return (
                  <tr key={row.id}>
                    <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: 12 }}>{formatTime(row.timestamp)}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.user_name}</td>
                    <td>{row.user_role}</td>
                    <td style={{ maxWidth: 280 }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }} title={row.query_text}>
                        {row.query_text}
                      </div>
                    </td>
                    <td>
                      <span className={`ax-badge ${b.cls}`} style={{ display: 'inline-flex' }}>
                        {Icon && <Icon size={12} />} {b.label}
                      </span>
                    </td>
                    <td>{(row.response_time_ms / 1000).toFixed(1)}s</td>
                    <td>{row.input_tokens} / {row.output_tokens}</td>
                  </tr>
                );
              })}
              {items.length === 0 && !loading && (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 28 }}>
                    رکوردی یافت نشد.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', borderTop: '1px solid var(--gray-100)' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {total.toLocaleString()} رکورد — صفحه {page + 1} از {totalPages}
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="ax-btn ax-btn--secondary ax-btn--sm" disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>
              <ChevronRight size={14} /> قبلی
            </button>
            <button className="ax-btn ax-btn--secondary ax-btn--sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
              بعدی <ChevronLeft size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}