import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts"
import { fetchHistory, fetchRating, fetchReflection } from "../api"
import { t } from "../i18n"

const TREND_CONFIG = {
  improving: { emoji: "📈", color: "#4eb496", key: "improving" },
  declining: { emoji: "📉", color: "#cd4e4e", key: "declining" },
  steady:    { emoji: "➖", color: "#6478a0", key: "steady" },
}

const RATING_LABEL_KEY = {
  "Doing well": "doingWell",
  "Holding steady": "holdingSteady",
  "Struggling a bit": "strugglingBit",
  "Having a hard time": "havingHardTime",
}

const EMOTION_SCORE  = { happy:6, surprised:5, neutral:4, fearful:3, disgusted:2, sad:1, angry:0 }
const EMOTION_COLORS = { happy:"#c9a84c", sad:"#4e78cd", angry:"#cd4e4e", fearful:"#9d7fd4", surprised:"#cd8c4e", disgusted:"#4eb496", neutral:"#6478a0" }
const EMOTION_EMOJI  = { happy:"😊", sad:"😔", angry:"😠", fearful:"😨", surprised:"😲", disgusted:"😒", neutral:"😐" }

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{ background: 'var(--bg)', border: '1px solid rgba(var(--surface-tint),0.1)', borderRadius: 10, padding: '10px 14px' }}>
      <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{d?.name}</p>
      <p style={{ fontSize: 14, color: 'var(--text-primary)', textTransform: 'capitalize' }}>{EMOTION_EMOJI[d?.emotion]} {d?.emotion}</p>
    </div>
  )
}

