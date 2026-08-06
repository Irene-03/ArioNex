export default function Card({ title, desc, actions, className = '', children, ...rest }) {
  return (
    <div className={`ax-card ${className}`} {...rest}>
      {(title || actions) && (
        <div className="ax-card__header">
          <div>
            {title && <div className="ax-card__title">{title}</div>}
            {desc && <div className="ax-card__desc">{desc}</div>}
          </div>
          {actions && <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
