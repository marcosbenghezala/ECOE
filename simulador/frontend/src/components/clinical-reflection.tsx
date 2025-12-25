import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { UMHLogo } from "@/components/umh-logo"
import { FileText, Lock } from "lucide-react"

interface ClinicalReflectionProps {
  onSubmit: (reflectionData: any) => void
  questions?: any[]
}

export function ClinicalReflection({ onSubmit, questions: propQuestions }: ClinicalReflectionProps) {
  const questions = (propQuestions || []).map((q, idx) => ({
    ...q,
    id: q.id ?? idx + 1,
  }))
  const [answers, setAnswers] = useState<Record<number, string>>({})

  const handleAnswerChange = (questionId: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.id]?.trim())

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center">
          <UMHLogo />
        </div>
      </header>

      {/* Content */}
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        <Card className="border-border">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <FileText className="w-6 h-6 text-primary" />
            </div>
            <CardTitle className="text-2xl">Reflexión Clínica sobre el Caso</CardTitle>
            <CardDescription className="text-base mt-2">
              Estas preguntas buscan valorar tu razonamiento y comprensión clínica del caso trabajado.
            </CardDescription>
            <div className="flex items-center justify-center gap-2 mt-4 text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
              <Lock className="w-4 h-4" />
              <span>
                Todas las respuestas son confidenciales y se usarán solo con finalidad docente e investigadora.
              </span>
            </div>
          </CardHeader>

          <CardContent className="space-y-6 pt-6">
            {questions.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                No hay preguntas configuradas para este caso.
              </div>
            ) : (
              questions.map((q) => (
                <div key={q.id} className="space-y-3">
                  <Label htmlFor={`question-${q.id}`} className="text-base font-medium leading-relaxed">
                    {q.id}. {q.question}
                  </Label>
                  <Textarea
                    id={`question-${q.id}`}
                    placeholder="Escribe tu respuesta aquí..."
                    value={answers[q.id] || ""}
                    onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                    className="min-h-[120px] resize-none"
                  />
                </div>
              ))
            )}

            {/* Submit Button */}
            <div className="pt-4">
              <Button
                onClick={() => {
                  // Construir objeto de respuestas usando field_name de cada pregunta
                  const reflectionData: Record<string, string> = {}
                  questions.forEach((q) => {
                    const fieldName = q.field_name || `pregunta_${q.id}`
                    reflectionData[fieldName] = answers[q.id] || ''
                  })
                  onSubmit(reflectionData)
                }}
                disabled={!allAnswered}
                className="w-full"
                size="lg"
              >
                Enviar reflexiones y continuar
              </Button>
              {questions.length > 0 && !allAnswered && (
                <p className="text-sm text-muted-foreground text-center mt-2">
                  Por favor, responde todas las preguntas para continuar.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
