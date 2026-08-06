export default function Switch({ checked, onChange, disabled = false, 'aria-label': ariaLabel }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={!!checked}
      aria-label={ariaLabel}
      className={`ax-switch ${checked ? 'ax-switch--on' : 'ax-switch--off'}`}
      onClick={onChange}
      disabled={disabled}
      style={disabled ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
    />
  );
}
