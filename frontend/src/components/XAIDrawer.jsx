import { useState } from "react"

const EMOTION_COLORS = {
  happy:"#e2b94b", sad:"#4d8de8", angry:"#e06b6b",
  fearful:"#b39dff", surprised:"#3dd9c8", disgusted:"#6bc8a0", neutral:"#6478a0"
}
const EMOTION_EMOJI = {
  happy:"😊", sad:"😔", angry:"😠", fearful:"😨",
  surprised:"😲", disgusted:"😒", neutral:"😐"
}

function EmotionCard({ emotion, score, maxScore, words, isActive, onClick }) {
  const pct = maxScore > 0 ? (score / maxScore) * 100 : 0
  const color = EMOTION_COLORS[emotion] || "#6478a0"
  const isTop = score === maxScore

  return (
    <div onClick={onClick} style={{
      borderRadius: 14, padding: '14px 16px', cursor: 'pointer',
      background: isActive ? `${color}22` : 'rgba(var(--surface-tint),0.03)',
      border: `1px solid ${isActive ? color+'60' : isTop ? color+'35' : 'rgba(var(--surface-tint),0.07)'}`,
      transition: 'all 0.25s ease',
      boxShadow: isActive ? `0 0 24px ${color}25` : 'none',
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom: isActive ? 12 : 0 }}>
        <span style={{ fontSize:21 }}>{EMOTION_EMOJI[emotion] || '○'}</span>
        <div style={{ flex:1 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:6 }}>
            <span style={{ fontSize:14, color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)', textTransform:'capitalize', fontWeight: isTop ? 500 : 300 }}>
              {emotion}
              {isTop && <span className="mono" style={{ fontSize:11, color, marginLeft:8, letterSpacing:'0.08em' }}>TOP</span>}
            </span>
            <span className="mono" style={{ fontSize:14, color }}>{(score*100).toFixed(0)}%</span>
          </div>
          <div style={{ height:4, background:'rgba(var(--surface-tint),0.06)', borderRadius:2, overflow:'hidden' }}>
            <div style={{
              height:'100%', borderRadius:2, width:`${pct}%`,
              background:`linear-gradient(90deg, ${color}, ${color}bb)`,
              boxShadow:`0 0 8px ${color}60`,
              transition:'width 0.9s cubic-bezier(0.22,1,0.36,1)',
            }}/>
          </div>
        </div>
        <span style={{ fontSize:13, color:'var(--text-muted)', transform: isActive ? 'rotate(180deg)' : 'none', transition:'transform 0.2s' }}>▾</span>
      </div>

      {isActive && words && words.length > 0 && (
        <div className="animate-fade-up">
          <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:10 }}>
            WORDS DRIVING THIS EMOTION
          </p>
          <div style={{ display:'flex', flexWrap:'wrap', gap:7 }}>
            {words.map((w, i) => (
              <div key={i} style={{
                display:'flex', alignItems:'center', gap:5,
                padding:'5px 12px', borderRadius:20,
                background: w.direction === 'positive' ? `${color}20` : 'rgba(224,107,107,0.15)',
                border: `1px solid ${w.direction === 'positive' ? color+'45' : 'rgba(224,107,107,0.35)'}`,
              }}>
                <span style={{ fontSize:13, color: w.direction === 'positive' ? color : 'var(--danger-text)', fontFamily:'DM Mono', fontWeight:500 }}>
                  {w.word}
                </span>
                <span style={{ fontSize:11, color: w.direction === 'positive' ? color : 'var(--danger-text)', opacity:0.8 }}>
                  {w.direction === 'positive' ? '▲' : '▼'}
                </span>
              </div>
            ))}
          </div>
          <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', marginTop:10, lineHeight:1.6 }}>
            ▲ pushes toward {emotion} · ▼ works against it
          </p>
        </div>
      )}

      {isActive && (!words || words.length === 0) && (
        <p style={{ fontSize:14, color:'var(--text-muted)', fontStyle:'italic', marginTop:8 }}>
          No word-level data for this emotion.
        </p>
      )}
    </div>
  )
}

