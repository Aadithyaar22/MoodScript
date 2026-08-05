import { useState, useEffect, useRef } from "react"
import { login, signup, googleLogin } from "../api"
import { t } from "../i18n"

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function Login({ onAuth, lang = "en" }) {
  const [mode, setMode] = useState("login") // "login" | "signup"
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const googleBtnRef = useRef(null)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !window.google || !googleBtnRef.current) return

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        setError(null)
        setLoading(true)
        try {
          await googleLogin(response.credential)
          onAuth()
        } catch (e) {
          setError(e.response?.data?.detail || e.message || "Google sign-in failed")
        } finally {
          setLoading(false)
        }
      },
    })
    window.google.accounts.id.renderButton(googleBtnRef.current, {
      theme: "filled_black", size: "large", width: 316, text: "continue_with",
    })
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!username.trim() || !password) {
      setError(lang === "hi" ? "कृपया उपयोगकर्ता नाम और पासवर्ड दर्ज करें" : lang === "kn" ? "ದಯವಿಟ್ಟು ಬಳಕೆದಾರಹೆಸರು ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ" : "Please enter a username and password")
      return
    }
    setLoading(true)
    try {
      const fn = mode === "login" ? login : signup
      await fn(username.trim(), password)
      onAuth()
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', zIndex: 10, padding: 20,
    }}>
      <form onSubmit={handleSubmit} className="glass animate-fade-up" style={{
        width: '100%', maxWidth: 380, borderRadius: 20, padding: '36px 32px',
        display: 'flex', flexDirection: 'column', gap: 18,
      }}>
        <div style={{ textAlign: 'center', marginBottom: 6 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12, margin: '0 auto 14px',
            background: 'linear-gradient(135deg, #8b6fd4 0%, #3dd9c8 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, fontWeight: 700, color: '#fff', fontFamily: 'DM Mono, monospace',
            boxShadow: '0 0 24px rgba(139,111,212,0.5)',
          }}>M</div>
          <h1 className="serif" style={{ fontSize: 26, fontWeight: 300, color: '#f0ece6' }}>
            {mode === "login" ? t(lang, "welcomeBack") : t(lang, "createYourSpace")}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6, fontWeight: 300 }}>
            {mode === "login" ? t(lang, "signInSubtitle") : t(lang, "signUpSubtitle")}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>{t(lang, "username")}</label>
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            autoComplete="username"
            style={{
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '11px 14px', color: '#f0ece6', fontSize: 14,
              fontFamily: 'DM Sans, sans-serif', outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>{t(lang, "password")}</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            style={{
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '11px 14px', color: '#f0ece6', fontSize: 14,
              fontFamily: 'DM Sans, sans-serif', outline: 'none',
            }}
          />
        </div>

        {error && (
          <div style={{
            background: 'rgba(205,78,78,0.1)', border: '1px solid rgba(205,78,78,0.3)',
            borderRadius: 10, padding: '10px 14px', fontSize: 13, color: '#f4a0a0',
          }}>{error}</div>
        )}

        <button type="submit" disabled={loading} style={{
          padding: '12px', borderRadius: 12, border: 'none', cursor: loading ? 'default' : 'pointer',
          background: 'linear-gradient(135deg, #8b6fd4, #3dd9c8)', color: '#0a0d16',
          fontSize: 14, fontWeight: 600, opacity: loading ? 0.6 : 1,
        }}>
          {loading ? t(lang, "pleaseWait") : mode === "login" ? t(lang, "logIn") : t(lang, "signUp")}
        </button>

        {GOOGLE_CLIENT_ID && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
              <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>{t(lang, "or")}</span>
              <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
            </div>
            <div ref={googleBtnRef} style={{ display: 'flex', justifyContent: 'center' }} />
          </>
        )}

        <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
          {mode === "login" ? `${t(lang, "newHere")} ` : `${t(lang, "alreadyHaveAccount")} `}
          <button type="button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null) }} style={{
            background: 'none', border: 'none', color: 'var(--violet-bright)', cursor: 'pointer',
            fontSize: 13, textDecoration: 'underline', padding: 0,
          }}>
            {mode === "login" ? t(lang, "signUp") : t(lang, "logIn")}
          </button>
        </p>
      </form>
    </div>
  )
}
