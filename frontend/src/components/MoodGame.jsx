import { useState, useEffect, useCallback } from "react"
import { t } from "../i18n"

const CARDS = ["😊","😔","😠","😨","😲","😒","🥰","😤"]
const ALL_CARDS = [...CARDS, ...CARDS]
  .map((v, i) => ({ id: i, emoji: v, flipped: false, matched: false }))

function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export default function MoodGame({ onClose, lang = "en" }) {
  const [cards, setCards] = useState(() => shuffle(ALL_CARDS))
  const [flipped, setFlipped] = useState([])
  const [matched, setMatched] = useState([])
  const [moves, setMoves] = useState(0)
  const [won, setWon] = useState(false)
  const [locked, setLocked] = useState(false)

  const reset = () => {
    setCards(shuffle(ALL_CARDS.map(c => ({ ...c, flipped: false, matched: false }))))
    setFlipped([])
    setMatched([])
    setMoves(0)
    setWon(false)
    setLocked(false)
  }

  const handleFlip = useCallback((card) => {
    if (locked || flipped.length === 2) return
    if (flipped.find(c => c.id === card.id)) return
    if (matched.includes(card.emoji)) return

    const newFlipped = [...flipped, card]
    setFlipped(newFlipped)

    if (newFlipped.length === 2) {
      setMoves(m => m + 1)
      setLocked(true)
      if (newFlipped[0].emoji === newFlipped[1].emoji) {
        const newMatched = [...matched, card.emoji]
        setMatched(newMatched)
        setFlipped([])
        setLocked(false)
        if (newMatched.length === CARDS.length) setWon(true)
      } else {
        setTimeout(() => { setFlipped([]); setLocked(false) }, 900)
      }
    }
  }, [flipped, matched, locked])

  const isFlipped = (card) => flipped.find(c => c.id === card.id) || matched.includes(card.emoji)

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(7,9,15,0.88)', backdropFilter: 'blur(16px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: 'var(--bg)', border: '1px solid rgba(var(--surface-tint),0.1)',
        borderRadius: 24, padding: 32, width: 360, maxWidth: '95vw',
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom: 20 }}>
          <div>
            <p className="serif" style={{ fontSize: 24, fontWeight: 400, color: 'var(--text-primary)' }}>{t(lang, "moodMatchTitle")}</p>
            <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', marginTop: 3 }}>
              {t(lang, "findAllPairs", CARDS.length)} · {t(lang, "movesCount", moves)}
            </p>
          </div>
          <button onClick={onClose} style={{ background:'none', border:'none', color:'var(--text-muted)', fontSize:20, cursor:'pointer', lineHeight:1 }}>×</button>
        </div>

        {/* Progress */}
        <div style={{ height: 3, background: 'rgba(var(--surface-tint),0.06)', borderRadius: 2, marginBottom: 20, overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${(matched.length / CARDS.length) * 100}%`,
            background: 'linear-gradient(90deg, #8b6fd4, #3dd9c8)',
            transition: 'width 0.5s ease',
          }} />
        </div>

        {/* Grid */}
        {!won ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
            {cards.map(card => {
              const face = isFlipped(card)
              const isMatchedCard = matched.includes(card.emoji)
              return (
                <div key={card.id} onClick={() => handleFlip(card)} style={{
                  height: 66, borderRadius: 12, cursor: face ? 'default' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: face ? 28 : 0,
                  background: isMatchedCard
                    ? 'rgba(61,217,200,0.15)'
                    : face
                      ? 'rgba(139,111,212,0.2)'
                      : 'rgba(var(--surface-tint),0.05)',
                  border: `1px solid ${isMatchedCard ? 'rgba(61,217,200,0.4)' : face ? 'rgba(139,111,212,0.4)' : 'rgba(var(--surface-tint),0.08)'}`,
                  transition: 'all 0.25s cubic-bezier(0.22,1,0.36,1)',
                  transform: face ? 'scale(1.04)' : 'scale(1)',
                  boxShadow: isMatchedCard ? '0 0 16px rgba(61,217,200,0.3)' : 'none',
                }}>
                  {face ? card.emoji : (
                    <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(var(--surface-tint),0.08)' }} />
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="animate-pop-in" style={{ textAlign: 'center', padding: '20px 0' }}>
            <p style={{ fontSize: 48, marginBottom: 12 }}>🎉</p>
            <p className="serif" style={{ fontSize: 26, color: 'var(--text-primary)', marginBottom: 6 }}>{t(lang, "youMatchedAll")}</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>{t(lang, "completedInMoves", moves)}</p>
            <div style={{ display:'flex', gap:10, justifyContent:'center' }}>
              <button onClick={reset} style={{
                padding: '10px 24px', borderRadius: 10, border: 'none', cursor: 'pointer',
                background: 'linear-gradient(135deg, #8b6fd4, #3dd9c8)',
                color: '#fff', fontSize: 13, fontFamily: 'DM Sans', fontWeight: 500,
              }}>{t(lang, "playAgain")}</button>
              <button onClick={onClose} style={{
                padding: '10px 24px', borderRadius: 10, cursor: 'pointer',
                background: 'rgba(var(--surface-tint),0.06)', border: '1px solid rgba(var(--surface-tint),0.1)',
                color: 'var(--text-secondary)', fontSize: 13, fontFamily: 'DM Sans',
              }}>{t(lang, "close")}</button>
            </div>
          </div>
        )}

        {!won && (
          <button onClick={reset} style={{
            width: '100%', marginTop: 16, padding: '10px', borderRadius: 10,
            background: 'rgba(var(--surface-tint),0.04)', border: '1px solid rgba(var(--surface-tint),0.08)',
            color: 'var(--text-muted)', fontSize: 12, fontFamily: 'DM Mono',
            cursor: 'pointer', letterSpacing: '0.06em',
          }}>↺ {t(lang, "shuffleRestart")}</button>
        )}
      </div>
    </div>
  )
}
