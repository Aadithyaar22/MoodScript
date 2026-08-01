import { useState, useRef } from "react"
import Webcam from "react-webcam"

export default function InputPanel({ onAnalyze, loading }) {
  const [text, setText] = useState("")
  const [imageBase64, setImageBase64] = useState(null)
  const [preview, setPreview] = useState(null)
  const [showWebcam, setShowWebcam] = useState(false)
  const webcamRef = useRef(null)
  const fileRef = useRef(null)

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
          <label className="mono" style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Journal entry
          </label>
          <span className="mono" style={{ fontSize: 11, color: wordCount > 20 ? 'var(--cyan)' : 'var(--text-muted)' }}>
            {wordCount} words
          </span>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write freely about how you feel today. The more you share, the deeper the analysis..."
          rows={6}
          style={{ width: '100%', borderRadius: 12, padding: '14px 16px', fontSize: 15, lineHeight: 1.8, fontFamily: 'DM Sans, sans-serif', fontWeight: 300 }}
        />
        {wordCount > 0 && wordCount < 20 && (
          <p style={{ fontSize: 12, color: 'var(--gold)', marginTop: 6, fontWeight: 300 }}>
            ↑ Longer entries produce richer emotional analysis
          </p>
        )}
      </div>

      <div>
        <label className="mono" style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block', marginBottom: 10 }}>
          Face image <span style={{ color: 'var(--text-muted)', fontWeight: 300 }}>— optional</span>
        </label>
        {preview ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src={preview} alt="preview" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--border)' }} />
            <div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Image captured</p>
              <button onClick={() => { setImageBase64(null); setPreview(null) }}
                style={{ fontSize: 12, color: '#f4a0a0', background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginTop: 2 }}>
                Remove
              </button>
            </div>
          </div>
        ) : showWebcam ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg"
              style={{ width: '100%', borderRadius: 12, border: '1px solid var(--border)' }}
              videoConstraints={{ width: 640, height: 360, facingMode: "user" }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={captureWebcam} style={btnPrimary}>Capture</button>
              <button onClick={() => setShowWebcam(false)} style={btnGhost}>Cancel</button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => fileRef.current.click()} style={btnGhost}>↑ Upload photo</button>
            <button onClick={() => setShowWebcam(true)} style={btnGhost}>⬤ Use webcam</button>
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
            : 'rgba(255,255,255,0.05)',
          border: '1px solid',
          borderColor: text.trim() && !loading ? 'transparent' : 'var(--border)',
          borderRadius: 12, fontSize: 14, fontWeight: 500,
          letterSpacing: '0.06em', textTransform: 'uppercase',
          color: text.trim() && !loading ? '#fff' : 'var(--text-muted)',
          cursor: text.trim() && !loading ? 'pointer' : 'not-allowed',
          transition: 'all 0.3s ease',
          fontFamily: 'DM Mono, monospace',
          boxShadow: text.trim() && !loading ? '0 0 32px rgba(123,94,167,0.4)' : 'none',
        }}
      >
        {loading ? '— analysing —' : 'Analyse Mood →'}
      </button>
    </div>
  )
}

const btnPrimary = {
  padding: '8px 20px', borderRadius: 8, fontSize: 13,
  background: 'rgba(123,94,167,0.3)', border: '1px solid rgba(123,94,167,0.5)',
  color: '#c4a8f0', cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
}
const btnGhost = {
  padding: '8px 18px', borderRadius: 8, fontSize: 13,
  background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
  color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
  transition: 'border-color 0.2s ease',
}