export default function XAIDrawer({ xai, textResult, faceResult, fusionResult, onClose }) {
  const [activeEmotion, setActiveEmotion] = useState(null)

  const textScores  = xai?.text_confidence_array || {}
  const faceScores  = faceResult?.all_scores || {}
  const fusedScores = fusionResult?.all_scores || {}

  const maxText  = Math.max(...Object.values(textScores), 0.001)
  const maxFace  = Math.max(...Object.values(faceScores), 0.001)
  const maxFused = Math.max(...Object.values(fusedScores), 0.001)

  const topWords = xai?.top_words || []

  const getWordsForEmotion = (emotion) => {
    const dominant = textResult?.dominant_emotion
    if (emotion === dominant) return topWords
    return []
  }

  const RESOLUTION_TEXT = {
    agreement: "Both face and text modalities agreed on this emotion.",
    text_only: "This analysis is based on text only — no face image was provided.",
    text_override: "The face appeared neutral, so the text signal was prioritised.",
    face_override: "The text appeared neutral, so the face signal was prioritised.",
    dominant_confidence_text: "The text model was significantly more confident.",
    dominant_confidence_face: "The face model was significantly more confident.",
  }

  const resolution = Object.entries(RESOLUTION_TEXT).find(
    ([k]) => fusionResult?.resolution_reason?.startsWith(k)
  )?.[1] || fusionResult?.resolution_reason

  return (
    <div style={{
      position:'fixed', inset:0, zIndex:50,
      display:'flex', justifyContent:'flex-end',
    }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{
        position:'absolute', inset:0,
        background:'rgba(7,9,15,0.7)', backdropFilter:'blur(4px)',
      }}/>

      {/* Drawer */}
      <div className="animate-fade-up" style={{
        position:'relative', width:480, maxWidth:'95vw',
        background:'var(--bg)',
        borderLeft:'1px solid rgba(var(--surface-tint),0.08)',
        overflowY:'auto', maxHeight:'100vh',
        padding:28, display:'flex', flexDirection:'column', gap:24,
      }}>

        {/* Header */}
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between' }}>
          <div>
            <h2 className="serif" style={{ fontSize:28, fontWeight:400, color:'var(--text-primary)' }}>Explainability</h2>
            <p className="mono" style={{ fontSize:12, color:'var(--text-muted)', letterSpacing:'0.08em', marginTop:4 }}>
              WHAT DROVE THE PREDICTION
            </p>
          </div>
          <button onClick={onClose} style={{
            background:'rgba(var(--surface-tint),0.06)', border:'1px solid rgba(var(--surface-tint),0.1)',
            borderRadius:8, width:32, height:32, cursor:'pointer',
            color:'var(--text-muted)', fontSize:17, display:'flex',
            alignItems:'center', justifyContent:'center',
          }}>×</button>
        </div>

        {/* Key sentence */}
        {xai?.key_sentence && (
          <div style={{
            padding:'16px 18px', borderRadius:14,
            background:'rgba(139,111,212,0.08)',
            borderLeft:'2px solid rgba(139,111,212,0.7)',
          }}>
            <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:10 }}>
              HIGHEST EMOTION SENTENCE
            </p>
            <p className="serif" style={{ fontSize:18, fontStyle:'italic', color:'var(--violet-soft-text)', lineHeight:1.75 }}>
              "{xai.key_sentence}"
            </p>
          </div>
        )}

        {/* Resolution note */}
        {resolution && (
          <div style={{
            padding:'12px 16px', borderRadius:12,
            background:'rgba(61,217,200,0.08)', border:'1px solid rgba(61,217,200,0.2)',
            display:'flex', gap:10, alignItems:'flex-start',
          }}>
            <span style={{ fontSize:15, flexShrink:0 }}>⚡</span>
            <p style={{ fontSize:14, color:'var(--cyan)', lineHeight:1.6 }}>{resolution}</p>
          </div>
        )}

        {/* Fusion weights */}
        {fusionResult?.modalities_used?.length > 1 && (
          <div>
            <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:12 }}>
              FUSION WEIGHTS
            </p>
            <div style={{ display:'flex', gap:10 }}>
              {[
                { label:'Text', weight: fusionResult.text_weight, color:'var(--violet-bright)' },
                { label:'Face', weight: fusionResult.face_weight, color:'var(--cyan)' },
              ].map(m => (
                <div key={m.label} style={{
                  flex:1, padding:'12px', borderRadius:12,
                  background:`${m.color}12`, border:`1px solid ${m.color}35`,
                  textAlign:'center',
                }}>
                  <p className="serif" style={{ fontSize:24, fontWeight:700, color:m.color }}>{(m.weight*100).toFixed(0)}%</p>
                  <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', marginTop:4, letterSpacing:'0.08em' }}>{m.label.toUpperCase()} MODEL</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Text model emotion cards */}
        <div>
          <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:12 }}>
            TEXT MODEL · click an emotion to see what drove it
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {Object.entries(textScores).sort((a,b)=>b[1]-a[1]).map(([emotion, score]) => (
              <EmotionCard
                key={emotion}
                emotion={emotion}
                score={score}
                maxScore={maxText}
                words={getWordsForEmotion(emotion)}
                isActive={activeEmotion === `text_${emotion}`}
                onClick={() => setActiveEmotion(activeEmotion === `text_${emotion}` ? null : `text_${emotion}`)}
              />
            ))}
          </div>
        </div>

        {/* Face model cards */}
        {faceResult && Object.keys(faceScores).length > 0 && (
          <div>
            <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:12 }}>
              FACE MODEL
            </p>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {Object.entries(faceScores).sort((a,b)=>b[1]-a[1]).map(([emotion, score]) => (
                <EmotionCard
                  key={emotion}
                  emotion={emotion}
                  score={score}
                  maxScore={maxFace}
                  words={[]}
                  isActive={activeEmotion === `face_${emotion}`}
                  onClick={() => setActiveEmotion(activeEmotion === `face_${emotion}` ? null : `face_${emotion}`)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Fused output */}
        <div>
          <p className="mono" style={{ fontSize:11, color:'var(--text-muted)', letterSpacing:'0.1em', marginBottom:12 }}>
            FUSED OUTPUT
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {Object.entries(fusedScores).sort((a,b)=>b[1]-a[1]).map(([emotion, score]) => (
              <EmotionCard
                key={emotion}
                emotion={emotion}
                score={score}
                maxScore={maxFused}
                words={getWordsForEmotion(emotion)}
                isActive={activeEmotion === `fused_${emotion}`}
                onClick={() => setActiveEmotion(activeEmotion === `fused_${emotion}` ? null : `fused_${emotion}`)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
