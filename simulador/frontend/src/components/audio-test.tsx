import { useState } from "react"
import { Mic, Volume2, CheckCircle2, XCircle, ArrowRight, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { UMHLogo } from "@/components/umh-logo"

interface AudioTestProps {
  onComplete: () => void
  onBack: () => void
}

export function AudioTest({ onComplete, onBack }: AudioTestProps) {
  const [micTested, setMicTested] = useState<boolean | null>(null)
  const [speakerTested, setSpeakerTested] = useState<boolean | null>(null)
  const [isTesting, setIsTesting] = useState<"mic" | "speaker" | null>(null)

  const testMicrophone = async () => {
    setIsTesting("mic")
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Simulate recording test
      await new Promise((resolve) => setTimeout(resolve, 2000))
      stream.getTracks().forEach((track) => track.stop())
      setMicTested(true)
    } catch {
      setMicTested(false)
    }
    setIsTesting(null)
  }

  const testSpeaker = () => {
    setIsTesting("speaker")
    // Create audio context and play test tone
    const audioContext = new (
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    )()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    oscillator.frequency.value = 440
    gainNode.gain.value = 0.3

    oscillator.start()

    setTimeout(() => {
      oscillator.stop()
      audioContext.close()
      setSpeakerTested(true)
      setIsTesting(null)
    }, 1500)
  }

  const canContinue = micTested === true && speakerTested === true

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center">
          <UMHLogo />
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-xl">
          <div className="text-center mb-8">
            <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">Comprobación de Audio</h1>
            <p className="text-muted-foreground">
              Antes de comenzar, verifica que tu micrófono y altavoces funcionan correctamente
            </p>
          </div>

          <div className="space-y-6">
            {/* Microphone Test */}
            <div className="bg-card rounded-2xl p-6 border border-border">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      micTested === true ? "bg-success/10" : micTested === false ? "bg-destructive/10" : "bg-primary/10"
                    }`}
                  >
                    <Mic
                      className={`w-6 h-6 ${
                        micTested === true ? "text-success" : micTested === false ? "text-destructive" : "text-primary"
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">Micrófono</h3>
                    <p className="text-sm text-muted-foreground">
                      {isTesting === "mic"
                        ? "Probando micrófono..."
                        : micTested === null
                          ? "Haz clic para probar"
                          : micTested
                            ? "Micrófono funcionando"
                            : "Error: no se detectó micrófono"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {micTested === true && <CheckCircle2 className="w-6 h-6 text-success" />}
                  {micTested === false && <XCircle className="w-6 h-6 text-destructive" />}
                  <Button
                    variant={micTested === true ? "outline" : "default"}
                    onClick={testMicrophone}
                    disabled={isTesting !== null}
                    className={micTested !== true ? "bg-primary hover:bg-primary/90 text-primary-foreground" : ""}
                  >
                    {isTesting === "mic" ? (
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-primary-foreground rounded-full animate-pulse" />
                        Grabando...
                      </span>
                    ) : micTested === true ? (
                      "Repetir"
                    ) : (
                      "Probar"
                    )}
                  </Button>
                </div>
              </div>

              {isTesting === "mic" && (
                <div className="flex items-center justify-center gap-1 h-8">
                  {[...Array(12)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-primary rounded-full animate-voice-wave"
                      style={{
                        height: `${Math.random() * 24 + 8}px`,
                        animationDelay: `${i * 0.1}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Speaker Test */}
            <div className="bg-card rounded-2xl p-6 border border-border">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      speakerTested === true ? "bg-success/10" : "bg-primary/10"
                    }`}
                  >
                    <Volume2 className={`w-6 h-6 ${speakerTested === true ? "text-success" : "text-primary"}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">Altavoces</h3>
                    <p className="text-sm text-muted-foreground">
                      {isTesting === "speaker"
                        ? "Reproduciendo sonido de prueba..."
                        : speakerTested === null
                          ? "Haz clic para probar"
                          : "Altavoces funcionando"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {speakerTested === true && <CheckCircle2 className="w-6 h-6 text-success" />}
                  <Button
                    variant={speakerTested === true ? "outline" : "default"}
                    onClick={testSpeaker}
                    disabled={isTesting !== null}
                    className={speakerTested !== true ? "bg-primary hover:bg-primary/90 text-primary-foreground" : ""}
                  >
                    {isTesting === "speaker" ? (
                      <span className="flex items-center gap-2">
                        <Volume2 className="w-4 h-4 animate-pulse" />
                        Sonando...
                      </span>
                    ) : speakerTested === true ? (
                      "Repetir"
                    ) : (
                      "Probar"
                    )}
                  </Button>
                </div>
              </div>

              {isTesting === "speaker" && (
                <div className="flex items-center justify-center gap-1 h-8">
                  {[...Array(12)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-primary rounded-full animate-voice-wave"
                      style={{
                        height: `${Math.random() * 24 + 8}px`,
                        animationDelay: `${i * 0.1}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Status message */}
          {!canContinue && (micTested !== null || speakerTested !== null) && (
            <p className="text-center text-muted-foreground mt-6">
              {micTested === false
                ? "Por favor, permite el acceso al micrófono e inténtalo de nuevo"
                : "Completa ambas pruebas para continuar"}
            </p>
          )}

          <div className="flex gap-3 mt-8">
            <Button variant="outline" onClick={onBack} className="flex-1 h-12 text-base bg-transparent">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Volver
            </Button>
            <Button
              onClick={onComplete}
              disabled={!canContinue}
              className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground h-12 text-base disabled:opacity-50"
            >
              Continuar
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
