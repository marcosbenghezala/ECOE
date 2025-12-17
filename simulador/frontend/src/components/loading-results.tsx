import { useEffect, useState } from "react"
import { UMHLogo } from "@/components/umh-logo"

export function LoadingResults() {
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState("Analizando respuestas...")

  const messages = [
    "Analizando respuestas...",
    "Evaluando anamnesis...",
    "Revisando reflexión clínica...",
    "Comprobando diagnóstico diferencial...",
    "Calculando puntuación final...",
  ]

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) return 100
        return prev + Math.random() * 15
      })
    }, 500)

    const messageInterval = setInterval(() => {
      setMessage(messages[Math.floor(Math.random() * messages.length)])
    }, 1200)

    return () => {
      clearInterval(progressInterval)
      clearInterval(messageInterval)
    }
  }, [])

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
        <div className="w-full max-w-md text-center">
          {/* Animated loader */}
          <div className="relative w-32 h-32 mx-auto mb-8">
            {/* Outer ring */}
            <div className="absolute inset-0 rounded-full border-4 border-muted" />

            {/* Progress ring */}
            <svg className="absolute inset-0 w-full h-full -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="60"
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
                className="text-primary"
                style={{
                  strokeDasharray: `${2 * Math.PI * 60}`,
                  strokeDashoffset: `${2 * Math.PI * 60 * (1 - Math.min(progress, 100) / 100)}`,
                  transition: "stroke-dashoffset 0.5s ease",
                }}
              />
            </svg>

            {/* Center content */}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-foreground">{Math.min(Math.round(progress), 100)}%</span>
            </div>
          </div>

          <h2 className="text-xl font-bold text-foreground mb-2">Evaluando tu desempeño</h2>

          <p className="text-muted-foreground mb-6">{message}</p>

          {/* Loading dots */}
          <div className="flex items-center justify-center gap-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-primary animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
