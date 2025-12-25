import {
  CheckCircle2,
  XCircle,
  Award,
  Download,
  Home,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  AlertCircle,
  FileText,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { UMHLogo } from "@/components/umh-logo"
import type { CaseData, StudentData } from "@/types"
import { useState } from "react"

interface ResultsScreenV3Props {
  caseData: CaseData
  studentData: StudentData
  evaluationResults: any | null
  onBackToDashboard: () => void
  onGoToSurvey: () => void
}

export function ResultsScreenV3({ caseData, studentData, evaluationResults, onBackToDashboard, onGoToSurvey }: ResultsScreenV3Props) {
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>({})
  const checklistMeta = evaluationResults?.checklist_meta || {}

  const percentage = Math.round(evaluationResults?.scores?.global?.percentage || 0)
  const pointsObtained = evaluationResults?.scores?.checklist?.score || 0
  const maxPointsCase = evaluationResults?.scores?.checklist?.max || 0
  const minPointsCase = checklistMeta?.min_points_required || 0
  const passed = percentage >= 60
  const blocksRaw = evaluationResults?.blocks || []

  const blocksList = Array.isArray(blocksRaw)
    ? blocksRaw
    : Object.entries(blocksRaw).map(([blockId, blockData]: [string, any]) => ({
        id: blockId,
        ...blockData,
      }))

  const summary = (() => {
    const totalItems = blocksList.reduce(
      (sum: number, block: any) => sum + ((block.items || []).length || 0),
      0
    )
    const matchedItems = blocksList.reduce(
      (sum: number, block: any) =>
        sum + (block.items || []).filter((item: any) => item.done).length,
      0
    )
    return {
      total_items_evaluated: totalItems,
      total_items_matched: matchedItems,
      match_rate: totalItems ? Math.round((matchedItems / totalItems) * 10) / 10 : 0,
    }
  })()

  const toggleBlock = (blockId: string) => {
    setExpandedBlocks((prev) => ({ ...prev, [blockId]: !prev[blockId] }))
  }

  const getGrade = (percent: number) => {
    if (percent >= 90) return { grade: "SB", label: "Sobresaliente", color: "text-success" }
    if (percent >= 80) return { grade: "NT", label: "Notable", color: "text-success" }
    if (percent >= 70) return { grade: "AP", label: "Aprobado", color: "text-warning-foreground" }
    if (percent >= 60) return { grade: "SF", label: "Suficiente", color: "text-warning-foreground" }
    return { grade: "SS", label: "Suspenso", color: "text-destructive" }
  }

  const gradeInfo = getGrade(percentage)

  // Mapeo de nombres de bloques
  const blockNames: Record<string, string> = {
    "B0_INTRODUCCION": "Introducción y Presentación",
    "B1_MOTIVO_CONSULTA": "Motivo de Consulta",
    "B2_HEA": "Historia de Enfermedad Actual",
    "B3_ANTECEDENTES": "Antecedentes Personales",
    "B4_MEDICACION_ALERGIAS": "Medicación y Alergias",
    "B5_SOCIAL": "Contexto Social",
    "B6_FAMILIAR": "Antecedentes Familiares",
    "B7_ANAMNESIS_APARATOS": "Anamnesis por Aparatos",
    "B8_CIERRE": "Cierre de la Entrevista",
    "B9_COMUNICACION": "Habilidades de Comunicación",
  }

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

          {/* Resultado aprobado/suspenso */}
          <div className="mt-6">
            <Badge variant={passed ? "default" : "destructive"} className="text-base px-6 py-2">
              {passed ? "✓ APROBADO" : "✗ SUSPENSO"}
            </Badge>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <TrendingUp className="w-6 h-6 text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{pointsObtained} / {maxPointsCase}</div>
            <div className="text-xs text-muted-foreground">Puntos obtenidos / máximos</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <CheckCircle2 className="w-6 h-6 text-success mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{summary.total_items_matched || 0} / {summary.total_items_evaluated || 0}</div>
            <div className="text-xs text-muted-foreground">Ítems cumplidos / total</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <Award className="w-6 h-6 text-warning-foreground mx-auto mb-2" />
            <div className="text-2xl font-bold text-foreground">{minPointsCase}</div>
            <div className="text-xs text-muted-foreground">Puntos mínimos (aprobado)</div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border text-center">
            <Award className={`w-6 h-6 mx-auto mb-2 ${passed ? 'text-success' : 'text-destructive'}`} />
            <div className={`text-2xl font-bold ${passed ? 'text-success' : 'text-destructive'}`}>
              {passed ? 'APTO' : 'NO APTO'}
            </div>
            <div className="text-xs text-muted-foreground">Resultado</div>
          </div>
        </div>

        {/* Bloques del Checklist */}
        <div className="space-y-4 mb-8">
          <h2 className="text-xl font-semibold text-foreground mb-4">Resultados por Bloque</h2>

          {blocksList.map((block: any) => {
            const blockId = block.id
            const blockItems = block.items || []

            return (
              <BlockResultCard
                key={blockId}
                blockId={blockId}
                blockName={block.name || blockNames[blockId] || blockId}
                blockData={block}
                blockItems={blockItems}
                isExpanded={expandedBlocks[blockId] || false}
                onToggle={() => toggleBlock(blockId)}
              />
            )
          })}
        </div>
        {/* Preguntas de Desarrollo */}
        {evaluationResults?.development?.questions?.length > 0 && (
          <DevelopmentQuestionsSection questions={evaluationResults.development.questions} />
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

// Componente para cada bloque
function BlockResultCard({
  blockId,
  blockName,
  blockData,
  blockItems,
  isExpanded,
  onToggle,
}: {
  blockId: string
  blockName: string
  blockData: any
  blockItems: any[]
  isExpanded: boolean
  onToggle: () => void
}) {
  const normalizedItems = (blockItems || []).map((item: any) => ({
    id: item.item_id || item.id,
    label: item.label || item.text || item.item_id || item.id,
    matched: item.matched ?? item.done ?? false,
    points: item.points ?? item.score ?? 0,
    maxPoints: item.max_score ?? item.max_points ?? 1,
  }))

  const percentage = blockData.percentage || 0
  const pointsObtained = blockData.score ?? 0
  const maxPoints = blockData.max ?? 0
  const itemsMatched = blockData.items_matched ?? normalizedItems.filter((item: any) => item.matched).length
  const itemsTotal = blockData.items_total ?? normalizedItems.length

  // Separar items cumplidos y no cumplidos
  const itemsCumplidos = normalizedItems.filter((item: any) => item.matched)
  const itemsNoCumplidos = normalizedItems.filter((item: any) => !item.matched)

  return (
    <div className="bg-card rounded-2xl border border-border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-6 flex items-center justify-between hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="text-left">
            <h3 className="text-lg font-semibold text-foreground">{blockName}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {itemsMatched} de {itemsTotal} ítems ({pointsObtained}/{maxPoints} pts)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Progress value={percentage} className="w-24 h-2" />
          <Badge variant={percentage >= 60 ? "default" : "outline"}>
            {Math.round(percentage)}%
          </Badge>
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-border p-6">
          {/* Lista de Ítems */}
          <div className="mt-4 space-y-3">
            {/* Ítems Cumplidos */}
            {itemsCumplidos.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-success mb-2 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  Ítems Cumplidos ({itemsCumplidos.length})
                </h4>
                <div className="space-y-1">
                  {itemsCumplidos.map((item: any) => (
                    <div key={item.id} className="flex items-start gap-2 text-sm bg-success/5 rounded p-2">
                      <CheckCircle2 className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="font-medium text-foreground">{item.label || item.id}</div>
                        <div className="text-xs text-muted-foreground">ID: {item.id}</div>
                      </div>
                      <Badge variant="outline" className="text-xs">{item.points} pts</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ítems No Cumplidos */}
            {itemsNoCumplidos.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-destructive mb-2 flex items-center gap-2">
                  <XCircle className="w-4 h-4" />
                  Ítems No Cumplidos ({itemsNoCumplidos.length})
                </h4>
                <div className="space-y-1">
                  {itemsNoCumplidos.map((item: any) => (
                    <div key={item.id} className="flex items-start gap-2 text-sm bg-destructive/5 rounded p-2">
                      <XCircle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="text-muted-foreground">{item.label || item.id}</div>
                        <div className="text-xs text-muted-foreground/70">ID: {item.id}</div>
                      </div>
                      <Badge variant="outline" className="text-xs opacity-50">{item.points} pts</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Componente para Preguntas de Desarrollo (con toggles)
function DevelopmentQuestionsSection({
  questions,
}: {
  questions?: any[]
}) {
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({})

  const toggleQuestion = (questionId: number) => {
    setExpandedQuestions((prev) => ({ ...prev, [questionId]: !prev[questionId] }))
  }

  const normalizedQuestions = questions?.length
    ? questions.map((q, idx) => ({
        id: idx + 1,
        title: q.question || q.titulo || `Pregunta ${idx + 1}`,
        answer: q.answer || q.respuesta || "",
        score: q.score || q.puntuacion || 0,
        feedback: q.feedback || q.comentario || "",
      }))
    : []

  const questionsList = normalizedQuestions.filter(
    (q) => q.answer || q.feedback || q.score > 0
  )

  if (questionsList.length === 0) return null

  // Calcular nota global de preguntas
  const totalScore = questionsList.reduce((sum, q) => sum + q.score, 0)
  const avgScore = Math.round(totalScore / questionsList.length)

  return (
    <div className="bg-card rounded-2xl p-6 border border-border mb-8">
      {/* Header con nota global */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          Preguntas de Desarrollo
        </h2>
        <div className="text-center">
          <div className="text-2xl font-bold text-foreground">{avgScore}%</div>
          <div className="text-xs text-muted-foreground">Nota Global</div>
        </div>
      </div>

      {/* Accordions de preguntas */}
      <div className="space-y-3">
        {questionsList.map((q) => (
          <div key={q.id} className="border border-border rounded-lg overflow-hidden">
            {/* Header del accordion */}
            <button
              onClick={() => toggleQuestion(q.id)}
              className="w-full p-4 flex items-center justify-between hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-foreground">{q.id}. {q.title}</span>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={q.score >= 70 ? "default" : "destructive"}>
                  {q.score}%
                </Badge>
                {expandedQuestions[q.id] ? (
                  <ChevronUp className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </button>

            {/* Contenido expandible */}
            {expandedQuestions[q.id] && (
              <div className="border-t border-border p-4 space-y-3">
                {/* Respuesta del estudiante */}
                <div className="bg-accent/20 rounded-lg p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Tu respuesta:</p>
                  <p className="text-sm text-foreground whitespace-pre-wrap">{q.answer}</p>
                </div>

                {/* Feedback del evaluador */}
                {q.feedback && (
                  <div className="flex items-start gap-2 bg-primary/5 rounded-lg p-3">
                    <AlertCircle className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-xs font-medium text-primary mb-1">Feedback del evaluador:</p>
                      <p className="text-sm text-foreground whitespace-pre-wrap">{q.feedback}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
