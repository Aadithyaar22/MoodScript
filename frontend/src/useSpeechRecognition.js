import { useState, useRef, useCallback } from "react"
import { speechLangCode } from "./i18n"

export function useSpeechRecognition(lang, onResult) {
  const [isListening, setIsListening] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const recognitionRef = useRef(null)
  const timerRef = useRef(null)
  const shouldListenRef = useRef(false)

  const SpeechRecognitionImpl = typeof window !== "undefined"
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const createRecognition = useCallback(() => {
    const recognition = new SpeechRecognitionImpl()
    recognition.lang = speechLangCode(lang)
    // continuous keeps the mic open across pauses/sentences — without it the
    // browser stops listening the moment it detects a sentence-ending silence
    recognition.continuous = true
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          onResult(event.results[i][0].transcript)
        }
      }
    }
    recognition.onend = () => {
      // some browsers end the session on their own after a silence timeout
      // even with continuous=true — if the user hasn't clicked stop, resume
      if (shouldListenRef.current) {
        try { recognition.start(); return } catch { /* fall through to cleanup */ }
      }
      setIsListening(false)
      stopTimer()
    }
    recognition.onerror = (event) => {
      if (event.error === "no-speech" && shouldListenRef.current) return
      shouldListenRef.current = false
    }
    return recognition
  }, [lang, onResult, SpeechRecognitionImpl])

  const start = useCallback(() => {
    if (!SpeechRecognitionImpl) return
    shouldListenRef.current = true
    const recognition = createRecognition()
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
    setElapsedSeconds(0)
    stopTimer()
    timerRef.current = setInterval(() => setElapsedSeconds(s => s + 1), 1000)
  }, [createRecognition, SpeechRecognitionImpl])

  const stop = useCallback(() => {
    shouldListenRef.current = false
    recognitionRef.current?.stop()
    setIsListening(false)
    stopTimer()
  }, [])

  const toggle = useCallback(() => {
    if (isListening) stop()
    else start()
  }, [isListening, start, stop])

  return { isListening, elapsedSeconds, start, stop, toggle, supported: !!SpeechRecognitionImpl }
}

export function formatElapsed(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export function speak(text, lang) {
  if (typeof window === "undefined" || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = speechLangCode(lang)
  const voices = window.speechSynthesis.getVoices()
  const match = voices.find(v => v.lang === utterance.lang) || voices.find(v => v.lang?.startsWith(lang))
  if (match) utterance.voice = match
  window.speechSynthesis.speak(utterance)
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel()
}
