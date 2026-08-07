// Small inline banner for errors / info / empty states.
export default function Callout({ tone = 'info', title, children }) {
  const icon = tone === 'error' ? '⚠' : tone === 'success' ? '✓' : 'ℹ'
  return (
    <div className={`callout callout-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <span className="callout-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="callout-body">
        {title && <strong className="callout-title">{title}</strong>}
        {children && <div className="callout-text">{children}</div>}
      </div>
    </div>
  )
}
