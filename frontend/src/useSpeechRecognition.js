import { useState, useRef, useCallback } from "react"
import { speechLangCode } from "./i18n"

export function useSpeechRecognition(lang, onResult) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  const SpeechRecognitionImpl = typeof window !== "undefined"
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null

  const start = useCallback(() => {
    if (!SpeechRecognitionImpl) return
    const recognition = new SpeechRecognitionImpl()
    recognition.lang = speechLangCode(lang)
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      onResult(transcript)
    }
    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }, [lang, onResult, SpeechRecognitionImpl])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }, [])

  const toggle = useCallback(() => {
    if (isListening) stop()
    else start()
  }, [isListening, start, stop])

  return { isListening, start, stop, toggle, supported: !!SpeechRecognitionImpl }
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
