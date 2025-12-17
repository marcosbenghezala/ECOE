import { useState } from "react"
import { Send, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { UMHLogo } from "@/components/umh-logo"

interface SurveyScreenProps {
  onComplete: () => void
  onSkip: () => void
}

const likertQuestions = [
  "Me ha gustado la experiencia general con el simulador de anamnesis.",
  "Me ha resultado fácil usar el sistema (voz, interfaz, navegación).",
  "Considero que este simulador me ayuda a mejorar mis habilidades de anamnesis.",
  "Me gustaría seguir usando esta herramienta para prepararme antes de ECOEs u otras prácticas clínicas.",
  "Confío en que la IA puede ser una herramienta útil en mi formación clínica.",
  "Creo que en el futuro los simuladores con IA serán habituales en la formación de estudiantes de medicina.",
  'Me siento cómodo interactuando con un "paciente" basado en IA.',
  "El feedback que he recibido (puntuaciones, comentarios) me ha ayudado a identificar errores o aspectos mejorables.",
]

const openQuestions = [
  "¿Qué es lo que más te ha aportado este simulador frente a otras formas de práctica (clases, lecturas, vídeos, pacientes estandarizados…)?",
  "Si pudieras cambiar o añadir solo una cosa al simulador para que fuera mucho más útil para ti, ¿qué sería y por qué?",
]

const likertLabels = [
  { value: "1", label: "Muy en desacuerdo" },
  { value: "2", label: "En desacuerdo" },
  { value: "3", label: "Neutral" },
  { value: "4", label: "De acuerdo" },
  { value: "5", label: "Muy de acuerdo" },
]

export function SurveyScreen({ onComplete, onSkip }: SurveyScreenProps) {
  const [likertAnswers, setLikertAnswers] = useState<Record<number, string>>({})
  const [openAnswers, setOpenAnswers] = useState<Record<number, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const allLikertAnswered = likertQuestions.every((_, idx) => likertAnswers[idx])
  const canSubmit = allLikertAnswered

  const handleSubmit = () => {
    setIsSubmitting(true)
    // Simular envío
    setTimeout(() => {
      setIsSubmitting(false)
      setIsSubmitted(true)
      setTimeout(() => {
        onComplete()
      }, 2000)
    }, 1500)
  }

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-success/10 mb-6">
            <CheckCircle2 className="w-10 h-10 text-success" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">¡Gracias por tu feedback!</h1>
          <p className="text-muted-foreground">Tu opinión nos ayuda a mejorar el simulador.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <UMHLogo />
          <Button variant="ghost" onClick={onSkip} className="text-muted-foreground">
            Ya he realizado esta encuesta
          </Button>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Encuesta de satisfacción</h1>
          <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            Este formulario forma parte de un Trabajo Fin de Grado de Medicina. Tus respuestas son{" "}
            <strong>completamente anónimas</strong> y se utilizarán únicamente con fines docentes y de investigación.
            Agradecemos tu colaboración.
          </p>
        </div>

        {/* Likert Questions */}
        <div className="bg-card rounded-2xl border border-border p-6 md:p-8 mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-6">Valora las siguientes afirmaciones</h2>
          <p className="text-sm text-muted-foreground mb-6">1 = Muy en desacuerdo, 5 = Muy de acuerdo</p>

          <div className="space-y-8">
            {likertQuestions.map((question, idx) => (
              <div key={idx} className="space-y-4">
                <Label className="text-foreground font-medium leading-relaxed">
                  {idx + 1}. {question}
                </Label>
                <RadioGroup
                  value={likertAnswers[idx] || ""}
                  onValueChange={(value) => setLikertAnswers((prev) => ({ ...prev, [idx]: value }))}
                  className="grid grid-cols-5 gap-2 md:gap-4"
                >
                  {likertLabels.map((option) => (
                    <div key={option.value} className="flex items-center">
                      <RadioGroupItem value={option.value} id={`q${idx}-${option.value}`} className="peer sr-only" />
                      <Label
                        htmlFor={`q${idx}-${option.value}`}
                        className="flex flex-col items-center justify-center w-full h-full min-h-[80px] md:min-h-[90px] px-2 py-3 rounded-xl border-2 border-border bg-background cursor-pointer transition-all hover:border-primary/50 peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5"
                      >
                        <span className="text-lg font-semibold text-foreground">{option.value}</span>
                        <span className="text-[10px] text-muted-foreground text-center hidden md:block">
                          {option.label}
                        </span>
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>
            ))}
          </div>
        </div>

        {/* Open Questions */}
        <div className="bg-card rounded-2xl border border-border p-6 md:p-8 mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-6">Preguntas abiertas</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Estas preguntas son opcionales pero muy valiosas para nosotros.
          </p>

          <div className="space-y-8">
            {openQuestions.map((question, idx) => (
              <div key={idx} className="space-y-3">
                <Label className="text-foreground font-medium leading-relaxed">
                  {idx + 9}. {question}
                </Label>
                <Textarea
                  value={openAnswers[idx] || ""}
                  onChange={(e) => setOpenAnswers((prev) => ({ ...prev, [idx]: e.target.value }))}
                  placeholder="Escribe tu respuesta aquí..."
                  className="min-h-[120px] resize-none bg-background"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex flex-col md:flex-row gap-4">
          <Button variant="outline" className="flex-1 bg-transparent" onClick={onSkip}>
            Omitir encuesta
          </Button>
          <Button
            className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={handleSubmit}
            disabled={!canSubmit || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-2" />
                Enviando...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Enviar encuesta
              </>
            )}
          </Button>
        </div>

        {!canSubmit && (
          <p className="text-sm text-muted-foreground text-center mt-4">
            Por favor, responde todas las preguntas de valoración (1-8) para enviar la encuesta.
          </p>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-border bg-card mt-8">
        <div className="max-w-3xl mx-auto px-6 py-6 text-center text-sm text-muted-foreground">
          © 2025 Universidad Miguel Hernández de Alicante - SimuPaciente
        </div>
      </footer>
    </div>
  )
}
