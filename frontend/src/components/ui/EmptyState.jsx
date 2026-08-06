import { Inbox } from 'lucide-react';

export default function EmptyState({ title = 'داده‌ای یافت نشد', desc, icon, action }) {
  return (
    <div className="ax-empty">
      {icon || <Inbox />}
      <div className="ax-empty__title">{title}</div>
      {desc && <div className="ax-empty__desc">{desc}</div>}
      {action}
    </div>
  );
}
