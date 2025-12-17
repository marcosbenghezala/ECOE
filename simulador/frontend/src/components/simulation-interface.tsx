import type React from "react"

import { useState, useEffect, useRef } from "react"
import {
  Mic,
  MicOff,
  Square,
  ImageIcon,
  X,
  ZoomIn,
  ZoomOut,
  Play,
  Pause,
  Volume2,
  FileVideo,
  Music,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { UMHLogo } from "@/components/umh-logo"
import { ParticleCircle } from "@/components/particle-circle"
import { float32ToPCM16, arrayBufferToBase64, base64ToPCM16, playPCM16Audio, initAudioQueue, clearAudioQueue, setAudioQueueEmptyCallback, isAudioQueuePlaying } from '@/lib/pcm16';
import type { CaseData } from "@/types"

interface SimulationInterfaceProps {
  caseData: CaseData
  sessionId: string
  onEnd: () => void
}

type SimulationState = "idle" | "listening" | "processing" | "speaking"

const WS_URL = import.meta.env.VITE_API_URL?.replace('http', 'ws') || "ws://localhost:8080"

type MediaType = "image" | "audio" | "video"

interface MediaItem {
  id: string
  type: MediaType
  title: string
  description: string
  src: string
}

export function SimulationInterface({ caseData, sessionId, onEnd }: SimulationInterfaceProps) {
  const [state, setState] = useState<SimulationState>("idle")
  const [isMuted, setIsMuted] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const [mediaStack, setMediaStack] = useState<MediaItem[]>([])
  const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isStackHovered, setIsStackHovered] = useState(false)

  const [audioLevel, setAudioLevel] = useState(0)

  const [autoShowTimeout, setAutoShowTimeout] = useState<NodeJS.Timeout | null>(null)
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const imageContainerRef = useRef<HTMLDivElement>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const responseInProgressRef = useRef(false)
  const [micBlocked, setMicBlocked] = useState(false)
  const [micRetryToken, setMicRetryToken] = useState(0)
  const [audioContextState, setAudioContextState] = useState("")

  // Conectar WebSocket para Realtime API con timeout y retry
  useEffect(() => {
    let connectionTimeout: NodeJS.Timeout | null = null
    let retryCount = 0
    const MAX_RETRIES = 3
    const TIMEOUT_MS = 15000

    const connectWebSocket = () => {
      console.log(`🔌 Conectando WebSocket (intento ${retryCount + 1}/${MAX_RETRIES + 1})`)

      const ws = new WebSocket(`${WS_URL}/ws/realtime/${sessionId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('🔌 WebSocket abierto, esperando OpenAI...')
        setError(null)

        // ⏱️ Timeout de 15s para recibir "connected"
        connectionTimeout = setTimeout(() => {
          if (!wsConnected) {
            console.error('❌ Timeout: No se recibió "connected" en 15s')
            ws.close()

            if (retryCount < MAX_RETRIES) {
              retryCount++
              console.log(`🔄 Reintentando en 2s... (${retryCount}/${MAX_RETRIES})`)
              setTimeout(connectWebSocket, 2000)
            } else {
              setError(
                `No se pudo conectar después de ${MAX_RETRIES + 1} intentos.\n\n` +
                  `Verifica:\n` +
                  `1. Conexión a internet activa\n` +
                  `2. API key de OpenAI con créditos\n` +
                  `3. No estás en red que bloquee WebSocket\n\n` +
                  `Contacta al administrador si persiste.`,
              )
            }
          }
        }, TIMEOUT_MS)
      }

      ws.onmessage = (event) => {
        try {
          if (typeof event.data === 'string') {
            const message = JSON.parse(event.data)
            console.log('📩 Mensaje:', message.type)

            if (message.type === 'connected') {
              console.log('✅ OpenAI Realtime API conectada')
              if (connectionTimeout) {
                clearTimeout(connectionTimeout)
                connectionTimeout = null
              }
              retryCount = 0
              responseInProgressRef.current = false
              setWsConnected(true)
              setState('idle')
            } else if (message.type === 'session.created') {
              console.log('✅ Sesión creada')
            } else if (message.type === 'response.audio.delta' || message.type === 'agent_audio') {
              responseInProgressRef.current = true
              // Reproducir audio del agente
              if (message.audio && audioContextRef.current) {
                try {
                  const pcm16 = base64ToPCM16(message.audio)
                  playPCM16Audio(pcm16, audioContextRef.current)
                  console.log(`🔊 Reproduciendo audio (${pcm16.length} samples)`)
                } catch (err) {
                  console.error('❌ Error reproduciendo audio:', err)
                }
              }
              setState('speaking')
            } else if (message.type === 'response.done' || message.type === 'response_done') {
              // "done" significa que no llegarán más chunks, pero el audio puede seguir reproduciéndose.
              responseInProgressRef.current = false
              if (!isAudioQueuePlaying()) {
                setState('idle')
              }
            } else if (message.type === 'conversation.item.input_audio_transcription.completed') {
              console.log('📝 Transcripción:', message.transcript)
            } else if (message.type === 'transcript_update') {
              console.log('📝 Transcript:', message.text)
            } else if (message.type === 'error') {
              console.error('❌ Error backend:', message.error)
              setError(typeof message.error === 'string' ? message.error : message.error?.message || 'Error en la API')
              setWsConnected(false)
              if (connectionTimeout) {
                clearTimeout(connectionTimeout)
                connectionTimeout = null
              }
            }
          }
        } catch (err) {
          console.error('❌ Error parsing message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        setError('Error de conexión con el servidor')
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }
      }

      ws.onclose = () => {
        console.log('🔌 WebSocket cerrado')
        setWsConnected(false)
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }
      }
    }

    // Iniciar conexión
    connectWebSocket()

    return () => {
      if (connectionTimeout) {
        clearTimeout(connectionTimeout)
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
    }
  }, [sessionId])

  // Inicializar AudioContext para reproducir audio del paciente
  useEffect(() => {
    audioContextRef.current = new AudioContext({ sampleRate: 24000 })
    initAudioQueue(audioContextRef.current)

    // Configurar callback para cuando termine de reproducir audio
    setAudioQueueEmptyCallback(() => {
      // Solo pasar a idle cuando ya no queda audio por reproducir y el modelo ya terminó de emitir audio.
      if (responseInProgressRef.current) return
      setState('idle')
      console.log('🔊 Audio terminado - estado: idle')
    })

    console.log('🔊 AudioContext y cola de audio inicializados')

    return () => {
      clearAudioQueue()
      if (audioContextRef.current) {
        audioContextRef.current.close()
        console.log('🔊 AudioContext cerrado')
      }
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Conectar micrófono y enviar audio PCM16 al WebSocket (auto-start + fallback)
  useEffect(() => {
    let mediaStream: MediaStream | null = null
    let audioContext: AudioContext | null = null
    let audioProcessor: AudioWorkletNode | null = null
    let analyser: AnalyserNode | null = null
    let animationFrameId: number | null = null

    async function setupAudio() {
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 24000,
          },
        })

        console.log("🎤 getUserMedia OK", {
          tracks: mediaStream.getAudioTracks().map((t) => ({
            label: t.label,
            enabled: t.enabled,
            muted: t.muted,
            readyState: t.readyState,
            settings: t.getSettings ? t.getSettings() : {},
          })),
        })

        audioContext = new AudioContext({ sampleRate: 24000 })
        setAudioContextState(audioContext.state)
        audioContext.onstatechange = () => {
          setAudioContextState(audioContext?.state || "")
          console.log("🔈 AudioContext state change", audioContext?.state)
        }
        if (audioContext.state === "suspended") {
          await audioContext.resume().catch((e) => console.warn("⚠️ No se pudo resumir AudioContext", e))
        }

        const source = audioContext.createMediaStreamSource(mediaStream)

        mediaStream.getAudioTracks().forEach((track) => {
          track.onended = () => console.warn("🎤 Track ended, reintentar captura")
        })

        analyser = audioContext.createAnalyser()
        analyser.fftSize = 256
        source.connect(analyser)

        const bufferLength = analyser.frequencyBinCount
        const dataArray = new Uint8Array(bufferLength)

        try {
          await audioContext.audioWorklet.addModule("/audio-processor-worklet.js")

          audioProcessor = new AudioWorkletNode(audioContext, "audio-capture-processor")

          audioProcessor.port.onmessage = (event) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

            const samples = event.data.samples as Float32Array
            const pcm16 = float32ToPCM16(samples)
            const audioB64 = arrayBufferToBase64(pcm16.buffer)

            wsRef.current.send(
              JSON.stringify({
                type: "audio",
                audio: audioB64,
              }),
            )
          }

          source.connect(audioProcessor)
          console.log("✅ AudioWorklet PCM16 configurado")
        } catch (workletError) {
          console.error("AudioWorklet no disponible, usando ScriptProcessor fallback:", workletError)

          const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1)

          scriptProcessor.onaudioprocess = (event) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

            const inputData = event.inputBuffer.getChannelData(0)
            const pcm16 = float32ToPCM16(inputData)
            const audioB64 = arrayBufferToBase64(pcm16.buffer)

            wsRef.current.send(
              JSON.stringify({
                type: "audio",
                audio: audioB64,
              }),
            )
          }

          source.connect(scriptProcessor)
          scriptProcessor.connect(audioContext.destination)
          console.log("⚠️  Usando ScriptProcessor (fallback)")
        }

        function updateAudioLevel() {
          if (!analyser) return

          analyser.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length
          const normalizedLevel = average / 255

          setAudioLevel(normalizedLevel)

          animationFrameId = requestAnimationFrame(updateAudioLevel)
        }

        updateAudioLevel()
        console.log("🎤 Micrófono conectado - enviando PCM16")
        setMicBlocked(false)
      } catch (err: any) {
        console.error("❌ getUserMedia error", err?.name, err?.message)
        setError("No se pudo acceder al micrófono. Verifica los permisos.")
        setMicBlocked(true)
      }
    }

    if (!isMuted && wsConnected) {
      setupAudio()
    } else {
      console.log("⏸️ Captura de micro no iniciada (isMuted/wsConnected)", { isMuted, wsConnected })
    }

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
      if (audioProcessor) {
        audioProcessor.disconnect()
      }
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => {
          console.log("🛑 Parando track", { label: track.label, readyState: track.readyState })
          track.stop()
        })
      }
      if (audioContext) {
        audioContext.close()
        console.log("🔊 AudioContext cerrado")
      }
    }
  }, [isMuted, wsConnected, micRetryToken])

  useEffect(() => {
    if (wsConnected) {
      console.log("🌐 WS conectado, listo para iniciar captura si no está muteado")
    }
  }, [wsConnected])

  useEffect(() => {
    let interval: NodeJS.Timeout

    if (state === "speaking") {
      interval = setInterval(() => {
        setAudioLevel(0.3 + Math.random() * 0.7)
      }, 100)
    } else if (state === "listening") {
      interval = setInterval(() => {
        setAudioLevel(0.1 + Math.random() * 0.3)
      }, 150)
    } else {
      setAudioLevel(0)
    }

    return () => clearInterval(interval)
  }, [state])

  // Multimedia de prueba desactivada - usar solo multimedia real del caso
  // useEffect(() => {
  //   const timeouts: NodeJS.Timeout[] = []
  //   timeouts.push(
  //     setTimeout(() => {
  //       setMediaStack((prev) => [...prev, { id: "1", type: "image", title: "Radiografía de tórax", description: "Vista anteroposterior", src: "/chest-xray-medical.jpg" }])
  //     }, 8000)
  //   )
  //   return () => timeouts.forEach((t) => clearTimeout(t))
  // }, [])

  useEffect(() => {
    if (mediaStack.length > 0) {
      const latestMedia = mediaStack[mediaStack.length - 1]

      // Only auto-show if we just added a new item and nothing is currently selected
      if (!selectedMedia || selectedMedia.id !== latestMedia.id) {
        // Clear any existing timeout
        if (autoShowTimeout) {
          clearTimeout(autoShowTimeout)
        }

        // Auto-show the new media
        setSelectedMedia(latestMedia)
        setZoomLevel(1)
        setPanPosition({ x: 0, y: 0 })
        setIsPlaying(false)

        // Auto-close after 5 seconds
        const timeout = setTimeout(() => {
          setSelectedMedia(null)
          setZoomLevel(1)
          setPanPosition({ x: 0, y: 0 })
          setIsStackHovered(false)
        }, 5000)

        setAutoShowTimeout(timeout)
      }
    }
  }, [mediaStack])

  useEffect(() => {
    return () => {
      if (autoShowTimeout) {
        clearTimeout(autoShowTimeout)
      }
    }
  }, [autoShowTimeout])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  const getStateText = () => {
    switch (state) {
      case "listening":
        return "Escuchando..."
      case "speaking":
        return "Hablando..."
      case "processing":
        return "Procesando..."
      default:
        return "Listo para hablar"
    }
  }

  const getSpeakerState = (): "idle" | "user" | "agent" => {
    switch (state) {
      case "listening":
        return "user"
      case "speaking":
        return "agent"
      default:
        return "idle"
    }
  }

  const handleSelectMedia = (media: MediaItem) => {
    if (autoShowTimeout) {
      clearTimeout(autoShowTimeout)
      setAutoShowTimeout(null)
    }
    setSelectedMedia(media)
    setZoomLevel(1)
    setPanPosition({ x: 0, y: 0 })
    setIsPlaying(false)
  }

  const handleCloseMedia = () => {
    if (autoShowTimeout) {
      clearTimeout(autoShowTimeout)
      setAutoShowTimeout(null)
    }
    setSelectedMedia(null)
    setZoomLevel(1)
    setPanPosition({ x: 0, y: 0 })
    setIsPlaying(false)
    setIsStackHovered(false)
  }

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 3))
  }

  const handleZoomOut = () => {
    setZoomLevel((prev) => {
      const newZoom = Math.max(prev - 0.25, 1)
      if (newZoom === 1) {
        setPanPosition({ x: 0, y: 0 })
      }
      return newZoom
    })
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - panPosition.x, y: e.clientY - panPosition.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1) {
      const newX = e.clientX - dragStart.x
      const newY = e.clientY - dragStart.y

      // Limit pan based on zoom level
      const maxPan = (zoomLevel - 1) * 150
      setPanPosition({
        x: Math.max(-maxPan, Math.min(maxPan, newX)),
        y: Math.max(-maxPan, Math.min(maxPan, newY)),
      })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handleMouseLeave = () => {
    setIsDragging(false)
  }

  const getMediaIcon = (type: MediaType) => {
    switch (type) {
      case "image":
        return <ImageIcon className="w-4 h-4" />
      case "audio":
        return <Music className="w-4 h-4" />
      case "video":
        return <FileVideo className="w-4 h-4" />
    }
  }

  const getMediaThumbnail = (media: MediaItem) => {
    switch (media.type) {
      case "image":
        return <img src={media.src} alt={media.title} className="w-full h-full object-cover" />
      case "audio":
        return (
          <div className="w-full h-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center">
            <Volume2 className="w-6 h-6 text-primary" />
          </div>
        )
      case "video":
        return (
          <div className="w-full h-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center">
            <Play className="w-6 h-6 text-primary" />
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-20 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <UMHLogo />
          <div className="flex items-center gap-4">
            <div className="text-sm text-muted-foreground font-mono">{formatTime(elapsedTime)}</div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowEndConfirm(true)}
              className="bg-primary hover:bg-primary/90"
            >
              <Square className="w-3 h-3 mr-2 fill-current" />
              Finalizar caso
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        {/* Case info - fixed at top */}
        <div className="absolute top-24 left-0 right-0 text-center pointer-events-none">
          <h2 className="text-lg font-medium text-muted-foreground mb-1">{caseData.category}</h2>
          <h1 className="text-xl md:text-2xl font-bold text-foreground">{caseData.title}</h1>
        </div>

        <div className="flex items-center justify-center">
          <ParticleCircle
            speaker={getSpeakerState()}
            audioLevel={audioLevel}
            className="w-[320px] h-[320px] md:w-[400px] md:h-[400px]"
          />
        </div>

        {/* State indicator */}
        <div className="flex items-center gap-2 mt-8 mb-4">
          <div
            className={`w-2 h-2 rounded-full transition-colors duration-300 ${
              state === "speaking"
                ? "bg-primary animate-pulse"
                : state === "listening"
                  ? "bg-primary/50 animate-pulse"
                  : state === "processing"
                    ? "bg-warning animate-pulse"
                    : "bg-muted"
            }`}
          />
          <span className="text-sm text-muted-foreground">{getStateText()}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          <Button
            variant={isMuted ? "destructive" : "outline"}
            size="lg"
            onClick={() => setIsMuted(!isMuted)}
            className={`rounded-full w-14 h-14 ${isMuted ? "bg-destructive hover:bg-destructive/90" : ""}`}
          >
            {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
          </Button>
        </div>

        {isMuted && <p className="text-sm text-destructive mt-4">Micrófono silenciado - haz clic para activar</p>}
        {(micBlocked || audioContextState === "suspended") && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-warning-foreground">
              Micrófono bloqueado o suspendido. Permite el acceso y reintenta activarlo.
            </p>
            <Button
              variant="default"
              onClick={() => setMicRetryToken((prev) => prev + 1)}
              className="bg-primary text-primary-foreground"
            >
              Activar micrófono
            </Button>
          </div>
        )}
      </div>

      {/* Media Stack - Card fan style in bottom right */}
      {mediaStack.length > 0 && !selectedMedia && (
        <div
          className="absolute bottom-6 right-6 z-30"
          onMouseEnter={() => setIsStackHovered(true)}
          onMouseLeave={() => setIsStackHovered(false)}
        >
          <div className="relative">
            {mediaStack.map((media, index) => {
              const totalCards = mediaStack.length
              const middleIndex = (totalCards - 1) / 2

              const baseRotation = (index - middleIndex) * 8
              const expandedSpacing = index * 70

              const rotation = isStackHovered ? 0 : baseRotation
              const translateX = isStackHovered ? -expandedSpacing : (index - middleIndex) * 4
              const translateY = isStackHovered ? 0 : Math.abs(index - middleIndex) * 3

              return (
                <button
                  key={media.id}
                  onClick={() => handleSelectMedia(media)}
                  className={`
                    absolute bottom-0 right-0
                    w-16 h-20 rounded-xl overflow-hidden
                    border-2 border-border bg-card
                    shadow-lg hover:shadow-xl
                    transition-all duration-300 ease-out
                    hover:border-primary hover:z-50
                    ${index === totalCards - 1 ? "animate-in slide-in-from-bottom-4 fade-in duration-500" : ""}
                  `}
                  style={{
                    transform: `
                      translateX(${translateX}px)
                      translateY(${translateY}px)
                      rotate(${rotation}deg)
                    `,
                    zIndex: isStackHovered ? index + 10 : totalCards - index,
                    transitionDelay: isStackHovered ? `${index * 30}ms` : `${(totalCards - index) * 30}ms`,
                  }}
                >
                  {getMediaThumbnail(media)}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />

                  {/* Media type icon */}
                  <div className="absolute bottom-1.5 left-1.5 p-1 bg-card/90 rounded-md shadow-sm">
                    {getMediaIcon(media.type)}
                  </div>

                  {/* New indicator pulse */}
                  {index === totalCards - 1 && (
                    <div className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-primary rounded-full animate-pulse shadow-lg shadow-primary/50" />
                  )}

                  {/* Hover label */}
                  <div
                    className={`
                    absolute -top-8 left-1/2 -translate-x-1/2
                    bg-foreground text-background text-xs px-2 py-1 rounded-md
                    whitespace-nowrap opacity-0 transition-opacity duration-200
                    pointer-events-none
                    ${isStackHovered ? "opacity-100" : ""}
                  `}
                  >
                    {media.title}
                  </div>
                </button>
              )
            })}

            {/* Stack count badge - only show when not hovered */}
            {mediaStack.length > 1 && !isStackHovered && (
              <div className="absolute -top-2 -left-2 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-bold z-50 shadow-lg animate-in zoom-in duration-200">
                {mediaStack.length}
              </div>
            )}

            {/* Hint text when hovered */}
            {isStackHovered && (
              <div className="absolute -top-8 right-0 text-xs text-muted-foreground animate-in fade-in duration-200">
                Selecciona para ver
              </div>
            )}
          </div>
        </div>
      )}

      {/* Media Viewer - Full panel on right side */}
      {selectedMedia && (
        <div className="absolute bottom-6 right-6 top-20 w-[400px] z-30 animate-in slide-in-from-right-4 fade-in duration-300">
          <div className="h-full bg-card rounded-2xl shadow-2xl border border-border flex flex-col overflow-hidden">
            {/* Media Header */}
            <div className="p-4 bg-muted/50 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg text-primary">{getMediaIcon(selectedMedia.type)}</div>
                <div>
                  <h3 className="font-semibold text-foreground text-sm">{selectedMedia.title}</h3>
                  <p className="text-xs text-muted-foreground">{selectedMedia.description}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="w-8 h-8 rounded-full hover:bg-destructive/10 hover:text-destructive"
                onClick={handleCloseMedia}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Media Content */}
            <div className="flex-1 relative overflow-hidden bg-muted/20 flex items-center justify-center p-4">
              {selectedMedia.type === "image" && (
                <div
                  ref={imageContainerRef}
                  className={`transition-transform duration-200 ease-out overflow-hidden ${
                    zoomLevel > 1 ? (isDragging ? "cursor-grabbing" : "cursor-grab") : "cursor-default"
                  }`}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseLeave}
                  style={{
                    transform: `scale(${zoomLevel}) translate(${panPosition.x / zoomLevel}px, ${panPosition.y / zoomLevel}px)`,
                  }}
                >
                  <img
                    src={selectedMedia.src}
                    alt={selectedMedia.title}
                    className="max-w-full max-h-full rounded-lg shadow-md select-none"
                    draggable={false}
                  />
                </div>
              )}

              {selectedMedia.type === "audio" && (
                <div className="w-full flex flex-col items-center gap-6 p-6">
                  <div
                    className={`w-32 h-32 bg-gradient-to-br from-primary/20 to-primary/40 rounded-full flex items-center justify-center transition-transform duration-300 ${isPlaying ? "scale-110" : ""}`}
                  >
                    <Volume2 className={`w-16 h-16 text-primary ${isPlaying ? "animate-pulse" : ""}`} />
                  </div>
                  <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                    <div
                      className={`bg-primary h-full rounded-full transition-all duration-300 ${isPlaying ? "animate-progress" : "w-0"}`}
                      style={{ width: isPlaying ? "33%" : "0%" }}
                    />
                  </div>
                  <Button
                    size="lg"
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="rounded-full w-14 h-14 bg-primary hover:bg-primary/90"
                  >
                    {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-1" />}
                  </Button>
                </div>
              )}

              {selectedMedia.type === "video" && (
                <div className="w-full h-full flex flex-col items-center justify-center gap-4">
                  <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden">
                    <img
                      src="/medical-ultrasound-video-thumbnail.jpg"
                      alt="Video thumbnail"
                      className={`w-full h-full object-cover transition-opacity duration-300 ${isPlaying ? "opacity-40" : "opacity-60"}`}
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Button
                        size="lg"
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="rounded-full w-16 h-16 bg-primary/90 hover:bg-primary"
                      >
                        {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />}
                      </Button>
                    </div>
                    {isPlaying && (
                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted">
                        <div className="bg-primary h-full animate-progress" style={{ width: "25%" }} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Zoom controls for images */}
              {selectedMedia.type === "image" && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-card/90 backdrop-blur-sm rounded-full p-1 shadow-lg border border-border">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-8 h-8 rounded-full"
                    onClick={handleZoomOut}
                    disabled={zoomLevel <= 1}
                  >
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <span className="text-xs font-medium w-12 text-center">{Math.round(zoomLevel * 100)}%</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-8 h-8 rounded-full"
                    onClick={handleZoomIn}
                    disabled={zoomLevel >= 3}
                  >
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                </div>
              )}

              {selectedMedia.type === "image" && zoomLevel > 1 && !isDragging && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground bg-card/80 backdrop-blur-sm px-3 py-1 rounded-full">
                  Arrastra para moverte por la imagen
                </div>
              )}
            </div>

            {/* Media thumbnails navigation */}
            <div className="p-3 bg-muted/50 border-t border-border">
              <div className="flex gap-2 overflow-x-auto pb-1">
                {mediaStack.map((media) => (
                  <button
                    key={media.id}
                    onClick={() => handleSelectMedia(media)}
                    className={`
                      flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden border-2 transition-all
                      ${selectedMedia.id === media.id ? "border-primary ring-2 ring-primary/30" : "border-border hover:border-primary/50"}
                    `}
                  >
                    {getMediaThumbnail(media)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* End Confirmation Modal */}
      {showEndConfirm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-2xl p-6 max-w-md w-full shadow-2xl border border-border animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-2">¿Finalizar el caso?</h3>
            <p className="text-muted-foreground mb-6">
              Una vez finalizado, no podrás volver a la simulación. Tu progreso será evaluado automáticamente.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 bg-transparent" onClick={() => setShowEndConfirm(false)}>
                Cancelar
              </Button>
              <Button className="flex-1 bg-primary hover:bg-primary/90" onClick={onEnd}>
                Finalizar caso
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
