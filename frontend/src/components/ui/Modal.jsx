import { X } from 'lucide-react';

export default function Modal({ open, title, onClose, children, footer, maxWidth = 460 }) {
  if (!open) return null;

  return (
    <div className="ax-modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ax-modal" style={{ maxWidth }} role="dialog" aria-modal="true" aria-label={title}>
        <div className="ax-modal__header">
          <div className="ax-modal__title">{title}</div>
          <button className="icon-btn" onClick={onClose} aria-label="بستن">
            <X size={18} />
          </button>
        </div>
        <div className="ax-modal__body">{children}</div>
        {footer && <div className="ax-modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
