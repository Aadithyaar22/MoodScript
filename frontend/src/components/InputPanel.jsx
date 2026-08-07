import { useState, useRef, useCallback } from "react"
import Webcam from "react-webcam"
import { t } from "../i18n"
import { useSpeechRecognition, formatElapsed } from "../useSpeechRecognition"

export default function InputPanel({ onAnalyze, loading, lang = "en" }) {
  const [text, setText] = useState("")
  const [imageBase64, setImageBase64] = useState(null)
  const [preview, setPreview] = useState(null)
  const [showWebcam, setShowWebcam] = useState(false)
  const webcamRef = useRef(null)
  const fileRef = useRef(null)

  const handleVoiceResult = useCallback((transcript) => {
    setText(prev => (prev ? prev.trim() + " " : "") + transcript)
  }, [])
  const { isListening, elapsedSeconds, toggle: toggleMic, supported: micSupported } = useSpeechRecognition(lang, handleVoiceResult)

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => { setImageBase64(ev.target.result); setPreview(ev.target.result); setShowWebcam(false) }
    reader.readAsDataURL(file)
  }

  const captureWebcam = () => {
    const s = webcamRef.current.getScreenshot()
    if (s) { setImageBase64(s); setPreview(s); setShowWebcam(false) }
  }

  const wordCount = text.trim().split(/\s+/).filter(Boolean).length

  return (
    <div className="glass" style={{ borderRadius: 20, padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
          <label className="mono" style={{ fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {t(lang, "journalEntry")}
          </label>
          <span className="mono" style={{ fontSize: 13, color: wordCount > 20 ? 'var(--cyan)' : 'var(--text-muted)' }}>
            {wordCount} {t(lang, "words")}
          </span>
        </div>
        <div style={{ position: 'relative' }}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t(lang, "journalPlaceholder")}
            rows={6}
            style={{ width: '100%', borderRadius: 12, padding: '14px 16px', paddingRight: micSupported ? 48 : 16, fontSize: 16, lineHeight: 1.8, fontFamily: 'DM Sans, sans-serif', fontWeight: 300 }}
          />
          {micSupported && (
            <button
              type="button"
              onClick={toggleMic}
              title="Voice input"
              style={{
                position: 'absolute', top: 12, right: 12, width: 32, height: 32, borderRadius: '50%',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: isListening ? 'rgba(224,107,107,0.3)' : 'rgba(139,111,212,0.2)',
                color: isListening ? 'var(--danger-text)' : 'var(--violet-text)', fontSize: 16,
                boxShadow: isListening ? '0 0 0 4px rgba(224,107,107,0.15)' : 'none',
                transition: 'all 0.2s ease',
              }}
            >🎙</button>
          )}
        </div>
        {isListening && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', marginTop: 8,
            borderRadius: 10, background: 'rgba(224,107,107,0.12)', border: '1px solid rgba(224,107,107,0.3)',
            width: 'fit-content',
          }}>
            <span className="rec-dot" />
            <span className="mono" style={{ fontSize: 13, color: 'var(--danger-text)', letterSpacing: '0.04em' }}>
              {t(lang, "recording")} · {formatElapsed(elapsedSeconds)}
            </span>
          </div>
        )}
        {wordCount > 0 && wordCount < 20 && (
          <p style={{ fontSize: 14, color: 'var(--gold)', marginTop: 6, fontWeight: 300 }}>
            {t(lang, "longerEntries")}
          </p>
        )}
      </div>

      <div>
        <label className="mono" style={{ fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block', marginBottom: 10 }}>
          {t(lang, "faceImage")} <span style={{ color: 'var(--text-muted)', fontWeight: 300 }}>— {t(lang, "optional")}</span>
        </label>
        {preview ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src={preview} alt="preview" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--border)' }} />
            <div>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{t(lang, "imageCaptured")}</p>
              <button onClick={() => { setImageBase64(null); setPreview(null) }}
                style={{ fontSize: 14, color: 'var(--danger-text)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginTop: 2 }}>
                {t(lang, "remove")}
              </button>
            </div>
          </div>
        ) : showWebcam ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg"
              style={{ width: '100%', borderRadius: 12, border: '1px solid var(--border)' }}
              videoConstraints={{ width: 640, height: 360, facingMode: "user" }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={captureWebcam} style={btnPrimary}>{t(lang, "capture")}</button>
              <button onClick={() => setShowWebcam(false)} style={btnGhost}>{t(lang, "cancel")}</button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => fileRef.current.click()} style={btnGhost}>↑ {t(lang, "uploadPhoto")}</button>
            <button onClick={() => setShowWebcam(true)} style={btnGhost}>⬤ {t(lang, "useWebcam")}</button>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFileUpload} />
          </div>
        )}
      </div>

      <button
        onClick={() => onAnalyze(text, imageBase64)}
        disabled={!text.trim() || loading}
        style={{
          width: '100%', padding: '14px 24px',
          background: text.trim() && !loading
            ? 'linear-gradient(135deg, #7b5ea7 0%, #4ecdc4 100%)'
            : 'rgba(var(--surface-tint),0.05)',
          border: '1px solid',
          borderColor: text.trim() && !loading ? 'transparent' : 'var(--border)',
          borderRadius: 12, fontSize: 15, fontWeight: 500,
          letterSpacing: '0.06em', textTransform: 'uppercase',
          color: text.trim() && !loading ? '#fff' : 'var(--text-muted)',
          cursor: text.trim() && !loading ? 'pointer' : 'not-allowed',
          transition: 'all 0.3s ease',
          fontFamily: 'DM Mono, monospace',
          boxShadow: text.trim() && !loading ? '0 0 32px rgba(123,94,167,0.4)' : 'none',
        }}
      >
        {loading ? `— ${t(lang, "analysing")} —` : `${t(lang, "analyseMood")} →`}
      </button>
    </div>
  )
}

const btnPrimary = {
  padding: '8px 20px', borderRadius: 8, fontSize: 14,
  background: 'rgba(123,94,167,0.3)', border: '1px solid rgba(123,94,167,0.5)',
  color: 'var(--violet-text)', cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
}
const btnGhost = {
  padding: '8px 18px', borderRadius: 8, fontSize: 14,
  background: 'rgba(var(--surface-tint),0.04)', border: '1px solid var(--border)',
  color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
  transition: 'border-color 0.2s ease',
}
