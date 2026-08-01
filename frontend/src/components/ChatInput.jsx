import { useState } from "react"

export default function ChatInput({ onSend, loading }) {
  const [text, setText] = useState("")

  const submit = () => {
    if (!text.trim() || loading) return
    onSend(text)
    setText("")
  }

  return (
    <div className="glass" style={{ borderRadius: 16, padding: 10, display: 'flex', gap: 10, alignItems: 'flex-end' }}>
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
  )
}
