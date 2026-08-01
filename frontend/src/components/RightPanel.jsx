import { useState, useMemo } from "react"
import MoodGame from "./MoodGame"

const EMOTION_COLORS = {
  happy:"#e2b94b", sad:"#4d8de8", angry:"#e06b6b",
  fearful:"#b39dff", surprised:"#3dd9c8", disgusted:"#6bc8a0", neutral:"#6478a0"
}
const EMOTION_EMOJI = {
  happy:"😊", sad:"😔", angry:"😠", fearful:"😨",
  surprised:"😲", disgusted:"😒", neutral:"😐"
}

// Large rotating pool — 8+ tips per emotion, 4 shown randomly each session
const TIP_POOL = {
  sad: [
    { icon:"🌤", title:"Step outside", detail:"Even 10 minutes of sunlight shifts serotonin. Walk slowly — notice the air, the sounds, the light." },
    { icon:"✍️", title:"Keep writing", detail:"You've already started. Write without stopping for 5 more minutes — let feelings move through the pen." },
    { icon:"🍵", title:"Make something warm", detail:"Hold the cup. Let the warmth be a small, deliberate act of care for yourself." },
    { icon:"📱", title:"Reach out", detail:"Text someone you trust — not to explain everything, just to say hello. Connection is medicine." },
    { icon:"🎵", title:"Match the mood first", detail:"Play music that fits how you feel right now, then gradually shift to something lighter." },
    { icon:"🛁", title:"Take a shower", detail:"Hot water physically relaxes the nervous system. Let it reset you." },
    { icon:"🍊", title:"Eat something nourishing", detail:"Low blood sugar amplifies sadness. Give your body something real to work with." },
    { icon:"🌙", title:"Rest without guilt", detail:"Sometimes doing nothing is exactly the right thing. You're allowed to just exist right now." },
    { icon:"📚", title:"Read something light", detail:"A few pages of a good book gently shifts where your mind goes without forcing it." },
    { icon:"🐾", title:"Touch something soft", detail:"A pet, a blanket, a pillow — physical comfort signals safety to your nervous system." },
  ],
  angry: [
    { icon:"💨", title:"Exhale slowly", detail:"Longer out than in. 4 counts in, 6 counts out. Your nervous system responds to the exhale." },
    { icon:"🚶", title:"Move your body", detail:"A brisk walk, jumping jacks — anger is energy, give it somewhere to go." },
    { icon:"✉️", title:"Unsent letter", detail:"Write everything you wish you could say. Don't send it. Just let it out." },
    { icon:"💧", title:"Cold water", detail:"Splash your face or run cold water on your wrists. Triggers the dive reflex — instant calm." },
    { icon:"🥊", title:"Physical release", detail:"Punch a pillow. Do push-ups. Scream into a pillow. The body stores anger — move it out." },
    { icon:"🎧", title:"Loud music", detail:"Put on something loud and raw. Let your body feel the anger safely for 3 minutes, then shift." },
    { icon:"🖊️", title:"Name what was violated", detail:"Anger usually signals a boundary was crossed. Write: 'What I needed was...'." },
    { icon:"⏱️", title:"Wait 20 minutes", detail:"The cortisol spike from anger peaks at 20 mins. Don't send that message yet." },
  ],
  fearful: [
    { icon:"👁", title:"5-4-3-2-1", detail:"Name 5 things you see, 4 touch, 3 hear, 2 smell, 1 taste. You are here. You are safe." },
    { icon:"📦", title:"Box breathing", detail:"In 4, hold 4, out 4, hold 4. Repeat 4 times. Used by first responders under pressure." },
    { icon:"🧩", title:"What's in your control?", detail:"Write two lists: what I can control, what I cannot. Focus only on the first list." },
    { icon:"🤝", title:"Tell someone", detail:"Fear shrinks when spoken aloud. Text someone safe — you don't need to have it figured out." },
    { icon:"🔬", title:"Reality-test", detail:"Ask: what is the actual probability this goes wrong? What evidence do I have?" },
    { icon:"🏃", title:"Light movement", detail:"Anxiety is the body preparing to run. Give it a small version of that — a short walk works." },
    { icon:"📺", title:"Distract briefly", detail:"10 minutes of something absorbing (video, puzzle) breaks the anxiety loop. Then return." },
    { icon:"🌊", title:"Ride the wave", detail:"Anxiety peaks and passes — usually within 10-20 minutes if you don't add fuel. Let it crest." },
  ],
  happy: [
    { icon:"⏸", title:"Savour this", detail:"Pause. Notice exactly what happiness feels like in your body. Anchor this memory consciously." },
    { icon:"🎨", title:"Create something", detail:"Happy states are creative states. Write, draw, build, cook — use this energy." },
    { icon:"💌", title:"Share the feeling", detail:"Tell someone who matters. Joy amplifies when witnessed." },
    { icon:"📖", title:"Note what worked", detail:"What made today different? Write it so you can find your way back here." },
    { icon:"🌱", title:"Start something new", detail:"Good energy is the perfect time to begin — a habit, a project, a conversation." },
    { icon:"🙏", title:"Feel grateful", detail:"Write 3 specific things that contributed to how you feel right now." },
    { icon:"🎯", title:"Set an intention", detail:"Ride this momentum. What's one thing you've been putting off that you could do today?" },
    { icon:"🫂", title:"Do something kind", detail:"Happy people who share it compound the feeling. Do something small for someone else." },
  ],
  surprised: [
    { icon:"🌊", title:"Sit with it", detail:"You don't need to resolve the unexpected right now. Uncertainty is not danger." },
    { icon:"📝", title:"Write what changed", detail:"Journal what this surprise means for you. Let the meaning emerge slowly." },
    { icon:"🗣", title:"Process aloud", detail:"Talking through surprise with someone helps the brain integrate the new information." },
    { icon:"⏳", title:"Give it time", detail:"Your first reaction to surprise is rarely your full reaction. Sleep on it before deciding anything." },
    { icon:"🔍", title:"Get curious", detail:"Ask: what does this open up that wasn't possible before? Sometimes surprises are doors." },
  ],
  disgusted: [
    { icon:"🎯", title:"Name the value", detail:"Disgust signals a value was violated. What matters to you that was crossed here?" },
    { icon:"🚪", title:"Create distance", detail:"Physically move away from what triggered this. Space is a legitimate response." },
    { icon:"✍️", title:"Write without judgment", detail:"Let yourself feel it fully on paper. No editing, no softening." },
    { icon:"🌬️", title:"Cleanse physically", detail:"Wash your hands, change your environment. Physical cleansing signals the feeling is complete." },
    { icon:"🗣", title:"Set a boundary", detail:"Name what's not okay for you. You don't owe anyone your comfort with things that disgust you." },
  ],
  neutral: [
    { icon:"🔍", title:"Check in deeper", detail:"Is this peace, or numbness? Sit quietly for 60 seconds and notice what comes up." },
    { icon:"✨", title:"Notice beauty", detail:"Find one small beautiful or interesting thing in your immediate surroundings right now." },
    { icon:"🎁", title:"One thing for you", detail:"Do one thing today purely for your own enjoyment — not productivity, not anyone else." },
    { icon:"🌿", title:"Step away from screens", detail:"A few minutes offline lets quieter feelings surface. They're often more interesting." },
    { icon:"🎲", title:"Do something random", detail:"Break your routine in one small way — different route, different music, different meal." },
    { icon:"💬", title:"Start a conversation", detail:"Neutral moods are great for connecting. Reach out to someone you haven't spoken to recently." },
  ],
}

