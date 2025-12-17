import {
  CheckCircle2,
  XCircle,
  Award,
  Clock,
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

// Componente principal que detecta V2 o V3
export function ResultsScreenV3({ caseData, studentData, evaluationResults, onBackToDashboard, onGoToSurvey }: ResultsScreenV3Props) {
  // Detectar si es evaluación V3 (tiene campo "blocks")
  const isV3 = evaluationResults?.blocks !== undefined

  if (isV3) {
    return <ResultsV3View caseData={caseData} studentData={studentData} evaluationResults={evaluationResults} onBackToDashboard={onBackToDashboard} onGoToSurvey={onGoToSurvey} />
  }

  // Fallback a vista V2: mostrar mensaje temporal
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="bg-card rounded-2xl p-8 border border-border max-w-md text-center">
        <h2 className="text-xl font-bold text-foreground mb-4">Evaluación V2 (Legacy)</h2>
        <p className="text-muted-foreground mb-6">
          Esta sesión fue evaluada con el sistema V2. Para ver los resultados detallados por bloques,
          completa una nueva simulación.
        </p>
        <Button onClick={onBackToDashboard}>
          <Home className="w-4 h-4 mr-2" />
          Volver al Inicio
        </Button>
      </div>
    </div>
  )
}

// Vista para evaluación V3
function ResultsV3View({ caseData, studentData, evaluationResults, onBackToDashboard, onGoToSurvey }: ResultsScreenV3Props) {
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>({})

  // Datos de evaluación V3
  const percentage = Math.round(evaluationResults?.percentage || 0)
  const pointsObtained = evaluationResults?.points_obtained || 0
  const maxPointsCase = evaluationResults?.max_points_case || 0
  const minPointsCase = evaluationResults?.min_points_case || 0
  const passed = evaluationResults?.passed || false
  const blocks = evaluationResults?.blocks || {}
  const b7Subsections = evaluationResults?.b7_subsections || {}
  const summary = evaluationResults?.summary || {}
  const itemsEvaluated = evaluationResults?.items_evaluated || []

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

          {Object.entries(blocks).map(([blockId, blockData]: [string, any]) => {
            // Filtrar items de este bloque
            // blockId = "B0_INTRODUCCION" → extraer "B0" → buscar items que empiecen con "B0_"
            const blockNumber = blockId.split('_')[0]  // "B0_INTRODUCCION" → "B0"
            const blockItems = itemsEvaluated.filter((item: any) => item.item_id.startsWith(blockNumber + '_'))

            return (
              <BlockResultCard
                key={blockId}
                blockId={blockId}
                blockName={blockNames[blockId] || blockId}
                blockData={blockData}
                blockItems={blockItems}
                isExpanded={expandedBlocks[blockId] || false}
                onToggle={() => toggleBlock(blockId)}
                // Mostrar subsecciones si es B7
                subsections={blockId === "B7_ANAMNESIS_APARATOS" ? b7Subsections : undefined}
              />
            )
          })}
        </div>

        {/* Subsecciones B7 Activadas (info) */}
        {evaluationResults?.subsections_b7_activas && evaluationResults.subsections_b7_activas.length > 0 && (
          <div className="bg-primary/5 rounded-xl p-4 border border-primary/20 mb-8">
            <h3 className="text-sm font-medium text-foreground mb-2">Subsecciones Activadas (Anamnesis por Aparatos)</h3>
            <div className="flex flex-wrap gap-2">
              {evaluationResults.subsections_b7_activas.map((subsection: string) => (
                <Badge key={subsection} variant="outline">{subsection}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Preguntas de Desarrollo */}
        {evaluationResults?.reflection && (
          <DevelopmentQuestionsSection reflection={evaluationResults.reflection} />
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
  subsections,
}: {
  blockId: string
  blockName: string
  blockData: any
  blockItems: any[]
  isExpanded: boolean
  onToggle: () => void
  subsections?: Record<string, any>
}) {
  const percentage = blockData.percentage || 0
  const pointsObtained = blockData.points_obtained || 0
  const maxPoints = blockData.max_points || 0
  const itemsMatched = blockData.items_matched || 0
  const itemsTotal = blockData.items_total || 0

  // Separar items cumplidos y no cumplidos
  const itemsCumplidos = blockItems.filter((item: any) => item.matched)
  const itemsNoCumplidos = blockItems.filter((item: any) => !item.matched)

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
          {/* Mostrar subsecciones si es B7 */}
          {subsections && Object.keys(subsections).length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-foreground mb-3">Subsecciones Evaluadas:</h4>
              <div className="space-y-2">
                {Object.entries(subsections).map(([subsectionName, subsectionData]: [string, any]) => (
                  <div key={subsectionName} className="flex items-center justify-between bg-accent/30 rounded-lg p-3">
                    <div>
                      <div className="font-medium text-sm text-foreground">{subsectionName}</div>
                      <div className="text-xs text-muted-foreground">
                        {subsectionData.items_matched}/{subsectionData.items_total} ítems - {subsectionData.points_obtained}/{subsectionData.max_points} pts
                      </div>
                    </div>
                    <Badge variant={subsectionData.percentage >= 60 ? "default" : "outline"}>
                      {Math.round(subsectionData.percentage)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

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
                    <div key={item.item_id} className="flex items-start gap-2 text-sm bg-success/5 rounded p-2">
                      <CheckCircle2 className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="font-medium text-foreground">{item.label || item.item_id}</div>
                        <div className="text-xs text-muted-foreground">ID: {item.item_id}</div>
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
                    <div key={item.item_id} className="flex items-start gap-2 text-sm bg-destructive/5 rounded p-2">
                      <XCircle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="text-muted-foreground">{item.label || item.item_id}</div>
                        <div className="text-xs text-muted-foreground/70">ID: {item.item_id}</div>
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
function DevelopmentQuestionsSection({ reflection }: { reflection: any }) {
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({})

  const toggleQuestion = (questionId: number) => {
    setExpandedQuestions((prev) => ({ ...prev, [questionId]: !prev[questionId] }))
  }

  // Definir las 4 preguntas con sus datos
  const questions = [
    {
      id: 1,
      title: "Resumen del Caso",
      answer: reflection.resumen_caso,
      score: reflection.puntuacion_resumen || 0,
      feedback: reflection.resumen_feedback
    },
    {
      id: 2,
      title: "Diagnóstico Principal",
      answer: reflection.diagnostico_principal,
      score: reflection.puntuacion_diagnostico || 0,
      feedback: reflection.diagnostico_feedback
    },
    {
      id: 3,
      title: "Diagnósticos Diferenciales",
      answer: reflection.diagnosticos_diferenciales,
      score: reflection.puntuacion_diferenciales || 0,
      feedback: reflection.diferenciales_feedback
    },
    {
      id: 4,
      title: "Pruebas Complementarias",
      answer: reflection.pruebas_diagnosticas,
      score: reflection.puntuacion_pruebas || 0,
      feedback: reflection.pruebas_feedback
    }
  ].filter(q => q.answer) // Solo mostrar preguntas con respuesta

  if (questions.length === 0) return null

  // Calcular nota global de preguntas
  const totalScore = questions.reduce((sum, q) => sum + q.score, 0)
  const avgScore = Math.round(totalScore / questions.length)

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
        {questions.map((q) => (
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
