const variantMap = {
  success: 'ax-badge--success',
  warning: 'ax-badge--warning',
  danger: 'ax-badge--danger',
  info: 'ax-badge--info',
  neutral: 'ax-badge--neutral',
  copper: 'ax-badge--copper',
};

export default function Badge({ variant = 'neutral', icon, className = '', children, ...rest }) {
  return (
    <span className={`ax-badge ${variantMap[variant] || variantMap.neutral} ${className}`} {...rest}>
      {icon}
      {children}
    </span>
  );
}
