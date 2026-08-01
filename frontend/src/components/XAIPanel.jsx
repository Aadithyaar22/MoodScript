import { useEffect, useRef } from "react"

const EMOTION_COLORS = {
  happy: "#c9a84c", sad: "#4e78cd", angry: "#cd4e4e",
  fearful: "#9d7fd4", surprised: "#cd8c4e", disgusted: "#4eb496", neutral: "#6478a0",
}

function AnimatedBar({ emotion, score, maxScore, delay = 0 }) {
  const pct = maxScore > 0 ? (score / maxScore) * 100 : 0
  const barRef = useRef(null)

  useEffect(() => {
    const el = barRef.current
    if (!el) return
    el.style.width = '0%'
    const t = setTimeout(() => {
      el.style.transition = `width 0.9s ${delay}s cubic-bezier(0.22, 1, 0.36, 1)`
      el.style.width = `${pct}%`
    }, 50)
    return () => clearTimeout(t)
  }, [pct, delay])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', width: 72, textTransform: 'capitalize' }}>
        {emotion}
      </span>
      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div ref={barRef} style={{
          height: '100%', borderRadius: 2,
          background: EMOTION_COLORS[emotion] || '#6478a0',
          boxShadow: `0 0 8px ${EMOTION_COLORS[emotion] || '#6478a0'}60`,
          width: 0,
        }} />
      </div>
      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', width: 32, textAlign: 'right' }}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  )
}

export default function XAIPanel({ xai, textResult, faceResult, fusionResult }) {
  if (!xai) return null

  const textScores  = xai.text_confidence_array || {}
  const faceScores  = faceResult?.all_scores || {}
  const fusedScores = fusionResult?.all_scores || {}

  const maxText  = Math.max(...Object.values(textScores), 0.001)
  const maxFace  = Math.max(...Object.values(faceScores), 0.001)
  const maxFused = Math.max(...Object.values(fusedScores), 0.001)

  return (
    <div className="glass" style={{ borderRadius: 20, padding: 28, display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div>
          <h3 className="serif" style={{ fontSize: 22, fontWeight: 400, color: 'var(--text-primary)' }}>Explainability</h3>
          <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', marginTop: 2 }}>
            What drove the prediction
          </p>
        </div>
        {fusionResult?.modalities_used && (
          <div style={{ display: 'flex', gap: 6 }}>
            {fusionResult.modalities_used.map(m => (
              <span key={m} className="mono" style={{
                fontSize: 10, padding: '3px 10px', borderRadius: 20,
                background: 'rgba(78,205,196,0.1)', border: '1px solid rgba(78,205,196,0.3)',
                color: '#4ecdc4', letterSpacing: '0.08em', textTransform: 'uppercase'
              }}>{m}</span>
            ))}
          </div>
        )}
      </div>

      {/* Key sentence */}
      {xai.key_sentence && (
        <div style={{
          padding: '16px 20px', borderRadius: 12,
          background: 'rgba(123,94,167,0.08)', borderLeft: '2px solid rgba(123,94,167,0.6)',
        }}>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 8 }}>
            KEY SENTENCE
          </p>
          <p className="serif" style={{ fontSize: 16, fontStyle: 'italic', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            "{xai.key_sentence}"
          </p>
        </div>
      )}

      {/* Word drivers */}
      {xai.top_words?.length > 0 && (
        <div>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 12 }}>
            WORD ATTRIBUTION
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {xai.top_words.map((w, i) => (
              <span key={i} className="mono" style={{
                fontSize: 12, padding: '5px 14px', borderRadius: 8,
                background: w.direction === 'positive' ? 'rgba(123,94,167,0.15)' : 'rgba(205,78,78,0.1)',
                border: `1px solid ${w.direction === 'positive' ? 'rgba(123,94,167,0.4)' : 'rgba(205,78,78,0.3)'}`,
                color: w.direction === 'positive' ? '#c4a8f0' : '#f4a0a0',
                letterSpacing: '0.04em',
              }}>
                {w.word} {w.direction === 'positive' ? '↑' : '↓'}
              </span>
            ))}
          </div>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8, letterSpacing: '0.04em' }}>
            ↑ increases emotion signal · ↓ decreases emotion signal
          </p>
        </div>
      )}

      {/* Confidence bars */}
      <div style={{ display: 'grid', gridTemplateColumns: faceResult ? '1fr 1fr' : '1fr', gap: 28 }}>
        <div>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 14 }}>
            TEXT MODEL
            {fusionResult && <span style={{ color: 'var(--violet-bright)', marginLeft: 8 }}>{((fusionResult.text_weight||0.55)*100).toFixed(0)}%</span>}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {Object.entries(textScores).sort((a,b)=>b[1]-a[1]).map(([e,s],i) => (
              <AnimatedBar key={e} emotion={e} score={s} maxScore={maxText} delay={i * 0.05} />
            ))}
          </div>
        </div>

        {faceResult && (
          <div>
            <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 14 }}>
              FACE MODEL
              {fusionResult && <span style={{ color: 'var(--cyan)', marginLeft: 8 }}>{((fusionResult.face_weight||0.45)*100).toFixed(0)}%</span>}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(faceScores).sort((a,b)=>b[1]-a[1]).map(([e,s],i) => (
                <AnimatedBar key={e} emotion={e} score={s} maxScore={maxFace} delay={i * 0.05} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Fused */}
      <div style={{ paddingTop: 20, borderTop: '1px solid var(--border)' }}>
        <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 14 }}>
          FUSED OUTPUT
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Object.entries(fusedScores).sort((a,b)=>b[1]-a[1]).map(([e,s],i) => (
            <AnimatedBar key={e} emotion={e} score={s} maxScore={maxFused} delay={i * 0.06} />
          ))}
        </div>
      </div>
    </div>
  )
}
