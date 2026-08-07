import { useEffect } from "react"
import { createPortal } from "react-dom"

/* Shared "open this panel full screen" primitives, matching the overlay MoodGame
   already uses so expanding a card feels the same as opening the game. */

export function ExpandButton({ onClick, label = "Expand", style }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      title={label}
      aria-label={label}
      style={{
        background: 'none', border: '1px solid var(--border)', borderRadius: 8,
        color: 'var(--text-muted)', cursor: 'pointer', flexShrink: 0,
        fontSize: 12, lineHeight: 1, padding: '3px 6px',
        fontFamily: 'DM Mono, monospace', transition: 'all 0.18s ease',
        ...style,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = 'var(--text-primary)'
        e.currentTarget.style.borderColor = 'var(--border-hover)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = 'var(--text-muted)'
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >⤢</button>
  )
}

export default function FullscreenModal({ title, onClose, children, maxWidth = 900 }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    // stop the page behind the overlay from scrolling while it is open
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      window.removeEventListener("keydown", onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  /* Rendered through a portal to <body>: an ancestor with a transform (the
     dashboard's .animate-fade-up wrapper) or a backdrop-filter (.glass) becomes the
     containing block for position:fixed, which would otherwise pin this overlay
     inside that element instead of over the viewport. */
  return createPortal(
    <div
      className="modal-scrim"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 120,
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 20, width: '100%', maxWidth, maxHeight: '90vh',
          overflowY: 'auto', padding: '24px 26px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.45)',
        }}
      >
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 16, marginBottom: 20,
        }}>
          <p className="mono" style={{
            fontSize: 12, color: 'var(--text-muted)', letterSpacing: '0.12em',
          }}>{title}</p>
          <button
            onClick={onClose}
            title="Close"
            aria-label="Close"
            style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 8,
              color: 'var(--text-secondary)', cursor: 'pointer', flexShrink: 0,
              fontSize: 13, lineHeight: 1, padding: '5px 9px', fontFamily: 'DM Mono, monospace',
            }}
          >✕</button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  )
}
