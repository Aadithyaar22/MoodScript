import { useState, useEffect } from "react"
import InputPanel from "./components/InputPanel"
import ChatInput from "./components/ChatInput"
import ChatReply from "./components/ChatReply"
import XAIDrawer from "./components/XAIDrawer"
import Dashboard from "./components/Dashboard"
import Sidebar from "./components/Sidebar"
import RightPanel from "./components/RightPanel"
import Login from "./components/Login"
import LanguageSwitcher from "./components/LanguageSwitcher"
import ThemeSwitcher from "./components/ThemeSwitcher"
import { sendChatMessage, fetchHistory, fetchConversations, fetchConversationMessages, getToken, logout, exportJournal, deleteAccount, deleteConversation } from "./api"
import { t } from "./i18n"
import "./index.css"

export default function App() {
  const [authed, setAuthed] = useState(!!getToken())
  const [lang, setLang] = useState(() => localStorage.getItem("moodscript_lang") || "en")
  const [theme, setTheme] = useState(() => localStorage.getItem("moodscript_theme") || "dark")
  const [messages, setMessages] = useState([])   // [{id, role:'user'|'assistant', text, imageBase64?, analysis?}]
  const [conversationId, setConversationId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [tab, setTab]         = useState("analyze")
  const [history, setHistory] = useState([])
  const [conversations, setConversations] = useState([])
  const [xaiTargetId, setXaiTargetId] = useState(null)

  const lastAssistant = [...messages].reverse().find(m => m.role === "assistant")
  const xaiTarget = messages.find(m => m.id === xaiTargetId)

  const conversationMood = (() => {
    const scores = {}
    let total = 0
    messages.forEach(m => {
      const emotion = m.analysis?.unified_emotion
      const confidence = m.analysis?.unified_confidence
      if (!emotion || typeof confidence !== "number") return
      scores[emotion] = (scores[emotion] || 0) + confidence
      total += confidence
    })
    if (!total) return null
    const allScores = Object.fromEntries(Object.entries(scores).map(([e, s]) => [e, s / total]))
    const [dominantEmotion, dominantScore] = Object.entries(allScores).sort((a, b) => b[1] - a[1])[0]
    return {
      unified_emotion: dominantEmotion,
      unified_confidence: dominantScore,
      fusion_result: { all_scores: allScores },
    }
  })()

  useEffect(() => {
    if (!authed) return
    fetchHistory().then(d => setHistory([...d].reverse())).catch(() => {})
    fetchConversations().then(setConversations).catch(() => {})
  }, [authed, lastAssistant?.id])

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
  }, [theme])

  const handleLangChange = (newLang) => {
    setLang(newLang)
    localStorage.setItem("moodscript_lang", newLang)
  }

  const handleThemeChange = (newTheme) => {
    setTheme(newTheme)
    localStorage.setItem("moodscript_theme", newTheme)
  }

  const runChat = async (text, imageBase64) => {
    setLoading(true)
    setError(null)
    const userMsg = { id: crypto.randomUUID(), role: "user", text, imageBase64 }
    setMessages(m => [...m, userMsg])
    try {
      const data = await sendChatMessage(text, imageBase64, conversationId, lang)
      setConversationId(data.conversation_id)
      const assistantMsg = { id: crypto.randomUUID(), role: "assistant", text: data.response, analysis: data }
      setMessages(m => [...m, assistantMsg])
    } catch (e) {
      if (e.response?.status === 502) {
        setError(t(lang, "serviceWaking"))
      } else {
        setError(e.response?.data?.detail || e.message || t(lang, "analysisFailed"))
      }
      setMessages(m => m.filter(msg => msg.id !== userMsg.id))
    } finally {
      setLoading(false)
    }
  }

  const handleFirstMessage = (text, imageBase64) => runChat(text, imageBase64)

  const handleContinue = (text, imageBase64) => runChat(text, imageBase64)

  const handleNewConversation = () => {
    setMessages([])
    setConversationId(null)
    setError(null)
    setXaiTargetId(null)
  }

  const handleSelectConversation = async (id) => {
    setError(null)
    setXaiTargetId(null)
    try {
      const msgs = await fetchConversationMessages(id)
      let lastUserMsg = null
      setMessages(msgs.map(m => {
        if (m.role === "user") lastUserMsg = m
        return {
          id: `db-${m.id}`,
          role: m.role,
          text: m.content,
          analysis: m.role === "assistant" ? {
            unified_emotion: lastUserMsg?.emotion, unified_confidence: lastUserMsg?.confidence,
            response: m.content, text_result: {}, face_result: null, fusion_result: {},
          } : undefined,
        }
      }))
      setConversationId(id)
      setTab("analyze")
    } catch (e) {
      setError("Couldn't load that conversation")
    }
  }

  const handleLogout = () => {
    logout()
    setAuthed(false)
    setMessages([])
    setConversationId(null)
    setHistory([])
    setConversations([])
  }

  const handleDeleteConversation = async (id) => {
    if (!window.confirm("Delete this conversation? This can't be undone.")) return
    try {
      await deleteConversation(id)
      setConversations(cs => cs.filter(c => c.id !== id))
      if (conversationId === id) handleNewConversation()
    } catch {
      setError("Couldn't delete that conversation — try again")
    }
  }

  const handleExport = async () => {
    try {
      await exportJournal()
    } catch {
      setError("Couldn't export your journal — try again")
    }
  }

  const handleDeleteAccount = async () => {
    if (!window.confirm("Delete your account and everything in it? This can't be undone.")) return
    try {
      await deleteAccount()
      handleLogout()
    } catch {
      setError("Couldn't delete your account — try again")
    }
  }

  const todayStr = new Date().toDateString()
  const hasEntryToday = history.some(h => new Date(h.timestamp).toDateString() === todayStr)
  const streakBeforeToday = (() => {
    const uniqueDays = [...new Set(history.map(h => new Date(h.timestamp).toDateString()))]
      .sort((a, b) => new Date(b) - new Date(a))
    let count = 0
    for (let i = 0; i < uniqueDays.length; i++) {
      const expected = new Date()
      expected.setDate(expected.getDate() - (i + 1))
      if (uniqueDays[i] === expected.toDateString()) count++
      else break
    }
    return count
  })()

  if (!authed) {
    return (
      <>
        <div className="bg-canvas">
          <div className="orb orb-1"/>
          <div className="orb orb-2"/>
          <div className="orb orb-3"/>
          <div className="orb orb-4"/>
        </div>
        <div className="grid-pattern"/>
        <div style={{ position:'fixed', top:20, right:20, zIndex:20, display:'flex', gap:8 }}>
          <LanguageSwitcher lang={lang} onLangChange={handleLangChange}/>
          <ThemeSwitcher theme={theme} onThemeChange={handleThemeChange}/>
        </div>
        <Login onAuth={() => setAuthed(true)} lang={lang} theme={theme}/>
      </>
    )
  }

  return (
    <>
      <div className="bg-canvas">
        <div className="orb orb-1"/>
        <div className="orb orb-2"/>
        <div className="orb orb-3"/>
        <div className="orb orb-4"/>
      </div>
      <div className="grid-pattern"/>

      {xaiTarget && (
        <XAIDrawer
          xai={xaiTarget.analysis.xai}
          textResult={xaiTarget.analysis.text_result}
          faceResult={xaiTarget.analysis.face_result}
          fusionResult={xaiTarget.analysis.fusion_result}
          onClose={() => setXaiTargetId(null)}
        />
      )}

      <div style={{
        position:'relative', zIndex:10,
        display:'grid', gridTemplateColumns:'240px 1fr 220px',
        minHeight:'100vh',
      }}>
        <Sidebar
          tab={tab} setTab={setTab} history={history}
          conversations={conversations}
          activeConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          onLogout={handleLogout}
          onExport={handleExport}
          onDeleteAccount={handleDeleteAccount}
          lang={lang}
          onLangChange={handleLangChange}
          theme={theme}
          onThemeChange={handleThemeChange}
        />

        <main style={{
          borderLeft:'1px solid rgba(var(--surface-tint),0.05)',
          borderRight:'1px solid rgba(var(--surface-tint),0.05)',
          padding:'40px 32px', overflowY:'auto', maxHeight:'100vh',
        }}>
          {tab === "analyze" ? (
            <div style={{ display:'flex', flexDirection:'column', gap:20, maxWidth:640, margin:'0 auto' }}>

              {messages.length === 0 && !loading && (
                <div className="animate-fade-up" style={{ marginBottom:8 }}>
                  <h1 className="serif" style={{ fontSize:42, fontWeight:300, lineHeight:1.2, color:'var(--text-primary)', marginBottom:10 }}>
                    {t(lang, "howAreYou")}<br/>
                    <em style={{ color:'var(--violet-bright)', fontStyle:'italic' }}>{t(lang, "feelingToday")}</em>
                  </h1>
                  <p style={{ fontSize:14, color:'var(--text-muted)', fontWeight:300, lineHeight:1.8 }}>
                    {t(lang, "introText")}
                  </p>
                </div>
              )}

              {messages.length === 0 && !loading && history.length > 0 && !hasEntryToday && (
                <div className="animate-fade-up glass" style={{
                  borderRadius: 14, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10,
                  border: '1px solid rgba(226,185,75,0.3)', background: 'rgba(226,185,75,0.06)',
                }}>
                  <span style={{ fontSize: 16 }}>🔥</span>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 300 }}>
                    {streakBeforeToday > 0
                      ? t(lang, "streakBanner", streakBeforeToday)
                      : t(lang, "noEntryToday")}
                  </p>
                </div>
              )}

              {messages.length > 0 && (
                <div style={{ display:'flex', justifyContent:'flex-end' }}>
                  <button onClick={handleNewConversation} style={{
                    fontSize:12, color:'var(--text-muted)', background:'none',
                    border:'1px solid var(--border)', borderRadius:8, padding:'6px 12px',
                    cursor:'pointer', fontFamily:'DM Mono, monospace',
                  }}>{t(lang, "newConversation")}</button>
                </div>
              )}

              {messages.map((m) => (
                <div key={m.id} className="animate-fade-up-delay-1">
                  {m.role === "user" ? (
                    <div style={{ display:'flex', justifyContent:'flex-end' }}>
                      <div style={{
                        maxWidth:'80%', background:'rgba(139,111,212,0.15)',
                        border:'1px solid rgba(139,111,212,0.3)', borderRadius:'16px 16px 4px 16px',
                        padding:'12px 16px', display:'flex', flexDirection:'column', gap:8,
                      }}>
                        {m.imageBase64 && (
                          <img src={m.imageBase64} alt="attached" style={{ width:64, height:64, objectFit:'cover', borderRadius:10 }}/>
                        )}
                        <p style={{ fontSize:14, color:'var(--text-primary)', lineHeight:1.6, fontWeight:300 }}>{m.text}</p>
                      </div>
                    </div>
                  ) : (
                    <ChatReply result={m.analysis} onShowXAI={() => setXaiTargetId(m.id)} lang={lang}/>
                  )}
                </div>
              ))}

              {messages.length === 0 && (
                <InputPanel onAnalyze={handleFirstMessage} loading={loading} lang={lang}/>
              )}

              {error && (
                <div style={{
                  background:'rgba(205,78,78,0.1)', border:'1px solid rgba(205,78,78,0.3)',
                  borderRadius:12, padding:'12px 16px', fontSize:13, color:'var(--danger-text)'
                }}>{error}</div>
              )}

              {loading && (
                <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
                  {[120,180,60].map((h,i) => (
                    <div key={i} className="glass shimmer" style={{ height:h, borderRadius:16 }}/>
                  ))}
                </div>
              )}

              {messages.length > 0 && (
                <ChatInput onSend={handleContinue} loading={loading} lang={lang}/>
              )}
            </div>
          ) : (
            <div className="animate-fade-up" style={{ maxWidth:640, margin:'0 auto' }}>
              <Dashboard lang={lang}/>
            </div>
          )}
        </main>

        <RightPanel result={conversationMood} loading={loading} history={history} lang={lang}/>
      </div>
    </>
  )
}
