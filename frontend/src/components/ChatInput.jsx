import { useState, useRef } from "react"
import Webcam from "react-webcam"

export default function ChatInput({ onSend, loading }) {
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

  const submit = () => {
    if (!text.trim() || loading) return
    onSend(text, imageBase64)
    setText("")
    setImageBase64(null)
    setPreview(null)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {showWebcam && (
        <div className="glass" style={{ borderRadius: 16, padding: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Webcam ref={webcamRef} screenshotFormat="image/jpeg"
            style={{ width: '100%', borderRadius: 12, border: '1px solid var(--border)' }}
            videoConstraints={{ width: 640, height: 360, facingMode: "user" }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={captureWebcam} style={btnPrimary}>Capture</button>
            <button onClick={() => setShowWebcam(false)} style={btnGhost}>Cancel</button>
          </div>
        </div>
      )}

      {preview && (
        <div className="glass" style={{ borderRadius: 14, padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src={preview} alt="attached" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }} />
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>Image attached</p>
          <button onClick={() => { setImageBase64(null); setPreview(null) }}
            style={{ fontSize: 12, color: '#f4a0a0', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            Remove
          </button>
        </div>
      )}

      <div className="glass" style={{ borderRadius: 16, padding: 10, display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <button
          onClick={() => fileRef.current.click()}
          title="Attach a photo"
          style={iconBtn}
        >↑</button>
        <button
          onClick={() => setShowWebcam(s => !s)}
          title="Use webcam"
          style={iconBtn}
        >⬤</button>
        <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFileUpload} />

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder="Reply to Aria..."
          rows={1}
          style={{
            flex: 1, resize: 'none', borderRadius: 12, padding: '12px 14px',
            fontSize: 14, lineHeight: 1.6, fontFamily: 'DM Sans, sans-serif', fontWeight: 300,
            maxHeight: 140, background: 'rgba(255,255,255,0.03)',
          }}
        />
        <button
          onClick={submit}
          disabled={!text.trim() || loading}
          style={{
            padding: '12px 20px', borderRadius: 12,
            background: text.trim() && !loading
              ? 'linear-gradient(135deg, #7b5ea7 0%, #4ecdc4 100%)'
              : 'rgba(255,255,255,0.05)',
            border: '1px solid',
            borderColor: text.trim() && !loading ? 'transparent' : 'var(--border)',
            fontSize: 13, fontWeight: 500, letterSpacing: '0.04em',
            color: text.trim() && !loading ? '#fff' : 'var(--text-muted)',
            cursor: text.trim() && !loading ? 'pointer' : 'not-allowed',
            fontFamily: 'DM Mono, monospace', whiteSpace: 'nowrap',
            transition: 'all 0.2s ease',
          }}
        >
          {loading ? '···' : 'Send →'}
        </button>
      </div>
    </div>
  )
}

const iconBtn = {
  width: 40, height: 44, borderRadius: 12, flexShrink: 0,
  background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
  color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 14,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
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
