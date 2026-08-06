import {
  Radar,
  Layers,
  CheckCircle2,
  Loader2,
  Globe,
  Database,
  XCircle,
  Trash2,
  Zap,
  ExternalLink,
  Bug,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';
import { useToast, useConfirm } from '../../components/ui/ToastProvider';
import { Input } from '../../components/ui/Fields';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';

const STATUS_META = {
  queued: { color: 'var(--text-muted)', bg: 'var(--gray-100)', label: 'در صف', icon: Layers },
  running: { color: 'var(--copper)', bg: 'var(--copper-pale)', label: 'در حال کرال', icon: Loader2 },
  completed: { color: 'var(--color-success)', bg: 'var(--color-success-bg)', label: 'تکمیل', icon: CheckCircle2 },
  failed: { color: 'var(--color-danger)', bg: 'var(--color-danger-bg)', label: 'خطا', icon: XCircle },
  cancelled: { color: 'var(--text-muted)', bg: 'var(--gray-100)', label: 'لغو شد', icon: XCircle },
};

export default function CrawlerView() {
  const {
    crawlJobs,
    setCrawlJobs,
    crawlUrl,
    setCrawlUrl,
    crawlMaxPages,
    setCrawlMaxPages,
    crawlMaxDepth,
    setCrawlMaxDepth,
    crawlJsRender,
    setCrawlJsRender,
    crawlFollowExternal,
    setCrawlFollowExternal,
    crawlRobots,
    setCrawlRobots,
    crawlSubmitting,
    setCrawlSubmitting,
    crawlStatusFilter,
    setCrawlStatusFilter,
    apiFetch,
  } = useApp();
  const toast = useToast();
  const confirmDialog = useConfirm();

  const statCards = [
    { label: 'کل jobهای کرال', value: crawlJobs.length, icon: Layers, color: 'var(--navy)' },
    { label: 'تکمیل‌شده', value: crawlJobs.filter(j => j.status === 'completed').length, icon: CheckCircle2, color: 'var(--color-success)' },
    { label: 'در حال اجرا', value: crawlJobs.filter(j => j.status === 'running').length, icon: Loader2, color: 'var(--copper)' },
    { label: 'کل chunkهای ایندکس', value: crawlJobs.reduce((s, j) => s + (j.chunks_indexed || 0), 0), icon: Database, color: 'var(--color-info)' },
  ];

  const filters = ['', 'queued', 'running', 'completed', 'failed'];

  const cancelJob = async (job) => {
    try {
      const res = await apiFetch(`${API_BASE}/v1/crawl/${job.job_id}`, { method: 'DELETE' });
      if (res.ok) {
        setCrawlJobs(prev => prev.map(j => (j.job_id === job.job_id ? { ...j, status: 'cancelled' } : j)));
        toast.info('کرال لغو شد');
      }
    } catch {
      toast.error('خطا در لغو کرال');
    }
  };

  const deleteJob = async (job) => {
    const confirmed = await confirmDialog({
      title: 'حذف تاریخچه کرال',
      desc: 'آیا از حذف دائم این تاریخچه اطمینان دارید؟',
      confirmLabel: 'حذف',
      cancelLabel: 'انصراف',
    });
    if (!confirmed) return;
    try {
      const res = await apiFetch(`${API_BASE}/v1/crawl/${job.job_id}?hard_delete=true`, { method: 'DELETE' });
      if (res.ok) {
        setCrawlJobs(prev => prev.filter(j => j.job_id !== job.job_id));
        toast.success('تاریخچه حذف شد');
      }
    } catch {
      toast.error('خطا در حذف تاریخچه');
    }
  };

  return (
    <div className="screen fade-in">
      <PageHeader
        icon={<Radar size={20} style={{ color: 'var(--copper)' }} />}
        title="کرالر هوشمند وب‌سایت"
      />

      <div className="stats-row">
        {statCards.map(card => {
          const Icon = card.icon;
          return (
            <div className="stat-card" key={card.label} style={{ borderTop: `3px solid ${card.color}` }}>
              <div className="stat-label">
                <Icon />
                {card.label}
              </div>
              <div className="stat-value">{card.value}</div>
            </div>
          );
        })}
      </div>

      <div className="two-col">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="ax-card">
            <div className="ax-card__title">
              <Globe size={16} style={{ color: 'var(--copper)' }} />
              شروع کرال جدید
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!crawlUrl.trim() || crawlSubmitting) return;
                setCrawlSubmitting(true);
                try {
                  const res = await apiFetch(`${API_BASE}/v1/crawl/start`, {
                    method: 'POST',
                    body: JSON.stringify({
                      url: crawlUrl,
                      max_pages: crawlMaxPages,
                      max_depth: crawlMaxDepth,
                      js_render: crawlJsRender,
                      follow_external_domains: crawlFollowExternal,
                      respect_robots: crawlRobots,
                    }),
                  });
                  const data = await res.json();
                  if (res.ok) {
                    setCrawlJobs(prev => [data, ...prev]);
                    setCrawlUrl('');
                    toast.success('کرال ثبت شد', 'عملیات خزش به صف اضافه شد.');
                  } else {
                    toast.error('خطا در شروع کرال', data.detail);
                  }
                } catch {
                  toast.error('خطا در اتصال به سرور');
                } finally {
                  setCrawlSubmitting(false);
                }
              }}
              style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 16 }}
            >
              <Input
                label="آدرس وب‌سایت (URL ریشه)"
                type="url"
                ltr
                placeholder="https://example.com"
                value={crawlUrl}
                onChange={(e) => setCrawlUrl(e.target.value)}
                required
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Input
                  label="حداکثر صفحات"
                  type="number"
                  value={crawlMaxPages}
                  onChange={(e) => setCrawlMaxPages(parseInt(e.target.value) || 10)}
                  min="1"
                  max="1000"
                />
                <Input
                  label="حداکثر عمق پیوند"
                  type="number"
                  value={crawlMaxDepth}
                  onChange={(e) => setCrawlMaxDepth(parseInt(e.target.value) || 1)}
                  min="1"
                  max="10"
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={crawlJsRender} onChange={(e) => setCrawlJsRender(e.target.checked)} />
                  رندر صفحات با جاوااسکریپت (Playwright)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={crawlFollowExternal} onChange={(e) => setCrawlFollowExternal(e.target.checked)} />
                  دنبال کردن دامنه‌های خارجی مرتبط
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={crawlRobots} onChange={(e) => setCrawlRobots(e.target.checked)} />
                  رعایت قوانین robots.txt
                </label>
              </div>

              <button
                type="submit"
                className="ax-btn ax-btn--primary"
                style={{ width: '100%', padding: 12 }}
                disabled={crawlSubmitting}
              >
                {crawlSubmitting ? <Loader2 size={16} className="ax-spin" /> : <Zap size={16} />}
                {crawlSubmitting ? 'در حال ثبت در صف...' : 'شروع عملیات خزش و نمایه‌سازی'}
              </button>
            </form>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <div className="card-title" style={{ margin: 0 }}>کارهای کرالر</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {filters.map(s => (
                <button
                  key={s}
                  onClick={() => setCrawlStatusFilter(s)}
                  className="ax-btn ax-btn--sm"
                  style={{
                    border: '1px solid',
                    background: crawlStatusFilter === s ? 'var(--navy)' : 'transparent',
                    color: crawlStatusFilter === s ? '#fff' : 'var(--text-muted)',
                    borderColor: crawlStatusFilter === s ? 'var(--navy)' : 'var(--gray-200)',
                  }}
                >
                  {s === '' ? 'همه' : STATUS_META[s]?.label || s}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16, overflowY: 'auto', flex: 1, maxHeight: 480 }}>
            {crawlJobs.filter(j => !crawlStatusFilter || j.status === crawlStatusFilter).length === 0 ? (
              <EmptyState
                icon={<Radar />}
                title="هیچ job کرالی یافت نشد"
                desc="یک URL را کرال کنید تا اینجا نمایش داده شود."
              />
            ) : (
              crawlJobs
                .filter(j => !crawlStatusFilter || j.status === crawlStatusFilter)
                .map(job => {
                  const meta = STATUS_META[job.status] || { color: 'var(--text-muted)', bg: 'var(--gray-100)', label: job.status, icon: Layers };
                  const StatusIcon = meta.icon;
                  const progress = job.max_pages > 0 ? Math.round((job.pages_crawled / job.max_pages) * 100) : 0;

                  return (
                    <div key={job.job_id} style={{ border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: 14, background: 'var(--gray-50)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, gap: 10 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--navy)', direction: 'ltr', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <ExternalLink size={13} style={{ color: 'var(--copper)', flexShrink: 0 }} />
                            {job.url}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3, direction: 'ltr' }}>
                            {job.job_id ? job.job_id.substring(0, 24) : ''}...
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                          <Badge variant="neutral" className="" style={{ background: meta.bg, color: meta.color, border: 'none' }}>
                            <StatusIcon size={12} /> {meta.label}
                          </Badge>
                          {(job.status === 'queued' || job.status === 'running') && (
                            <button className="ax-btn ax-btn--danger-ghost ax-btn--sm" onClick={() => cancelJob(job)}>
                              لغو
                            </button>
                          )}
                          {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                            <button className="icon-btn icon-btn--danger" onClick={() => deleteJob(job)} title="حذف تاریخچه" aria-label="حذف تاریخچه">
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      </div>

                      {(job.status === 'running' || job.status === 'completed') && (
                        <div style={{ marginBottom: 10 }}>
                          <span className="prog-bar-wrap" style={{ display: 'block', width: '100%' }}>
                            <span
                              className="prog-bar"
                              style={{
                                display: 'block',
                                width: `${Math.min(progress || 0, 100)}%`,
                                background: job.status === 'completed' ? 'var(--color-success)' : 'linear-gradient(90deg, var(--copper), var(--copper-light))',
                              }}
                            />
                          </span>
                        </div>
                      )}

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, fontSize: 11.5 }}>
                        <div style={{ textAlign: 'center', background: '#fff', borderRadius: 4, padding: 6 }}>
                          <div style={{ fontWeight: 700, color: 'var(--navy)' }}>{job.pages_crawled ?? 0}</div>
                          <div style={{ color: 'var(--text-muted)' }}>صفحه کرال شد</div>
                        </div>
                        <div style={{ textAlign: 'center', background: '#fff', borderRadius: 4, padding: 6 }}>
                          <div style={{ fontWeight: 700, color: 'var(--copper)' }}>{job.chunks_indexed ?? 0}</div>
                          <div style={{ color: 'var(--text-muted)' }}>chunk ایندکس</div>
                        </div>
                        <div style={{ textAlign: 'center', background: '#fff', borderRadius: 4, padding: 6 }}>
                          <div style={{ fontWeight: 700, color: (job.pages_failed || 0) > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                            {job.pages_failed ?? 0}
                          </div>
                          <div style={{ color: 'var(--text-muted)' }}>صفحه ناموفق</div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                        <span className="file-pill" style={{ fontSize: 10.5, padding: '2px 8px' }}>عمق: {job.max_depth ?? 0}</span>
                        {job.js_render && <span className="file-pill" style={{ fontSize: 10.5, padding: '2px 8px', background: 'rgba(196,137,74,0.12)', color: 'var(--copper-dark)' }}>JS Render</span>}
                        {job.follow_external_domains && <span className="file-pill" style={{ fontSize: 10.5, padding: '2px 8px', background: 'rgba(29,78,216,0.08)', color: 'var(--color-info)' }}>دامنه خارجی</span>}
                        {job.label && <span className="file-pill" style={{ fontSize: 10.5, padding: '2px 8px', fontFamily: 'monospace', direction: 'ltr' }}>{job.label}</span>}
                      </div>

                      {job.error_message && (
                        <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--color-danger)', background: 'var(--color-danger-bg)', padding: '6px 10px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Bug size={13} /> {job.error_message}
                        </div>
                      )}
                    </div>
                  );
                })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
