export default function PageHeader({ title, desc, actions, icon }) {
  return (
    <div className="ax-page-header">
      <div>
        <div className="ax-page-header__title">
          {icon}
          {title}
        </div>
        {desc && <div className="ax-page-header__desc">{desc}</div>}
      </div>
      {actions && <div className="ax-page-header__actions">{actions}</div>}
    </div>
  );
}
