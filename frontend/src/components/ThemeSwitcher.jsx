export default function ThemeSwitcher({ theme, onThemeChange, style }) {
  const isLight = theme === "light"
  return (
    <button
      onClick={() => onThemeChange(isLight ? "dark" : "light")}
      title={isLight ? "Switch to dark theme" : "Switch to light theme"}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: 34, height: 34, borderRadius: 10, flexShrink: 0,
        background: 'rgba(var(--surface-tint),0.03)', border: '1px solid var(--border)',
        color: 'var(--text-primary)', cursor: 'pointer', fontSize: 15,
        transition: 'all 0.2s ease',
        ...style,
      }}
    >
      {isLight ? '☀' : '☾'}
    </button>
  )
}
