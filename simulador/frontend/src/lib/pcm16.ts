/**
 * Utilidades para manejar audio PCM16 (formato requerido por OpenAI Realtime API)
 */

/**
 * Convierte Float32Array (formato nativo Web Audio API) a PCM16 (Int16Array)
 */
export function float32ToPCM16(float32Array: Float32Array): Int16Array {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return pcm16;
}

/**
 * Convierte ArrayBuffer a Base64 (para enviar por WebSocket)
 */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Convierte Base64 a PCM16 Int16Array (para reproducir audio del agente)
 */
export function base64ToPCM16(base64: string): Int16Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}

function pcm16ToFloat32(pcm16: Int16Array): Float32Array {
  const float32 = new Float32Array(pcm16.length)
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / 32768.0
  }
  return float32
}

function resampleLinear(
  input: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number
): Float32Array {
  if (sourceSampleRate === targetSampleRate) return input

  const ratio = targetSampleRate / sourceSampleRate
  const outputLength = Math.max(1, Math.round(input.length * ratio))
  const output = new Float32Array(outputLength)

  for (let i = 0; i < outputLength; i++) {
    const sourceIndex = i / ratio
    const index0 = Math.floor(sourceIndex)
    const index1 = Math.min(index0 + 1, input.length - 1)
    const t = sourceIndex - index0
    const sample0 = input[index0] ?? 0
    const sample1 = input[index1] ?? 0
    output[i] = sample0 + (sample1 - sample0) * t
  }

  return output
}

/**
 * Cola de audio para reproducción secuencial
 */
class AudioQueue {
  private queue: Int16Array[] = []
  private audioContext: AudioContext
  private nextStartTime = 0
  private gainNode: GainNode
  private scheduledSources = new Set<AudioBufferSourceNode>()
  private onQueueEmptyCallback: (() => void) | null = null
  private hasLoggedResample = false
  private hasLoggedScheduler = false

  private lookaheadSeconds = 0.25
  private startDelaySeconds = 0.03

  constructor(audioContext: AudioContext) {
    this.audioContext = audioContext
    this.gainNode = this.audioContext.createGain()
    this.gainNode.gain.value = 0.7
    this.gainNode.connect(this.audioContext.destination)
  }

  setOnQueueEmpty(callback: () => void): void {
    this.onQueueEmptyCallback = callback
  }

  enqueue(pcm16: Int16Array): void {
    this.queue.push(pcm16)
    this.schedule()
  }

  private schedule(): void {
    const currentTime = this.audioContext.currentTime

    if (this.nextStartTime === 0) {
      this.nextStartTime = currentTime + this.startDelaySeconds
    }

    const scheduleUntil = currentTime + this.lookaheadSeconds
    let scheduledAny = false

    while (this.queue.length > 0 && this.nextStartTime < scheduleUntil) {
      const pcm16 = this.queue.shift()!

      const float24k = pcm16ToFloat32(pcm16)
      const targetSampleRate = this.audioContext.sampleRate

      let samples = float24k
      let bufferSampleRate = 24000

      if (targetSampleRate !== 24000) {
        if (!this.hasLoggedResample) {
          if (targetSampleRate === 48000) {
            console.log('Resampling 24kHz→48kHz')
          } else {
            console.log(`Resampling 24kHz→${Math.round(targetSampleRate / 1000)}kHz`)
          }
          this.hasLoggedResample = true
        }

        samples = resampleLinear(float24k, 24000, targetSampleRate)
        bufferSampleRate = targetSampleRate
      }

      const audioBuffer = this.audioContext.createBuffer(1, samples.length, bufferSampleRate)
      audioBuffer.copyToChannel(samples, 0)

      const source = this.audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(this.gainNode)

      const startTime = Math.max(currentTime, this.nextStartTime)
      source.start(startTime)

      this.scheduledSources.add(source)
      this.nextStartTime = startTime + audioBuffer.duration
      scheduledAny = true

      source.onended = () => {
        this.scheduledSources.delete(source)
        this.schedule()
        this.maybeNotifyQueueEmpty()
      }
    }

    if (scheduledAny && !this.hasLoggedScheduler) {
      console.log('Audio scheduler lookahead OK (sin gaps)')
      this.hasLoggedScheduler = true
    }

    this.maybeNotifyQueueEmpty()
  }

  private maybeNotifyQueueEmpty(): void {
    if (this.queue.length !== 0) return
    if (this.scheduledSources.size !== 0) return

    this.nextStartTime = 0
    if (this.onQueueEmptyCallback) {
      this.onQueueEmptyCallback()
    }
  }

  clear(): void {
    this.queue = []
    this.nextStartTime = 0
    for (const source of this.scheduledSources) {
      try {
        source.stop()
      } catch {
        // ignore
      }
    }
    this.scheduledSources.clear()
  }

  getIsPlaying(): boolean {
    return this.queue.length > 0 || this.scheduledSources.size > 0
  }
}

// Instancia global de la cola (será gestionada por el componente)
let globalAudioQueue: AudioQueue | null = null

/**
 * Inicializa la cola de audio global
 */
export function initAudioQueue(audioContext: AudioContext): void {
  globalAudioQueue = new AudioQueue(audioContext)
}

/**
 * Reproduce audio PCM16 usando cola secuencial
 */
export function playPCM16Audio(
  pcm16: Int16Array,
  audioContext: AudioContext
): void {
  if (!globalAudioQueue) {
    globalAudioQueue = new AudioQueue(audioContext)
  }
  globalAudioQueue.enqueue(pcm16)
}

/**
 * Limpia la cola de audio (para interrupciones)
 */
export function clearAudioQueue(): void {
  if (globalAudioQueue) {
    globalAudioQueue.clear()
  }
}

/**
 * Configura callback para cuando la cola esté vacía
 */
export function setAudioQueueEmptyCallback(callback: () => void): void {
  if (globalAudioQueue) {
    globalAudioQueue.setOnQueueEmpty(callback)
  }
}

/**
 * Verifica si la cola está reproduciendo
 */
export function isAudioQueuePlaying(): boolean {
  return globalAudioQueue?.getIsPlaying() || false
}
