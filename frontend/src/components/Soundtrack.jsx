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
// The three-stage structure is meaningless without saying what it is for. Users see
// "Meets you here" and have no reason to know that starting sad is deliberate rather
// than the app misreading them.
const STAGE_SUB = { meet: "stageMeetSub", bridge: "stageBridgeSub", lift: "stageLiftSub" }

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

      <p style={{
        fontSize: big ? 14 : 11.5, color: "var(--text-muted)", lineHeight: 1.55,
        fontStyle: "italic", marginBottom: big ? 4 : 2,
      }}>
        {t(lang, "soundtrackIntro")}
      </p>

      {stages.map(stage => (
        <div key={stage.stage} style={{ display: "flex", flexDirection: "column", gap: big ? 8 : 5 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 7, flexWrap: "wrap" }}>
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, flexShrink: 0 }}/>
            <p className="mono" style={{ fontSize: big ? 12 : 10, color: "var(--text-muted)", letterSpacing: "0.1em" }}>
              {t(lang, STAGE_LABEL[stage.stage] || "soundtrack")}
            </p>
            <span style={{ fontSize: big ? 12.5 : 10.5, color: "var(--text-muted)", opacity: 0.75 }}>
              — {t(lang, STAGE_SUB[stage.stage] || "soundtrack")}
            </span>
          </div>

          {stage.tracks.map(track => {
            const playing = playingId === track.id
            return (
              /* A div, not a button: the external links live inside this row and an
                 anchor nested in a button is invalid and breaks keyboard navigation.
                 The play control is its own button; the links are their own anchors. */
              <div
                key={track.id}
                style={{
                  display: "flex", alignItems: "center", gap: big ? 12 : 9, width: "100%",
                  padding: big ? "10px 12px" : "7px 9px", borderRadius: 10,
                  background: playing ? `${color}1c` : "rgba(var(--surface-tint),0.04)",
                  border: `1px solid ${playing ? color + "55" : "rgba(var(--surface-tint),0.07)"}`,
                  transition: "background .18s, border-color .18s",
                }}
              >
                <button
                  onClick={() => toggle(track)}
                  aria-label={`${playing ? "Pause" : "Play"} ${track.title} by ${track.artist}`}
                  style={{
                    width: big ? 28 : 22, height: big ? 28 : 22, borderRadius: "50%", flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center", border: "none",
                    background: playing ? color : `${color}30`,
                    color: playing ? "#fff" : color, cursor: "pointer", padding: 0,
                  }}
                >
                  <PlayIcon playing={playing}/>
                </button>

                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{
                    display: "block", fontSize: big ? 14.5 : 12.5, color: "var(--text-primary)",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>{track.title}</span>
                  {/* Wraps rather than shrinks. The right panel is 248px wide, leaving
                      ~190px here, and letting the artist name shrink to fit two links
                      beside it collapsed it to a single stray character. The links have
                      a fixed size and the name keeps a floor, so on a narrow panel the
                      links drop to their own line instead. */}
                  <span style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, flexWrap: "wrap" }}>
                    <span className="mono" style={{
                      fontSize: big ? 12 : 10.5, color: "var(--text-muted)",
                      minWidth: big ? 120 : 84, flex: "1 1 auto",
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                    }}>{track.artist}</span>
                    {track.youtube && (
                      <a href={track.youtube} target="_blank" rel="noopener noreferrer"
                         title={`${t(lang, "findOnYoutube")}: ${track.artist} — ${track.title}`}
                         className="mono"
                         style={{ fontSize: big ? 11 : 9.5, color, opacity: 0.85, flexShrink: 0, textDecoration: "none" }}>
                        ↗{t(lang, "findOnYoutube")}
                      </a>
                    )}
                    {track.share_url && (
                      <a href={track.share_url} target="_blank" rel="noopener noreferrer"
                         title={`${t(lang, "openOnJamendo")}: ${track.artist} — ${track.title}`}
                         className="mono"
                         style={{ fontSize: big ? 11 : 9.5, color: "var(--text-muted)", flexShrink: 0, textDecoration: "none" }}>
                        ↗{t(lang, "openOnJamendo")}
                      </a>
                    )}
                  </span>
                </span>

                <span className="mono" style={{ fontSize: big ? 12 : 10.5, color: "var(--text-muted)", flexShrink: 0 }}>
                  {fmt(track.duration)}
                </span>
              </div>
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
