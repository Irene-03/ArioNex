import React from 'react';
import { useApp } from '../../context/AppContext';

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
    apiFetch
  } = useApp();

  return (
    <div className="screen fade-in">
      {/* آمار کلی job‌ها */}
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px'}}>
        <div className="card" style={{borderTop: '3px solid var(--navy)'}}>
          <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>کل job‌های کرال</div>
          <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--navy)'}}>{crawlJobs.length}</div>
        </div>
        <div className="card" style={{borderTop: '3px solid var(--color-success)'}}>
          <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>تکمیل‌شده</div>
          <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--color-success)'}}>{crawlJobs.filter(j => j.status === 'completed').length}</div>
        </div>
        <div className="card" style={{borderTop: '3px solid var(--copper)'}}>
          <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>در حال اجرا</div>
          <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--copper)'}}>{crawlJobs.filter(j => j.status === 'running').length}</div>
        </div>
        <div className="card" style={{borderTop: '3px solid var(--color-info)'}}>
          <div style={{fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px'}}>کل chunk‌های ایندکس</div>
          <div style={{fontSize: '24px', fontWeight: '800', color: 'var(--navy)'}}>{crawlJobs.reduce((s, j) => s + (j.chunks_indexed || 0), 0)}</div>
        </div>
      </div>

      <div className="two-col">
        {/* فرم ایجاد job جدید */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
          <div className="card">
            <div className="card-title">🕷️ شروع کرال وب‌سایت جدید</div>
            <div style={{fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', marginBottom: '16px'}}>
              آدرس وب‌سایت را وارد کنید. سیستم تمام صفحات را به صورت async کرال کرده، محتوا را chunk و در پایگاه دانش ایندکس می‌کند.
            </div>

            <form onSubmit={async (e) => {
              e.preventDefault();
              if (!crawlUrl.trim() || crawlSubmitting) return;
              setCrawlSubmitting(true);
              try {
                const res = await apiFetch('http://localhost:8000/v1/crawl/start', {
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
                } else {
                  alert(data.detail || 'خطا در شروع کرال');
                }
              } catch(err) {
                alert('خطا در اتصال به سرور');
              } finally {
                setCrawlSubmitting(false);
              }
            }} style={{display: 'flex', flexDirection: 'column', gap: '14px'}}>

              <div>
                <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>آدرس وب‌سایت (URL ریشه)</label>
                <input
                  type="url"
                  id="crawl-url-input"
                  className="chat-input-box"
                  style={{borderRadius: 'var(--radius)', width: '100%', direction: 'ltr', fontSize: '13px'}}
                  placeholder="https://example.com"
                  value={crawlUrl}
                  onChange={e => setCrawlUrl(e.target.value)}
                  required
                />
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
                <div>
                  <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>حداکثر صفحات</label>
                  <input
                    type="number"
                    className="chat-input-box"
                    style={{borderRadius: 'var(--radius)', width: '100%'}}
                    value={crawlMaxPages}
                    onChange={e => setCrawlMaxPages(parseInt(e.target.value) || 10)}
                    min="1"
                    max="1000"
                  />
                </div>
                <div>
                  <label style={{fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600'}}>حداکثر عمق پیوند (Depth)</label>
                  <input
                    type="number"
                    className="chat-input-box"
                    style={{borderRadius: 'var(--radius)', width: '100%'}}
                    value={crawlMaxDepth}
                    onChange={e => setCrawlMaxDepth(parseInt(e.target.value) || 1)}
                    min="1"
                    max="10"
                  />
                </div>
              </div>

              {/* گزینه‌های چک‌باکس پیشرفته */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '6px'}}>
                <label style={{display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--text-secondary)', cursor: 'pointer'}}>
                  <input
                    type="checkbox"
                    checked={crawlJsRender}
                    onChange={e => setCrawlJsRender(e.target.checked)}
                  />
                  رندر صفحات با جاوااسکریپت (JS Rendering via Playwright)
                </label>

                <label style={{display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--text-secondary)', cursor: 'pointer'}}>
                  <input
                    type="checkbox"
                    checked={crawlFollowExternal}
                    onChange={e => setCrawlFollowExternal(e.target.checked)}
                  />
                  دنبال کردن دامنه‌های فرعی خارجی مرتبط (Score-based heuristic)
                </label>

                <label style={{display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--text-secondary)', cursor: 'pointer'}}>
                  <input
                    type="checkbox"
                    checked={crawlRobots}
                    onChange={e => setCrawlRobots(e.target.checked)}
                  />
                  رعایت قوانین فایل robots.txt وب‌سایت هدف
                </label>
              </div>

              <button
                type="submit"
                id="crawl-start-btn"
                className="topbar-btn btn-primary"
                style={{width: '100%', justifyContent: 'center', padding: '12px', marginTop: '10px'}}
                disabled={crawlSubmitting}
              >
                {crawlSubmitting ? '⏳ در حال ثبت در صف...' : '🕷️ شروع عملیات خزش و نمایه سازی'}
              </button>
            </form>
          </div>
        </div>

        {/* لیست کارهای ثبت‌شده */}
        <div className="card" style={{display: 'flex', flexDirection: 'column'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
            <div className="card-title" style={{margin: 0}}>کارهای کرالر فعال و اخیر</div>
            
            {/* فیلتر وضعیت */}
            <div style={{display: 'flex', gap: '4px'}}>
              {['', 'queued', 'running', 'completed', 'failed'].map(s => (
                <button
                  key={s}
                  onClick={() => setCrawlStatusFilter(s)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    borderRadius: '12px',
                    border: '1px solid',
                    cursor: 'pointer',
                    fontWeight: crawlStatusFilter === s ? '700' : '400',
                    background: crawlStatusFilter === s ? 'var(--navy)' : 'transparent',
                    color: crawlStatusFilter === s ? '#fff' : 'var(--text-muted)',
                    borderColor: crawlStatusFilter === s ? 'var(--navy)' : 'var(--gray-100)',
                  }}
                >
                  {s === '' ? 'همه' : s === 'queued' ? 'صف' : s === 'running' ? 'در حال اجرا' : s === 'completed' ? 'تکمیل' : 'خطا'}
                </button>
              ))}
            </div>
          </div>

          <div style={{display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px', overflowY: 'auto', flex: 1, maxHeight: '420px'}}>
            {crawlJobs
              .filter(j => !crawlStatusFilter || j.status === crawlStatusFilter)
              .map(job => {
                const statusColor = {
                  queued: 'var(--text-muted)',
                  running: 'var(--copper)',
                  completed: 'var(--color-success)',
                  failed: '#c62828',
                  cancelled: 'var(--text-muted)',
                }[job.status] || 'var(--text-muted)';

                const statusLabel = {
                  queued: '⏳ در صف',
                  running: '⚡ در حال کرال',
                  completed: '✅ تکمیل',
                  failed: '❌ خطا',
                  cancelled: '🚫 لغو شد',
                }[job.status] || job.status;

                const progress = job.max_pages > 0 ? Math.round((job.pages_crawled / job.max_pages) * 100) : 0;

                return (
                  <div key={job.job_id} style={{border: '1px solid var(--gray-100)', borderRadius: 'var(--radius)', padding: '14px', background: 'var(--gray-50)'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px'}}>
                      <div style={{flex: 1, minWidth: 0}}>
                        <div style={{fontWeight: '600', fontSize: '13px', color: 'var(--navy)', direction: 'ltr', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                          {job.url}
                        </div>
                        <div style={{fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px', direction: 'ltr'}}>
                          {job.job_id ? job.job_id.substring(0, 20) : ''}...
                        </div>
                      </div>
                      <div style={{display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0, marginRight: '10px'}}>
                        <span style={{fontSize: '12px', fontWeight: '700', color: statusColor}}>{statusLabel}</span>
                        {(job.status === 'queued' || job.status === 'running') && (
                          <button
                            onClick={async () => {
                              const res = await apiFetch(`http://localhost:8000/v1/crawl/${job.job_id}`, {method: 'DELETE'});
                              if (res.ok) {
                                setCrawlJobs(prev => prev.map(j => j.job_id === job.job_id ? {...j, status: 'cancelled'} : j));
                              }
                            }}
                            style={{background: '#ffebee', color: '#c62828', border: 'none', borderRadius: '4px', padding: '3px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold'}}
                          >
                            لغو
                          </button>
                        )}
                        {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                          <button
                            onClick={async () => {
                              if (!window.confirm('آیا از حذف دائم این تاریخچه اطمینان دارید؟')) return;
                              const res = await apiFetch(`http://localhost:8000/v1/crawl/${job.job_id}?hard_delete=true`, {method: 'DELETE'});
                              if (res.ok) {
                                setCrawlJobs(prev => prev.filter(j => j.job_id !== job.job_id));
                              }
                            }}
                            style={{background: '#f1f5f9', color: 'var(--text-muted)', border: 'none', borderRadius: '4px', padding: '3px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold', transition: '0.2s'}}
                            onMouseOver={e => e.target.style.background = '#e2e8f0'}
                            onMouseOut={e => e.target.style.background = '#f1f5f9'}
                          >
                            حذف
                          </button>
                        )}
                      </div>
                    </div>

                    {/* نوار پیشرفت */}
                    {(job.status === 'running' || job.status === 'completed') && (
                      <div style={{marginBottom: '10px'}}>
                        <div className="prog-bar-wrap" style={{width: '100%'}}>
                          <div className="prog-bar" style={{width: `${Math.min(progress || 0, 100)}%`, background: job.status === 'completed' ? 'var(--color-success)' : 'linear-gradient(90deg, var(--copper), var(--copper-light))'}} />
                        </div>
                      </div>
                    )}

                    {/* آمار */}
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '11.5px'}}>
                      <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                        <div style={{fontWeight: '700', color: 'var(--navy)'}}>{job.pages_crawled ?? 0}</div>
                        <div style={{color: 'var(--text-muted)'}}>صفحه کرال شد</div>
                      </div>
                      <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                        <div style={{fontWeight: '700', color: 'var(--copper)'}}>{job.chunks_indexed ?? 0}</div>
                        <div style={{color: 'var(--text-muted)'}}>chunk ایندکس</div>
                      </div>
                      <div style={{textAlign: 'center', background: '#fff', borderRadius: '4px', padding: '6px'}}>
                        <div style={{fontWeight: '700', color: (job.pages_failed || 0) > 0 ? '#c62828' : 'var(--color-success)'}}>{job.pages_failed ?? 0}</div>
                        <div style={{color: 'var(--text-muted)'}}>صفحه ناموفق</div>
                      </div>
                    </div>

                    {/* تگ‌های تنظیمات */}
                    <div style={{display: 'flex', gap: '6px', marginTop: '10px', flexWrap: 'wrap'}}>
                      <span style={{fontSize: '10.5px', background: 'var(--gray-100)', padding: '2px 8px', borderRadius: '8px', color: 'var(--text-muted)'}}>عمق: {job.max_depth ?? 0}</span>
                      {job.js_render && <span style={{fontSize: '10.5px', background: 'rgba(196, 137, 74, 0.15)', padding: '2px 8px', borderRadius: '8px', color: 'var(--copper-dark)'}}>JS Render</span>}
                      {job.follow_external_domains && <span style={{fontSize: '10.5px', background: 'rgba(13, 71, 161, 0.1)', padding: '2px 8px', borderRadius: '8px', color: 'var(--navy)'}}>دامنه خارجی</span>}
                      {job.label && <span style={{fontSize: '10.5px', background: 'var(--gray-100)', padding: '2px 8px', borderRadius: '8px', color: 'var(--text-muted)', fontFamily: 'monospace', direction: 'ltr'}}>{job.label}</span>}
                    </div>

                    {job.error_message && (
                      <div style={{marginTop: '8px', fontSize: '11.5px', color: '#c62828', background: '#ffebee', padding: '6px 10px', borderRadius: '4px'}}>
                        ⚠️ {job.error_message}
                      </div>
                    )}
                  </div>
                );
              })}

            {crawlJobs.filter(j => !crawlStatusFilter || j.status === crawlStatusFilter).length === 0 && (
              <div style={{textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', fontSize: '13px'}}>
                🕷️ هیچ job کرالی یافت نشد. یک URL را کرال کنید تا اینجا نمایش داده شود.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
