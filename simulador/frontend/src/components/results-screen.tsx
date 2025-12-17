import {
  CheckCircle2,
  XCircle,
  Award,
  Clock,
  Download,
  Home,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { UMHLogo } from "@/components/umh-logo"
import type { CaseData, StudentData, ChecklistResult } from "@/types"
import { useState } from "react"

interface ResultsScreenProps {
  caseData: CaseData
  studentData: StudentData
  evaluationResults: any | null
  onBackToDashboard: () => void
  onGoToSurvey: () => void
}

export function ResultsScreen({ caseData, studentData, evaluationResults, onBackToDashboard, onGoToSurvey }: ResultsScreenProps) {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    principal: true,
    diferencial: true,
    screening: true,
  })
  const [expandedReflections, setExpandedReflections] = useState<Record<string, boolean>>({})

  // Datos de evaluación
  const overallScore = evaluationResults?.overall_score || 0
  const clinicalReasoningScore = evaluationResults?.clinical_reasoning_score || 0
  const communicationScore = evaluationResults?.communication_score || 0
  const strengths = evaluationResults?.strengths || []
  const areasForImprovement = evaluationResults?.areas_for_improvement || []
  const feedback = evaluationResults?.feedback || ""

  // Checklists por categoría
  const checklistPrincipal: ChecklistResult = evaluationResults?.checklist_principal || {
    items_completed: [],
    items_missed: [],
    percentage: 0,
    total_items: 0,
  }

  const checklistDiferencial: ChecklistResult = evaluationResults?.checklist_diferencial || {
    items_completed: [],
    items_missed: [],
    percentage: 0,
    total_items: 0,
  }

  const checklistScreening: ChecklistResult = evaluationResults?.checklist_screening || {
    items_completed: [],
    items_missed: [],
    percentage: 0,
    total_items: 0,
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({ ...prev, [category]: !prev[category] }))
  }

  const toggleReflection = (key: string) => {
    setExpandedReflections((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const percentage = Math.round(overallScore)

  const getGrade = (percent: number) => {
    if (percent >= 90) return { grade: "A", label: "Sobresaliente", color: "text-success" }
    if (percent >= 80) return { grade: "B", label: "Notable", color: "text-success" }
    if (percent >= 70) return { grade: "C", label: "Bien", color: "text-warning-foreground" }
    if (percent >= 60) return { grade: "D", label: "Suficiente", color: "text-warning-foreground" }
    return { grade: "F", label: "Insuficiente", color: "text-destructive" }
  }

  const gradeInfo = getGrade(percentage)

  // Total de items
  const totalCompleted = checklistPrincipal.items_completed.length +
                         checklistDiferencial.items_completed.length +
                         checklistScreening.items_completed.length
  const totalMissed = checklistPrincipal.items_missed.length +
                      checklistDiferencial.items_missed.length +
                      checklistScreening.items_missed.length

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <UMHLogo />
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Descargar PDF
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Score Header */}
        <div className="bg-card rounded-2xl p-8 border border-border mb-8 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-4">
            <Award className="w-10 h-10 text-primary" />
          </div>

          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">¡Simulación completada!</h1>

          <p className="text-muted-foreground mb-6">
            {studentData.nombre} - {caseData.title}
          </p>

          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <div className={`text-5xl md:text-6xl font-bold ${gradeInfo.color}`}>{gradeInfo.grade}</div>
              <div className="text-sm text-muted-foreground mt-1">{gradeInfo.label}</div>
            </div>

            <div className="h-20 w-px bg-border" />

            <div className="text-center">
              <div className="text-5xl md:text-6xl font-bold text-foreground">{percentage}%</div>
              <div className="text-sm text-muted-foreground mt-1">Puntuación general</div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <CheckCircle2 className="w-6 h-6 text-success mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{totalCompleted}</div>
            <div className="text-xs text-muted-foreground">Ítems completados</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <XCircle className="w-6 h-6 text-destructive mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{totalMissed}</div>
            <div className="text-xs text-muted-foreground">Ítems no completados</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <Clock className="w-6 h-6 text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{clinicalReasoningScore}%</div>
            <div className="text-xs text-muted-foreground">Razonamiento clínico</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <Award className="w-6 h-6 text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{communicationScore}%</div>
            <div className="text-xs text-muted-foreground">Comunicación</div>
          </div>
        </div>

        {/* Checklist Categories */}
        <div className="space-y-4 mb-8">
          {/* Motivo de Consulta Principal */}
          <ChecklistCategory
            title="Motivo de Consulta Principal"
            checklist={checklistPrincipal}
            isExpanded={expandedCategories.principal}
            onToggle={() => toggleCategory('principal')}
          />

          {/* Diagnóstico Diferencial */}
          <ChecklistCategory
            title="Diagnóstico Diferencial"
            checklist={checklistDiferencial}
            isExpanded={expandedCategories.diferencial}
            onToggle={() => toggleCategory('diferencial')}
          />

          {/* Screening */}
          <ChecklistCategory
            title="Screening y Contexto"
            checklist={checklistScreening}
            isExpanded={expandedCategories.screening}
            onToggle={() => toggleCategory('screening')}
          />
        </div>

        {/* Reflexión Clínica */}
        {evaluationResults?.reflection_evaluation && (
          <div className="bg-card rounded-2xl border border-border overflow-hidden mb-8">
            <div className="p-6 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Reflexión Clínica</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Evaluación de tus respuestas escritas
              </p>
            </div>

            <div className="divide-y divide-border">
              {Object.entries(evaluationResults.reflection_evaluation).map(([key, value]: [string, any]) => (
                <ReflectionItem
                  key={key}
                  question={value.question}
                  studentAnswer={value.student_answer}
                  feedback={value.feedback}
                  score={value.score}
                  maxScore={value.max_score}
                  isExpanded={expandedReflections[key] || false}
                  onToggle={() => toggleReflection(key)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Feedback General */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Strengths */}
          <div className="bg-card rounded-2xl border border-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-success" />
              <h3 className="font-semibold text-foreground">Fortalezas</h3>
            </div>
            <ul className="space-y-2">
              {strengths.map((strength: string, index: number) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-success mt-1">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Areas for Improvement */}
          <div className="bg-card rounded-2xl border border-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-5 h-5 text-warning-foreground" />
              <h3 className="font-semibold text-foreground">Áreas de Mejora</h3>
            </div>
            <ul className="space-y-2">
              {areasForImprovement.map((area: string, index: number) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-warning-foreground mt-1">•</span>
                  <span>{area}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Feedback Message */}
        {feedback && (
          <div className="bg-card rounded-2xl border border-border p-6 mb-8">
            <h3 className="font-semibold text-foreground mb-3">Comentario del Evaluador</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{feedback}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button variant="outline" onClick={onBackToDashboard}>
            <Home className="w-4 h-4 mr-2" />
            Volver al Inicio
          </Button>
          <Button onClick={onGoToSurvey}>
            Continuar a Encuesta
          </Button>
        </div>
      </div>
    </div>
  )
}

// Componente para cada categoría de checklist
function ChecklistCategory({
  title,
  checklist,
  isExpanded,
  onToggle
}: {
  title: string
  checklist: ChecklistResult
  isExpanded: boolean
  onToggle: () => void
}) {
  return (
    <div className="bg-card rounded-2xl border border-border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-6 flex items-center justify-between hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="text-left">
            <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {checklist.items_completed.length} de {checklist.total_items} completados ({Math.round(checklist.percentage)}%)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Progress value={checklist.percentage} className="w-24 h-2" />
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-border">
          {/* Items Completados */}
          {checklist.items_completed.length > 0 && (
            <div className="p-6 border-b border-border">
              <h4 className="text-sm font-medium text-success mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Completados
              </h4>
              <ul className="space-y-2">
                {checklist.items_completed.map((item: string, index: number) => (
                  <li key={index} className="text-sm text-muted-foreground flex items-start gap-2 pl-6">
                    <CheckCircle2 className="w-4 h-4 text-success mt-0.5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Items No Completados */}
          {checklist.items_missed.length > 0 && (
            <div className="p-6">
              <h4 className="text-sm font-medium text-destructive mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                No completados
              </h4>
              <ul className="space-y-2">
                {checklist.items_missed.map((item: string, index: number) => (
                  <li key={index} className="text-sm text-muted-foreground flex items-start gap-2 pl-6">
                    <XCircle className="w-4 h-4 text-destructive mt-0.5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Componente para cada ítem de reflexión
function ReflectionItem({
  question,
  studentAnswer,
  feedback,
  score,
  maxScore,
  isExpanded,
  onToggle,
}: {
  question: string
  studentAnswer: string
  feedback: string
  score: number
  maxScore: number
  isExpanded: boolean
  onToggle: () => void
}) {
  const percentage = (score / maxScore) * 100

  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full p-6 flex items-center justify-between hover:bg-accent/50 transition-colors text-left"
      >
        <div className="flex-1">
          <h4 className="font-medium text-foreground mb-1">{question}</h4>
          <p className="text-sm text-muted-foreground line-clamp-2">{studentAnswer}</p>
        </div>
        <div className="flex items-center gap-4 ml-4">
          <Badge variant={percentage >= 60 ? "default" : "destructive"}>
            {score}/{maxScore}
          </Badge>
          {isExpanded ? <ChevronUp className="w-5 h-5 shrink-0" /> : <ChevronDown className="w-5 h-5 shrink-0" />}
        </div>
      </button>

      {isExpanded && (
        <div className="px-6 pb-6 space-y-4">
          <div>
            <h5 className="text-sm font-medium text-foreground mb-2">Tu respuesta:</h5>
            <p className="text-sm text-muted-foreground leading-relaxed bg-accent/30 rounded-lg p-4">
              {studentAnswer}
            </p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-foreground mb-2">Feedback:</h5>
            <p className="text-sm text-muted-foreground leading-relaxed bg-primary/5 rounded-lg p-4 border border-primary/20">
              {feedback}
            </p>
          </div>
          <Progress value={percentage} className="h-2" />
        </div>
      )}
    </div>
  )
}