export default function Dashboard({ lang = "en" }) {
  const [history, setHistory] = useState([])
  const [rating, setRating] = useState(null)
  const [reflection, setReflection] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistory().then(d => setHistory([...d].reverse())).catch(console.error).finally(() => setLoading(false))
    fetchRating().then(setRating).catch(console.error)
    fetchReflection().then(setReflection).catch(console.error)
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {[80, 280, 240].map((h, i) => <div key={i} className="glass shimmer" style={{ height: h, borderRadius: 16 }} />)}
    </div>
  )

  if (!history.length) return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <p className="serif" style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>📓</p>
      <p className="serif" style={{ fontSize: 22, color: 'var(--text-secondary)', fontWeight: 300, fontStyle: 'italic' }}>{t(lang, "noEntriesYet")}</p>
      <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 8 }}>{t(lang, "analyseFirstEntry")}</p>
    </div>
  )

  const lineData = history.map(h => ({
    name: new Date(h.timestamp).toLocaleDateString("en-IN", { month:"short", day:"numeric" }),
    score: EMOTION_SCORE[h.emotion] ?? 4,
    emotion: h.emotion,
  }))

  const emotionCounts = history.reduce((acc, h) => { acc[h.emotion] = (acc[h.emotion]||0)+1; return acc }, {})
  const pieData = Object.entries(emotionCounts).map(([name,value]) => ({ name, value }))
  const dominant = Object.entries(emotionCounts).sort((a,b)=>b[1]-a[1])[0]
  const latest = history[history.length-1]

  const StatCard = ({ label, value, sub }) => (
    <div className="glass" style={{ borderRadius: 16, padding: '20px 22px' }}>
      <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 8 }}>{label}</p>
      <p className="serif" style={{ fontSize: 28, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1 }}>{value}</p>
      {sub && <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</p>}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }} className="animate-fade-up">
      {/* Heading */}
      <div style={{ paddingBottom: 8 }}>
        <h2 className="serif" style={{ fontSize: 36, fontWeight: 300, color: 'var(--text-primary)' }}>{t(lang, "moodHistory")}</h2>
        <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', marginTop: 4 }}>{history.length} {t(lang, "entriesRecorded")}</p>
      </div>

      {/* Overall rating */}
      {rating?.score !== null && rating !== null && (
        <div className="glass" style={{ borderRadius: 18, padding: '24px 26px', display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ position: 'relative', width: 88, height: 88, flexShrink: 0 }}>
            <svg width={88} height={88} style={{ transform: 'rotate(-90deg)' }}>
              <circle cx={44} cy={44} r={37} fill="none" stroke="rgba(var(--surface-tint),0.06)" strokeWidth={7} />
              <circle cx={44} cy={44} r={37} fill="none" stroke="#9d7fd4" strokeWidth={7} strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 37 * (rating.score / 100)} ${2 * Math.PI * 37}`}
                style={{ filter: 'drop-shadow(0 0 6px #9d7fd4)' }} />
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="serif" style={{ fontSize: 26, fontWeight: 600, color: 'var(--text-primary)' }}>{rating.score}</span>
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 6 }}>{t(lang, "overallRating")}</p>
            <p className="serif" style={{ fontSize: 22, fontWeight: 300, color: 'var(--text-primary)', marginBottom: 6 }}>{t(lang, RATING_LABEL_KEY[rating.label]) || rating.label}</p>
            <p style={{ fontSize: 12, color: TREND_CONFIG[rating.trend]?.color || 'var(--text-muted)' }}>
              {TREND_CONFIG[rating.trend]?.emoji} {t(lang, TREND_CONFIG[rating.trend]?.key)} · {rating.entry_count} {t(lang, "entries")}
            </p>
          </div>
        </div>
      )}

      {/* Weekly reflection */}
      {reflection?.content && (
        <div style={{
          borderRadius: 18, padding: '22px 24px',
          background: 'linear-gradient(135deg, rgba(139,111,212,0.1), rgba(61,217,200,0.06))',
          border: '1px solid rgba(139,111,212,0.25)',
        }}>
          <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 12 }}>
            ✦ {t(lang, "weeklyReflection")} · {reflection.entry_count} {t(lang, "entries")}
          </p>
          <p className="serif" style={{ fontSize: 16, fontWeight: 300, fontStyle: 'italic', color: 'var(--violet-soft-text)', lineHeight: 1.8 }}>
            {reflection.content}
          </p>
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
        <StatCard label={t(lang, "totalEntries")} value={history.length} />
        <StatCard label={t(lang, "mostCommon")} value={`${EMOTION_EMOJI[dominant?.[0]]} ${t(lang, dominant?.[0])}`} sub={`${dominant?.[1]} ×`} />
        <StatCard label={t(lang, "latest")} value={`${EMOTION_EMOJI[latest?.emotion]} ${t(lang, latest?.emotion)}`} sub={new Date(latest?.timestamp).toLocaleDateString("en-IN", { month:'short', day:'numeric' })} />
      </div>

      {/* Line chart */}
      <div className="glass" style={{ borderRadius: 16, padding: '24px' }}>
        <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 20 }}>{t(lang, "moodOverTime")}</p>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={lineData}>
            <CartesianGrid strokeDasharray="2 4" stroke="rgba(var(--surface-tint),0.04)" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'DM Mono' }} axisLine={false} tickLine={false} />
            <YAxis domain={[0,6]} hide />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="score" stroke="#7b5ea7" strokeWidth={2}
              dot={{ r: 4, fill: '#7b5ea7', strokeWidth: 0 }}
              activeDot={{ r: 6, fill: '#9d7fd4', strokeWidth: 0 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Pie chart */}
      <div className="glass" style={{ borderRadius: 16, padding: '24px' }}>
        <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 20 }}>{t(lang, "emotionDistribution")}</p>
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} innerRadius={30}
              label={({ name, percent }) => `${EMOTION_EMOJI[name]} ${(percent*100).toFixed(0)}%`}
              labelLine={false}>
              {pieData.map(e => <Cell key={e.name} fill={EMOTION_COLORS[e.name]||"#6478a0"} />)}
            </Pie>
            <Tooltip contentStyle={{ background:'var(--bg)', border:'1px solid rgba(var(--surface-tint),0.1)', borderRadius:10, fontFamily:'DM Mono' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Recent list */}
      <div className="glass" style={{ borderRadius: 16, padding: '24px' }}>
        <p className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 20 }}>{t(lang, "recentEntries")}</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {[...history].reverse().slice(0,8).map((h, i) => (
            <div key={h.id} style={{
              display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 0',
              borderBottom: i < 7 ? '1px solid var(--border)' : 'none',
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                background: `${EMOTION_COLORS[h.emotion] || '#6478a0'}20`,
                border: `1px solid ${EMOTION_COLORS[h.emotion] || '#6478a0'}40`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
              }}>
                {EMOTION_EMOJI[h.emotion] || "😐"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 14, color: 'var(--text-primary)', textTransform: 'capitalize', fontWeight: 400 }}>{t(lang, h.emotion)}</span>
                  {h.face_emotion && h.face_emotion !== h.text_emotion && (
                    <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>face: {h.face_emotion}</span>
                  )}
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    {new Date(h.timestamp).toLocaleString("en-IN", { month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" })}
                  </span>
                </div>
                {h.journal_snippet && (
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {h.journal_snippet}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
