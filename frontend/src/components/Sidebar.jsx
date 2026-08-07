import { useEffect, useRef, useState } from "react"
import { t } from "../i18n"
import LanguageSwitcher from "./LanguageSwitcher"
import ThemeSwitcher from "./ThemeSwitcher"

const EMOTION_EMOJI  = { happy:"😊", sad:"😔", angry:"😠", fearful:"😨", surprised:"😲", disgusted:"😒", neutral:"😐" }
const EMOTION_COLOR  = { happy:"#e2b94b", sad:"#4d8de8", angry:"#e06b6b", fearful:"#b39dff", surprised:"#3dd9c8", disgusted:"#6bc8a0", neutral:"#6478a0" }

export default function Sidebar({ tab, setTab, history, conversations = [], activeConversationId, onSelectConversation, onNewConversation, onLogout, onExportFormat, onDeleteAccount, onDeleteConversation, lang, onLangChange, theme, onThemeChange }) {
  const [time, setTime] = useState(new Date())
  const [exportFormat, setExportFormat] = useState("")
  const [exportStatus, setExportStatus] = useState(null) // { label, state: 'loading' | 'success' }
  const exportTimeoutRef = useRef(null)
  useEffect(() => { const timer = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(timer) }, [])
  useEffect(() => () => clearTimeout(exportTimeoutRef.current), [])

  const FORMAT_LABEL_KEY = { "journal-txt": "journalTxtOption", "report-txt": "reportTxtOption", "report-pdf": "reportPdfOption" }

  const handleExportChange = async (e) => {
    const format = e.target.value
    if (!format) return
    const label = t(lang, FORMAT_LABEL_KEY[format])
    setExportFormat("")
    clearTimeout(exportTimeoutRef.current)
    setExportStatus({ label, state: "loading" })
    const success = await onExportFormat(format)
    if (success) {
      setExportStatus({ label, state: "success" })
      exportTimeoutRef.current = setTimeout(() => setExportStatus(null), 4000)
    } else {
      setExportStatus(null)
    }
  }

  const username = localStorage.getItem("moodscript_username")
  const todayEntries = history.filter(h => new Date(h.timestamp).toDateString() === new Date().toDateString())
  const recentFive   = [...history].reverse().slice(0, 5)
  const emotionCounts = history.reduce((acc, h) => { acc[h.emotion] = (acc[h.emotion]||0)+1; return acc }, {})
  const topEmotion   = Object.entries(emotionCounts).sort((a,b)=>b[1]-a[1])[0]

  return (
    <aside className="app-sidebar" style={{ padding: '28px 18px', display: 'flex', flexDirection: 'column', gap: 24, overflowY: 'auto', maxHeight: '100vh', background: 'rgba(var(--surface-tint),0.01)' }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, #8b6fd4 0%, #3dd9c8 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 17, fontWeight: 700, color: '#fff', fontFamily: 'DM Mono, monospace',
          boxShadow: '0 0 20px rgba(139,111,212,0.5)',
        }}>M</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p className="serif" style={{ fontSize: 19, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1 }}>{t(lang, "appName")}</p>
          <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>{t(lang, "tagline")}</p>
        </div>
      </div>

      {/* Language + theme switcher */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <LanguageSwitcher lang={lang} onLangChange={onLangChange} style={{ flex: 1 }}/>
        <ThemeSwitcher theme={theme} onThemeChange={onThemeChange}/>
      </div>

      {/* User + logout */}
      {username && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <p title={username} style={{
            fontSize: 13, color: 'var(--text-secondary)', minWidth: 0, flex: 1,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            👤 {username}
          </p>
          <button onClick={onLogout} style={{
            fontSize: 11, color: 'var(--text-secondary)', background: 'none',
            border: '1px solid var(--border)', borderRadius: 8, padding: '4px 9px',
            cursor: 'pointer', fontFamily: 'DM Mono, monospace', flexShrink: 0,
          }}>{t(lang, "logOut")}</button>
        </div>
      )}

      {/* Export */}
      {username && (
        <div>
          <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 8 }}>
            {t(lang, "export")}
          </p>
          <select
            value={exportFormat}
            onChange={handleExportChange}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 10,
              background: 'rgba(var(--surface-tint),0.03)', border: '1px solid var(--border)',
              color: exportFormat ? 'var(--text-primary)' : 'var(--text-muted)',
              fontSize: 14, fontFamily: 'DM Sans, sans-serif', cursor: 'pointer', outline: 'none',
            }}
          >
            <option value="" disabled>{t(lang, "chooseFormat")}</option>
            <option value="journal-txt">{t(lang, "journalTxtOption")}</option>
            <option value="report-txt">{t(lang, "reportTxtOption")}</option>
            <option value="report-pdf">{t(lang, "reportPdfOption")}</option>
          </select>
          {exportStatus && (
            <p className="mono animate-fade-up" style={{
              fontSize: 12, marginTop: 7, display: 'flex', alignItems: 'center', gap: 6,
              color: exportStatus.state === "success" ? 'var(--cyan)' : 'var(--text-muted)',
            }}>
              {exportStatus.state === "loading"
                ? <>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                      border: '1.5px solid var(--text-muted)', borderTopColor: 'transparent',
                      animation: 'spin 0.7s linear infinite',
                    }} />
                    {t(lang, "exporting")} {exportStatus.label}…
                  </>
                : <>✓ {exportStatus.label} {t(lang, "exportedSuccessfully")}</>
              }
            </p>
          )}
        </div>
      )}

      {/* Delete account */}
      {username && (
        <button onClick={onDeleteAccount} style={{
          fontSize: 12, color: 'var(--danger-text)', background: 'none', border: 'none',
          cursor: 'pointer', fontFamily: 'DM Mono, monospace', textDecoration: 'underline',
          padding: 0, textAlign: 'left', width: 'fit-content',
        }}>{t(lang, "deleteAccount")}</button>
      )}

      {/* Clock */}
      <div style={{
        borderRadius: 14, padding: '16px',
        background: 'linear-gradient(135deg, rgba(139,111,212,0.15), rgba(61,217,200,0.08))',
        border: '1px solid rgba(139,111,212,0.3)',
      }}>
        <p className="mono" style={{ fontSize: 26, color: 'var(--text-primary)', letterSpacing: '0.04em', lineHeight: 1 }}>
          {time.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' })}
        </p>
        <p className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6, letterSpacing: '0.08em' }}>
          {time.toLocaleDateString('en-IN', { weekday:'long', month:'short', day:'numeric' }).toUpperCase()}
        </p>
        {todayEntries.length > 0 && (
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(139,111,212,0.2)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13, color: 'var(--violet-bright)', fontFamily: 'DM Mono' }}>{todayEntries.length} {t(lang, todayEntries.length === 1 ? "entryToday" : "entriesToday")}</span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 4 }}>{t(lang, "navigation")}</p>
        {[
          { id: 'analyze', label: t(lang, "journal"), icon: '✦', color: 'var(--violet-bright)' },
          { id: 'dashboard', label: t(lang, "dashboard"), icon: '◎', color: 'var(--cyan)' },
        ].map(item => (
          <button key={item.id} onClick={() => setTab(item.id)} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '11px 14px', borderRadius: 12, border: 'none', cursor: 'pointer',
            background: tab === item.id ? `${item.color}18` : 'transparent',
            borderLeft: `2px solid ${tab === item.id ? item.color : 'transparent'}`,
            color: tab === item.id ? item.color : 'var(--text-muted)',
            fontFamily: 'DM Sans, sans-serif', fontSize: 14, fontWeight: tab === item.id ? 500 : 300,
            transition: 'all 0.2s ease', textAlign: 'left',
            boxShadow: tab === item.id ? `0 0 20px ${item.color}20` : 'none',
          }}>
            <span className="mono" style={{ fontSize: 14 }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {/* Past conversations */}
      {conversations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.14em' }}>{t(lang, "conversations")}</p>
            <button onClick={onNewConversation} style={{
              fontSize: 11, color: 'var(--violet-bright)', background: 'none', border: 'none',
              cursor: 'pointer', fontFamily: 'DM Mono, monospace',
            }}>{t(lang, "newLink")}</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 180, overflowY: 'auto' }}>
            {conversations.map(c => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', gap: 4, borderRadius: 10,
                background: activeConversationId === c.id ? 'rgba(139,111,212,0.15)' : 'rgba(var(--surface-tint),0.02)',
                border: `1px solid ${activeConversationId === c.id ? 'rgba(139,111,212,0.4)' : 'var(--border)'}`,
              }}>
                <button onClick={() => onSelectConversation(c.id)} style={{
                  flex: 1, minWidth: 0, textAlign: 'left', borderRadius: 10, padding: '8px 10px', cursor: 'pointer',
                  background: 'none', border: 'none',
                }}>
                  <p style={{
                    fontSize: 13, color: 'var(--violet-soft-text)', overflow: 'hidden', textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap', fontWeight: 300,
                  }}>{c.opening_line || t(lang, "newConversationLabel")}</p>
                  <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {new Date(c.started_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} · {c.message_count} msgs
                  </p>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteConversation(c.id) }}
                  title={t(lang, "deleteConversation")}
                  style={{
                    flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', fontSize: 14, padding: '0 10px', lineHeight: 1,
                  }}
                >×</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent entries */}
      {recentFive.length > 0 && (
        <div style={{ flex: 1 }}>
          <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 10 }}>{t(lang, "recent")}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {recentFive.map((h, i) => {
              const c = EMOTION_COLOR[h.emotion] || '#6478a0'
              return (
                <div key={h.id} style={{
                  borderRadius: 10, padding: '10px 12px',
                  background: `${c}10`,
                  border: `1px solid ${c}30`,
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                  <span style={{ fontSize: 17 }}>{EMOTION_EMOJI[h.emotion] || '😐'}</span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ fontSize: 14, color: 'var(--text-primary)', textTransform: 'capitalize', fontWeight: 400 }}>{t(lang, h.emotion)}</p>
                    <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
                      {new Date(h.timestamp).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' })}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Top emotion */}
      {topEmotion && (
        <div style={{
          borderRadius: 12, padding: '14px',
          background: `${EMOTION_COLOR[topEmotion[0]] || '#6478a0'}15`,
          border: `1px solid ${EMOTION_COLOR[topEmotion[0]] || '#6478a0'}40`,
        }}>
          <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 8 }}>{t(lang, "dominantEmotion")}</p>
          <p style={{ fontSize: 22 }}>{EMOTION_EMOJI[topEmotion[0]]}
            <span className="serif" style={{ fontSize: 17, color: 'var(--text-primary)', marginLeft: 8, fontStyle: 'italic', textTransform: 'capitalize' }}>{t(lang, topEmotion[0])}</span>
          </p>
          <p className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>{topEmotion[1]} {t(lang, "of")} {history.length} {t(lang, "entries")}</p>
        </div>
      )}
    </aside>
  )
}
