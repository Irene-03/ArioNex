import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

/* ── Toast ─────────────────────────────────────────────── */

const ToastContext = createContext(null);

const toastMeta = {
  success: { icon: CheckCircle2, variant: 'ax-toast--success' },
  error: { icon: AlertCircle, variant: 'ax-toast--error' },
  warning: { icon: AlertTriangle, variant: 'ax-toast--warning' },
  info: { icon: Info, variant: 'ax-toast--info' },
};

let toastId = 0;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts(prev => {
      const target = prev.find(t => t.id === id);
      if (target) {
        target.leaving = true;
      }
      return [...prev];
    });
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 250);
  }, []);

  const push = useCallback((type, title, desc, duration = 5000) => {
    const id = ++toastId;
    setToasts(prev => [...prev, { id, type, title, desc }]);
    if (duration > 0) {
      setTimeout(() => remove(id), duration);
    }
    return id;
  }, [remove]);

  const api = {
    success: (title, desc) => push('success', title, desc),
    error: (title, desc) => push('error', title, desc),
    warning: (title, desc) => push('warning', title, desc),
    info: (title, desc) => push('info', title, desc),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="ax-toast-viewport">
        {toasts.map(t => {
          const meta = toastMeta[t.type] || toastMeta.info;
          const Icon = meta.icon;
          return (
            <div key={t.id} className={`ax-toast ${meta.variant} ${t.leaving ? 'ax-toast--leaving' : ''}`} role="status" aria-live="polite">
              <Icon className="ax-toast__icon" />
              <div className="ax-toast__content">
                {t.title && <div className="ax-toast__title">{t.title}</div>}
                {t.desc && <div className="ax-toast__desc">{t.desc}</div>}
              </div>
              <button className="ax-toast__close" onClick={() => remove(t.id)} aria-label="بستن اعلان">
                <X />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
};

/* ── Confirm dialog ───────────────────────────────────── */

const ConfirmContext = createContext(null);

export const ConfirmProvider = ({ children }) => {
  const [state, setState] = useState(null);
  const resolverRef = useRef(null);

  const confirmDialog = useCallback((options) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setState(options);
    });
  }, []);

  const close = (result) => {
    setState(null);
    if (resolverRef.current) {
      resolverRef.current(result);
      resolverRef.current = null;
    }
  };

  const value = { confirmDialog };

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {state && (
        <div className="ax-modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) close(false); }}>
          <div className="ax-modal" style={{ maxWidth: 420 }} role="alertdialog" aria-modal="true" aria-label={state.title || 'تأیید عملیات'}>
            <div className="ax-modal__body" style={{ paddingTop: 24 }}>
              <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 10,
                    background: 'var(--color-danger-bg)',
                    color: 'var(--color-danger)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
                    {state.title || 'تأیید عملیات'}
                  </div>
                  {state.desc && (
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>{state.desc}</div>
                  )}
                </div>
              </div>
            </div>
            <div className="ax-modal__footer">
              <button className="ax-btn ax-btn--secondary" onClick={() => close(false)}>
                {state.cancelLabel || 'انصراف'}
              </button>
              <button className="ax-btn ax-btn--danger" onClick={() => close(true)}>
                {state.confirmLabel || 'تأیید'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useConfirm = () => {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error('useConfirm must be used within ConfirmProvider');
  return ctx.confirmDialog;
};