const QUOTES = [
  { text: "You don't have to see the whole staircase, just take the first step.", author: "Martin Luther King Jr." },
  { text: "Even the darkest night will end and the sun will rise.", author: "Victor Hugo" },
  { text: "Feelings are just visitors. Let them come and go.", author: "Mooji" },
  { text: "You are allowed to be both a masterpiece and a work in progress.", author: "Sophia Bush" },
  { text: "Almost everything will work again if you unplug it for a few minutes.", author: "Anne Lamott" },
  { text: "Be gentle with yourself. You are a child of the universe.", author: "Max Ehrmann" },
  { text: "Nothing in the universe can stop you from letting go and starting over.", author: "Guy Finley" },
  { text: "Breathe. It's just a bad day, not a bad life.", author: "Unknown" },
  { text: "The emotion that can break your heart is sometimes the very one that heals it.", author: "Nicholas Sparks" },
  { text: "Happiness is not something ready-made. It comes from your own actions.", author: "Dalai Lama" },
  { text: "You are braver than you believe, stronger than you seem.", author: "A.A. Milne" },
  { text: "In the middle of difficulty lies opportunity.", author: "Albert Einstein" },
  { text: "Stars can't shine without darkness.", author: "Unknown" },
  { text: "You are enough. You have enough. You do enough.", author: "Brené Brown" },
  { text: "The present moment always will have been.", author: "Eckhart Tolle" },
  { text: "Not all storms come to disrupt your life — some come to clear your path.", author: "Unknown" },
  { text: "Courage is feeling the fear and doing it anyway.", author: "Susan Jeffers" },
  { text: "What you seek is seeking you.", author: "Rumi" },
  { text: "Joy is not in things — it is in us.", author: "Richard Wagner" },
  { text: "You owe yourself the love you so freely give others.", author: "Unknown" },
  { text: "Be the energy you want to attract.", author: "Unknown" },
  { text: "Healing is not linear.", author: "Unknown" },
  { text: "Your feelings are valid. Every single one of them.", author: "Unknown" },
  { text: "Small steps every day still move you forward.", author: "Unknown" },
  { text: "Rest is not a reward. It is a necessity.", author: "Unknown" },
  { text: "The strongest people make time to help others, even if they are struggling themselves.", author: "Roy T. Bennett" },
  { text: "You cannot pour from an empty cup. Take care of yourself first.", author: "Unknown" },
  { text: "Every day is a chance to begin again.", author: "Unknown" },
  { text: "Your mental health is a priority. Your happiness is essential.", author: "Unknown" },
  { text: "It's okay to not be okay. Just don't stay there.", author: "Unknown" },
]

