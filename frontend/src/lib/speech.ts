// Browser Text-to-Speech and Audio utilities

let enabled = true
let voice: SpeechSynthesisVoice | null = null
let alarmEnabled = true
let alarmInterval: ReturnType<typeof setInterval> | null = null
let audioContext: AudioContext | null = null

// Try to find a good voice (prefer Microsoft or Google voices)
function initVoice() {
  const voices = speechSynthesis.getVoices()
  // Prefer Microsoft or Google voices
  voice = voices.find(v => v.name.includes('Microsoft') || v.name.includes('Google')) 
    || voices.find(v => v.lang.startsWith('en'))
    || voices[0]
}

// Voices load async, so init when ready
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  speechSynthesis.onvoiceschanged = initVoice
  initVoice()
}

export function speak(text: string) {
  if (!enabled || typeof window === 'undefined' || !('speechSynthesis' in window)) return
  
  // Cancel any ongoing speech
  speechSynthesis.cancel()
  
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 1.1 // Slightly faster
  utterance.pitch = 1
  utterance.volume = 1
  if (voice) utterance.voice = voice
  
  speechSynthesis.speak(utterance)
}

export function setSpeechEnabled(value: boolean) {
  enabled = value
  if (!value) speechSynthesis.cancel()
}

export function isSpeechEnabled() {
  return enabled
}

// === Motion Alarm ===

function getAudioContext() {
  if (!audioContext) {
    audioContext = new AudioContext()
  }
  return audioContext
}

function beep(frequency = 800, duration = 100) {
  if (!alarmEnabled) return
  
  try {
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gain = ctx.createGain()
    
    oscillator.connect(gain)
    gain.connect(ctx.destination)
    
    oscillator.frequency.value = frequency
    oscillator.type = 'square'
    gain.gain.value = 0.1 // Keep it soft
    
    oscillator.start()
    oscillator.stop(ctx.currentTime + duration / 1000)
  } catch (e) {
    console.error('Beep failed', e)
  }
}

export function startMotionAlarm() {
  if (alarmInterval) return // Already running
  
  beep(600, 150) // Initial beep
  alarmInterval = setInterval(() => beep(600, 150), 1000) // Beep every second
}

export function stopMotionAlarm() {
  if (alarmInterval) {
    clearInterval(alarmInterval)
    alarmInterval = null
  }
}

export function setAlarmEnabled(value: boolean) {
  alarmEnabled = value
  if (!value) stopMotionAlarm()
}

export function isAlarmEnabled() {
  return alarmEnabled
}
