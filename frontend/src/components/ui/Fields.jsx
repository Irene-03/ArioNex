export function Input({ label, hint, ltr = false, className = '', ...rest }) {
  return (
    <div className="ax-field">
      {label && <label className="ax-label">{label}</label>}
      <input className={`ax-input ${ltr ? 'ax-input--ltr' : ''} ${className}`} {...rest} />
      {hint && <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{hint}</span>}
    </div>
  );
}

export function Textarea({ label, ltr = false, className = '', ...rest }) {
  return (
    <div className="ax-field">
      {label && <label className="ax-label">{label}</label>}
      <textarea className={`ax-textarea ${ltr ? 'ax-textarea--ltr' : ''} ${className}`} {...rest} />
    </div>
  );
}

export function Select({ label, className = '', children, ...rest }) {
  return (
    <div className="ax-field">
      {label && <label className="ax-label">{label}</label>}
      <select className={`ax-select ${className}`} {...rest}>
        {children}
      </select>
    </div>
  );
}

export function Checkbox({ label, ...rest }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
      <input type="checkbox" {...rest} />
      {label}
    </label>
  );
}
