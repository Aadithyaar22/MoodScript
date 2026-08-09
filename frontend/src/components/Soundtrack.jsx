import { useRef, useState } from "react"
import { t } from "../i18n"

/* A soundtrack that follows the entry's emotional trajectory rather than its label.
   Three stages, in order: the music meets the mood, moves through it, then eases out
   (the iso-principle — see models/music.py for why matching alone is the wrong design).

   Deliberately no autoplay. The user asked for the soundtrack; they did not ask to be
   played at. One <audio> element is shared across every track so that starting a second
   one stops the first — separate elements per track let a user accidentally stack four
   songs on top of each other, which is unpleasant at the best of times and worse when
   the entry was about feeling overwhelmed. */

const STAGE_LABEL = { meet: "stageMeet", bridge: "stageBridge", lift: "stageLift" }

function PlayIcon({ playing }) {
  return (
    <svg width="13" height="13" viewBox="0 0 12 12" aria-hidden="true">
      {playing
        ? <><rect x="2" y="1.5" width="3" height="9" rx="1" fill="currentColor"/>
            <rect x="7" y="1.5" width="3" height="9" rx="1" fill="currentColor"/></>
        : <path d="M3 1.5 L10.5 6 L3 10.5 Z" fill="currentColor"/>}
    </svg>
  )
}

function fmt(seconds) {
  if (!seconds && seconds !== 0) return ""
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, "0")}`
}

export default function Soundtrack({ data, color, lang = "en", big = false }) {
  const [playingId, setPlayingId] = useState(null)
  const audioRef = useRef(null)

  const toggle = (track) => {
    const el = audioRef.current
    if (!el) return
    if (playingId === track.id) {
      el.pause()
      setPlayingId(null)
      return
    }
    el.src = track.audio
    el.play().then(() => setPlayingId(track.id)).catch(() => setPlayingId(null))
  }

  if (data?.suppressed) {
    return (
      <p style={{ fontSize: big ? 15 : 12.5, color: "var(--text-muted)", fontStyle: "italic" }}>
        {t(lang, "soundtrackCrisis")}
      </p>
    )
  }

  const stages = (data?.stages || []).filter(s => s.tracks?.length)
  if (!stages.length) {
    return (
      <p style={{ fontSize: big ? 15 : 12.5, color: "var(--text-muted)", fontStyle: "italic" }}>
        {t(lang, "soundtrackNone")}
      </p>
    )
  }

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: big ? 16 : 11 }}>
      <audio ref={audioRef} onEnded={() => setPlayingId(null)} preload="none"/>

      {stages.map(stage => (
        <div key={stage.stage} style={{ display: "flex", flexDirection: "column", gap: big ? 8 : 5 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, flexShrink: 0 }}/>
            <p className="mono" style={{ fontSize: big ? 12 : 10, color: "var(--text-muted)", letterSpacing: "0.1em" }}>
              {t(lang, STAGE_LABEL[stage.stage] || "soundtrack")}
            </p>
          </div>

          {stage.tracks.map(track => {
            const playing = playingId === track.id
            return (
              <button
                key={track.id}
                onClick={() => toggle(track)}
                aria-label={`${playing ? "Pause" : "Play"} ${track.title} by ${track.artist}`}
                style={{
                  display: "flex", alignItems: "center", gap: big ? 12 : 9, width: "100%",
                  padding: big ? "10px 12px" : "7px 9px", borderRadius: 10, textAlign: "left",
                  background: playing ? `${color}1c` : "rgba(var(--surface-tint),0.04)",
                  border: `1px solid ${playing ? color + "55" : "rgba(var(--surface-tint),0.07)"}`,
                  cursor: "pointer", transition: "background .18s, border-color .18s",
                }}
              >
                <span style={{
                  width: big ? 28 : 22, height: big ? 28 : 22, borderRadius: "50%", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: playing ? color : `${color}30`,
                  color: playing ? "#fff" : color,
                }}>
                  <PlayIcon playing={playing}/>
                </span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{
                    display: "block", fontSize: big ? 14.5 : 12.5, color: "var(--text-primary)",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>{track.title}</span>
                  <span className="mono" style={{
                    display: "block", fontSize: big ? 12 : 10.5, color: "var(--text-muted)",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>{track.artist}</span>
                </span>
                <span className="mono" style={{ fontSize: big ? 12 : 10.5, color: "var(--text-muted)", flexShrink: 0 }}>
                  {fmt(track.duration)}
                </span>
              </button>
            )
          })}
        </div>
      ))}

      {/* Attribution is a licence condition of using Creative Commons audio, not decoration. */}
      <p className="mono" style={{ fontSize: big ? 11 : 9.5, color: "var(--text-muted)", opacity: 0.75, letterSpacing: "0.04em" }}>
        {t(lang, "soundtrackCC")}
      </p>
    </div>
  )
}