function getDailyQuote() {
  const day = Math.floor(Date.now() / 86400000)
  return QUOTES[day % QUOTES.length]
}

function getRandomTips(emotion, count = 4) {
  const pool = TIP_POOL[emotion] || TIP_POOL.neutral
  const shuffled = [...pool].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

function TipCard({ tip, color, isOpen, onToggle }) {
  return (
    <div onClick={onToggle} style={{
      borderRadius: 12, padding: '11px 13px', cursor: 'pointer',
      background: isOpen ? `${color}18` : 'rgba(255,255,255,0.03)',
      border: `1px solid ${isOpen ? color+'50' : 'rgba(255,255,255,0.07)'}`,
      transition: 'all 0.25s ease',
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <span style={{ fontSize:16, flexShrink:0 }}>{tip.icon}</span>
        <p style={{ fontSize:12, color: isOpen ? '#f0ece6' : '#9aa0bc', fontWeight:400, flex:1 }}>{tip.title}</p>
        <span style={{ fontSize:10, color, transition:'transform 0.2s', display:'inline-block', transform: isOpen ? 'rotate(180deg)' : 'none' }}>▾</span>
      </div>
      {isOpen && (
        <p className="animate-fade-up" style={{
          fontSize:12, color:'#9aa0bc', lineHeight:1.7, marginTop:9,
          paddingTop:9, borderTop:`1px solid ${color}28`, fontWeight:300,
        }}>{tip.detail}</p>
      )}
    </div>
  )
}

function RadarRing({ emotion, score, color, size=88 }) {
  const r = (size/2)-7
  const circ = 2*Math.PI*r
  const dash = circ * Math.min(score, 1)
  return (
    <div style={{ position:'relative', width:size, height:size, flexShrink:0 }}>
      <svg width={size} height={size} style={{ transform:'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={6}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke={color} strokeWidth={6} strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition:'stroke-dasharray 1.2s cubic-bezier(0.22,1,0.36,1)', filter:`drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:24 }}>
        {EMOTION_EMOJI[emotion]||'○'}
      </div>
    </div>
  )
}

export default function RightPanel({ result, loading, history }) {
  const [openTip, setOpenTip] = useState(null)
  const [showGame, setShowGame] = useState(false)

  const emotion = result?.unified_emotion || 'neutral'
  const confidence = result?.unified_confidence || 0
  const color = EMOTION_COLORS[emotion] || '#6478a0'

  // Tips shuffle fresh each session (useMemo with no deps = computed once per mount)
  const tips = useMemo(() => getRandomTips(emotion, 4), [emotion])
  const quote = useMemo(() => getDailyQuote(), [])

  const allScores = result?.fusion_result?.all_scores || {}
  const topThree  = Object.entries(allScores).sort((a,b)=>b[1]-a[1]).slice(0,3)

  const streak = (() => {
    if (!history.length) return 0
    const uniqueDays = [...new Set(history.map(h => new Date(h.timestamp).toDateString()))]
      .map(d => new Date(d)).sort((a,b) => b-a)
    let count = 0
    for (let i = 0; i < uniqueDays.length; i++) {
      const expected = new Date()
      expected.setDate(expected.getDate() - i)
      if (uniqueDays[i]?.toDateString() === expected.toDateString()) count++
      else break
    }
    return Math.max(count, history.length > 0 ? 1 : 0)
  })()

  return (
    <>
      {showGame && <MoodGame onClose={() => setShowGame(false)} />}

      <aside style={{ padding:'28px 14px', display:'flex', flexDirection:'column', gap:14, overflowY:'auto', maxHeight:'100vh' }}>

        {/* Emotion radar */}
        <div className="glass" style={{ borderRadius:18, padding:'18px 16px', display:'flex', flexDirection:'column', alignItems:'center', gap:14, border: result ? `1px solid ${color}35` : undefined }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', width:'100%' }}>
            <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', letterSpacing:'0.12em' }}>EMOTION RADAR</p>
            {result && <span className="mono" style={{ fontSize:10, color, letterSpacing:'0.06em' }}>{(confidence*100).toFixed(0)}%</span>}
          </div>

          {result && !loading ? (
            <>
              <RadarRing emotion={emotion} score={confidence} color={color} size={90}/>
              <div style={{ width:'100%', display:'flex', flexDirection:'column', gap:8 }}>
                {topThree.map(([e,s]) => (
                  <div key={e} style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <span style={{ fontSize:10, color:'var(--text-muted)', width:56, textTransform:'capitalize', fontFamily:'DM Mono' }}>{e}</span>
                    <div style={{ flex:1, height:3, background:'rgba(255,255,255,0.06)', borderRadius:2, overflow:'hidden' }}>
                      <div style={{
                        height:'100%', borderRadius:2, width:`${s*100}%`,
                        background:`linear-gradient(90deg, ${EMOTION_COLORS[e]}, ${EMOTION_COLORS[e]}aa)`,
                        boxShadow:`0 0 6px ${EMOTION_COLORS[e]}80`,
                        transition:'width 1s cubic-bezier(0.22,1,0.36,1)',
                      }}/>
                    </div>
                    <span className="mono" style={{ fontSize:10, color:'var(--text-muted)', width:26, textAlign:'right' }}>{(s*100).toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{ padding:'16px 0', textAlign:'center', width:'100%' }}>
              <div style={{ width:72, height:72, borderRadius:'50%', margin:'0 auto 10px', background:'rgba(255,255,255,0.03)', border:'2px dashed rgba(255,255,255,0.08)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:24, opacity:0.4 }}>○</div>
              <p style={{ fontSize:11, color:'var(--text-muted)', fontStyle:'italic' }}>Analyse an entry to see your emotion radar</p>
            </div>
          )}
        </div>

        {/* Streak + total */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
          <div className="glass" style={{ borderRadius:14, padding:'13px 12px', borderLeft:'2px solid #e2b94b' }}>
            <div style={{ fontSize:18, marginBottom:4 }}>🔥</div>
            <p className="serif" style={{ fontSize:22, fontWeight:700, color:'#e2b94b', lineHeight:1 }}>{streak}</p>
            <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', marginTop:3, letterSpacing:'0.08em' }}>DAY STREAK</p>
          </div>
          <div className="glass" style={{ borderRadius:14, padding:'13px 12px', borderLeft:'2px solid #b39dff' }}>
            <div style={{ fontSize:18, marginBottom:4 }}>📓</div>
            <p className="serif" style={{ fontSize:22, fontWeight:700, color:'#b39dff', lineHeight:1 }}>{history.length}</p>
            <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', marginTop:3, letterSpacing:'0.08em' }}>TOTAL</p>
          </div>
        </div>

        {/* Interactive wellness tips */}
        <div className="glass" style={{ borderRadius:18, padding:'16px 14px', border:`1px solid ${color}25` }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
            <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', letterSpacing:'0.12em' }}>
              {result ? `FOR ${emotion.toUpperCase()}` : 'WELLNESS TIPS'}
            </p>
            <span style={{ fontSize:9, color, fontFamily:'DM Mono', opacity:0.8 }}>tap ↓</span>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:7 }}>
            {tips.map((tip, i) => (
              <TipCard key={i} tip={tip} color={color} isOpen={openTip===i} onToggle={() => setOpenTip(openTip===i ? null : i)}/>
            ))}
          </div>
        </div>

        {/* Daily quote */}
        <div style={{
          borderRadius:16, padding:'16px',
          background:'linear-gradient(135deg, rgba(179,157,255,0.1), rgba(61,217,200,0.07))',
          border:'1px solid rgba(179,157,255,0.25)',
        }}>
          <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', letterSpacing:'0.12em', marginBottom:10 }}>✦ QUOTE OF THE DAY</p>
          <p className="serif" style={{ fontSize:14, fontStyle:'italic', color:'#d4cef0', lineHeight:1.75, fontWeight:300 }}>
            "{quote.text}"
          </p>
          <p className="mono" style={{ fontSize:9, color:'var(--text-muted)', marginTop:8, letterSpacing:'0.06em' }}>— {quote.author}</p>
        </div>

        {/* Game button */}
        <button onClick={() => setShowGame(true)} style={{
          width:'100%', padding:'12px', borderRadius:14,
          background:'linear-gradient(135deg, rgba(139,111,212,0.2), rgba(61,217,200,0.15))',
          border:'1px solid rgba(139,111,212,0.35)',
          color:'#c4a8f0', fontSize:12, fontFamily:'DM Mono',
          cursor:'pointer', letterSpacing:'0.08em',
          display:'flex', alignItems:'center', justifyContent:'center', gap:10,
          transition:'all 0.2s ease',
        }}
        onMouseEnter={e => e.currentTarget.style.background='linear-gradient(135deg, rgba(139,111,212,0.32), rgba(61,217,200,0.22))'}
        onMouseLeave={e => e.currentTarget.style.background='linear-gradient(135deg, rgba(139,111,212,0.2), rgba(61,217,200,0.15))'}
        >
          <span style={{ fontSize:16 }}>🎮</span>
          MOOD MATCH · PLAY A GAME
        </button>
      </aside>
    </>
  )
}
