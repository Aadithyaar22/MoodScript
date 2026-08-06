import { LANGUAGES } from "../i18n"

export default function LanguageSwitcher({ lang, onLangChange, style }) {
  return (
    <div style={{
      display: 'flex', gap: 4, padding: 4, borderRadius: 10,
      background: 'rgba(var(--surface-tint),0.03)', border: '1px solid var(--border)',
      ...style,
    }}>
      {LANGUAGES.map(l => (
        <button
          key={l.code}
          onClick={() => onLangChange(l.code)}
          style={{
            padding: '5px 10px', borderRadius: 7, border: 'none', cursor: 'pointer',
            background: lang === l.code ? 'rgba(139,111,212,0.3)' : 'transparent',
            color: lang === l.code ? 'var(--text-primary)' : 'var(--text-muted)',
            fontSize: 11, fontFamily: 'DM Sans, sans-serif',
            fontWeight: lang === l.code ? 500 : 300,
            transition: 'all 0.2s ease',
          }}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}
