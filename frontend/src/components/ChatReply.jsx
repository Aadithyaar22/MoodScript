import { useState } from "react"
import { t } from "../i18n"
import { speak, stopSpeaking } from "../useSpeechRecognition"

const EMOTION_CONFIG = {
  happy:     { emoji: "◎", accent: "#e2b94b" },
  sad:       { emoji: "◉", accent: "#4d8de8" },
  angry:     { emoji: "◈", accent: "#e06b6b" },
  fearful:   { emoji: "◇", accent: "#b39dff" },
  surprised: { emoji: "◆", accent: "#3dd9c8" },
  disgusted: { emoji: "◐", accent: "#6bc8a0" },
  neutral:   { emoji: "○", accent: "#6478a0" },
}

export default function ChatReply({ result, onShowXAI, lang = "en" }) {
  const { unified_emotion, unified_confidence, response } = result
  const cfg = EMOTION_CONFIG[unified_emotion] || EMOTION_CONFIG.neutral
  const [speaking, setSpeaking] = useState(false)
  const [loadingSpeech, setLoadingSpeech] = useState(false)
  const speechSupported = typeof window !== "undefined" && !!window.speechSynthesis

  const toggleSpeak = async () => {
    if (speaking || loadingSpeech) {
      stopSpeaking()
      setSpeaking(false)
      setLoadingSpeech(false)
      return
    }
    setLoadingSpeech(true)
    await speak(response, lang, unified_emotion, () => setSpeaking(false))
    setLoadingSpeech(false)
    setSpeaking(true)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: '85%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ fontSize: 12, color: cfg.accent, letterSpacing: '0.06em' }}>
          {cfg.emoji} {t(lang, unified_emotion) || unified_emotion} · {(unified_confidence * 100).toFixed(0)}%
        </span>
        {onShowXAI && (
          <button onClick={onShowXAI} style={{
            fontSize: 11, color: 'var(--text-muted)', background: 'none', border: 'none',
            cursor: 'pointer', fontFamily: 'DM Mono, monospace', textDecoration: 'underline', padding: 0,
          }}>{t(lang, "why")}</button>
        )}
        {speechSupported && (
          <button onClick={toggleSpeak} title="Listen" disabled={loadingSpeech} style={{
            fontSize: 13, color: speaking ? 'var(--danger-text)' : 'var(--text-muted)', background: 'none', border: 'none',
            cursor: loadingSpeech ? 'default' : 'pointer', padding: 0, marginLeft: 2,
            opacity: loadingSpeech ? 0.5 : 1,
          }}>{loadingSpeech ? '…' : speaking ? '◼' : '🔊'}</button>
        )}
      </div>
      <p className="serif" style={{ fontSize: 18, fontWeight: 300, lineHeight: 1.8, color: 'var(--violet-soft-text)', fontStyle: 'italic' }}>
        {response}
      </p>
    </div>
  )
}
