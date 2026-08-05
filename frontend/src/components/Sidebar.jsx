import { useEffect, useState } from "react"

const EMOTION_EMOJI  = { happy:"😊", sad:"😔", angry:"😠", fearful:"😨", surprised:"😲", disgusted:"😒", neutral:"😐" }
const EMOTION_COLOR  = { happy:"#e2b94b", sad:"#4d8de8", angry:"#e06b6b", fearful:"#b39dff", surprised:"#3dd9c8", disgusted:"#6bc8a0", neutral:"#6478a0" }

export default function Sidebar({ tab, setTab, history, conversations = [], activeConversationId, onSelectConversation, onNewConversation, onLogout, onExport, onDeleteAccount, onDeleteConversation }) {
  const [time, setTime] = useState(new Date())
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t) }, [])

  const username = localStorage.getItem("moodscript_username")
  const todayEntries = history.filter(h => new Date(h.timestamp).toDateString() === new Date().toDateString())
  const recentFive   = [...history].reverse().slice(0, 5)
  const emotionCounts = history.reduce((acc, h) => { acc[h.emotion] = (acc[h.emotion]||0)+1; return acc }, {})
  const topEmotion   = Object.entries(emotionCounts).sort((a,b)=>b[1]-a[1])[0]

  return (
    <aside style={{ padding: '28px 18px', display: 'flex', flexDirection: 'column', gap: 24, overflowY: 'auto', maxHeight: '100vh', background: 'rgba(255,255,255,0.01)' }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, #8b6fd4 0%, #3dd9c8 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 700, color: '#fff', fontFamily: 'DM Mono, monospace',
          boxShadow: '0 0 20px rgba(139,111,212,0.5)',
        }}>M</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p className="serif" style={{ fontSize: 18, fontWeight: 600, color: '#f0ece6', lineHeight: 1 }}>MoodScript</p>
          <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>EMOTION AI · v1.0</p>
        </div>
      </div>

      {/* User + logout */}
      {username && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            👤 {username}
          </p>
          <button onClick={onLogout} style={{
            fontSize: 10, color: 'var(--text-muted)', background: 'none',
            border: '1px solid var(--border)', borderRadius: 8, padding: '4px 10px',
            cursor: 'pointer', fontFamily: 'DM Mono, monospace', flexShrink: 0,
          }}>Log out</button>
        </div>
      )}

      {/* Account actions */}
      {username && (
        <div style={{ display: 'flex', gap: 14 }}>
          <button onClick={onExport} style={{
            fontSize: 10, color: 'var(--text-muted)', background: 'none', border: 'none',
            cursor: 'pointer', fontFamily: 'DM Mono, monospace', textDecoration: 'underline', padding: 0,
          }}>Export journal</button>
          <button onClick={onDeleteAccount} style={{
            fontSize: 10, color: '#e06b6b', background: 'none', border: 'none',
            cursor: 'pointer', fontFamily: 'DM Mono, monospace', textDecoration: 'underline', padding: 0,
          }}>Delete account</button>
        </div>
      )}

      {/* Clock */}
      <div style={{
        borderRadius: 14, padding: '16px',
        background: 'linear-gradient(135deg, rgba(139,111,212,0.15), rgba(61,217,200,0.08))',
        border: '1px solid rgba(139,111,212,0.3)',
      }}>
        <p className="mono" style={{ fontSize: 26, color: '#f0ece6', letterSpacing: '0.04em', lineHeight: 1 }}>
          {time.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' })}
        </p>
        <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6, letterSpacing: '0.08em' }}>
          {time.toLocaleDateString('en-IN', { weekday:'long', month:'short', day:'numeric' }).toUpperCase()}
        </p>
        {todayEntries.length > 0 && (
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(139,111,212,0.2)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: '#b39dff', fontFamily: 'DM Mono' }}>{todayEntries.length} entr{todayEntries.length === 1 ? 'y' : 'ies'} today</span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 4 }}>NAVIGATION</p>
        {[
          { id: 'analyze', label: 'Journal', icon: '✦', color: '#b39dff' },
          { id: 'dashboard', label: 'Dashboard', icon: '◎', color: '#3dd9c8' },
        ].map(item => (
          <button key={item.id} onClick={() => setTab(item.id)} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '11px 14px', borderRadius: 12, border: 'none', cursor: 'pointer',
            background: tab === item.id ? `${item.color}18` : 'transparent',
            borderLeft: `2px solid ${tab === item.id ? item.color : 'transparent'}`,
            color: tab === item.id ? item.color : 'var(--text-muted)',
            fontFamily: 'DM Sans, sans-serif', fontSize: 13, fontWeight: tab === item.id ? 500 : 300,
            transition: 'all 0.2s ease', textAlign: 'left',
            boxShadow: tab === item.id ? `0 0 20px ${item.color}20` : 'none',
          }}>
            <span className="mono" style={{ fontSize: 12 }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {/* Past conversations */}
      {conversations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.14em' }}>CONVERSATIONS</p>
            <button onClick={onNewConversation} style={{
              fontSize: 9, color: 'var(--violet-bright)', background: 'none', border: 'none',
              cursor: 'pointer', fontFamily: 'DM Mono, monospace',
            }}>+ new</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 180, overflowY: 'auto' }}>
            {conversations.map(c => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', gap: 4, borderRadius: 10,
                background: activeConversationId === c.id ? 'rgba(139,111,212,0.15)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${activeConversationId === c.id ? 'rgba(139,111,212,0.4)' : 'var(--border)'}`,
              }}>
                <button onClick={() => onSelectConversation(c.id)} style={{
                  flex: 1, minWidth: 0, textAlign: 'left', borderRadius: 10, padding: '8px 10px', cursor: 'pointer',
                  background: 'none', border: 'none',
                }}>
                  <p style={{
                    fontSize: 11, color: '#d8d4e8', overflow: 'hidden', textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap', fontWeight: 300,
                  }}>{c.opening_line || "New conversation"}</p>
                  <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                    {new Date(c.started_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} · {c.message_count} msgs
                  </p>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteConversation(c.id) }}
                  title="Delete conversation"
                  style={{
                    flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', fontSize: 13, padding: '0 10px', lineHeight: 1,
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
          <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 10 }}>RECENT</p>
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
                  <span style={{ fontSize: 16 }}>{EMOTION_EMOJI[h.emotion] || '😐'}</span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ fontSize: 12, color: '#f0ece6', textTransform: 'capitalize', fontWeight: 400 }}>{h.emotion}</p>
                    <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 1 }}>
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
          <p className="mono" style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 8 }}>DOMINANT EMOTION</p>
          <p style={{ fontSize: 22 }}>{EMOTION_EMOJI[topEmotion[0]]}
            <span className="serif" style={{ fontSize: 16, color: '#f0ece6', marginLeft: 8, fontStyle: 'italic', textTransform: 'capitalize' }}>{topEmotion[0]}</span>
          </p>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>{topEmotion[1]} of {history.length} entries</p>
        </div>
      )}
    </aside>
  )
}
