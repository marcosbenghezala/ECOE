import { useState, useEffect } from "react"
import { Dashboard } from "@/components/dashboard"
import { CasePreview } from "@/components/case-preview"
import { StudentForm } from "@/components/student-form"
import { AudioTest } from "@/components/audio-test"
import { CaseInstructions } from "@/components/case-instructions"
import { SimulationInterface } from "@/components/simulation-interface"
import { ClinicalReflection } from "@/components/clinical-reflection"
import { LoadingResults } from "@/components/loading-results"
import { ResultsScreen } from "@/components/results-screen"
import { ResultsScreenV3 } from "@/components/results-screen-v3"
import { SurveyScreen } from "@/components/survey-screen"
import type { SimulationStep, CaseData, StudentData } from "@/types"

// Use empty string for relative URLs (works in both localhost and production)
const API_BASE_URL = import.meta.env.VITE_API_URL || ""

export default function Home() {
  const [currentStep, setCurrentStep] = useState<SimulationStep>("dashboard")
  const [selectedCase, setSelectedCase] = useState<CaseData | null>(null)
  const [studentData, setStudentData] = useState<StudentData | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [cases, setCases] = useState<CaseData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [evaluationResults, setEvaluationResults] = useState<any | null>(null)
  const [reflectionQuestions, setReflectionQuestions] = useState<any[]>([])

  // Cargar casos desde el backend
  useEffect(() => {
    loadCases()
  }, [])

  // Cargar preguntas cuando se selecciona un caso
  useEffect(() => {
    if (selectedCase?.id) {
      loadReflectionQuestions(selectedCase.id)
    }
  }, [selectedCase])

  async function loadCases() {
    try {
      setIsLoading(true)
      setError(null)
      const response = await fetch(`${API_BASE_URL}/api/cases`)

      if (!response.ok) {
        throw new Error('Error al cargar los casos')
      }

      const backendCases = await response.json()

      // Adaptar formato backend a formato frontend
      const adaptedCases: CaseData[] = backendCases.map((c: any) => ({
        id: c.id,
        title: c.titulo,
        description: c.descripcion_corta || c.motivo_consulta || 'Sin descripción',
        difficulty: c.dificultad as "Básico" | "Intermedio" | "Avanzado",
        duration: `${c.duracion_estimada || 15} min`,
        category: c.especialidad,
        tags: [c.especialidad, c.dificultad].filter(Boolean),
        patientAge: c.informacion_paciente?.edad || 0,
        patientGender: c.informacion_paciente?.genero || "Desconocido",
        chiefComplaint: c.motivo_consulta || "Sin motivo de consulta",
        // Datos originales del backend
        especialidad: c.especialidad,
        duracion_estimada: c.duracion_estimada,
        motivo_consulta: c.motivo_consulta,
        informacion_paciente: c.informacion_paciente
      }))

      setCases(adaptedCases)
      console.log('✅ Casos cargados:', adaptedCases.length)
    } catch (err) {
      console.error('Error loading cases:', err)
      setError(`Error al cargar los casos. Asegúrate de que el backend esté corriendo en ${API_BASE_URL}`)
    } finally {
      setIsLoading(false)
    }
  }

  async function loadReflectionQuestions(caseId: string) {
    try {
      console.log(`📋 Cargando preguntas para caso: ${caseId}`)
      const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/questions`)

      if (!response.ok) {
        console.warn('⚠️ Error cargando preguntas, usando fallback')
        return
      }

      const data = await response.json()
      setReflectionQuestions(data.questions || [])
      console.log(`✅ Preguntas cargadas: ${data.questions?.length || 0} (source: ${data.source})`)
    } catch (err) {
      console.error('Error loading reflection questions:', err)
      // No bloqueamos la UI, solo usamos preguntas hardcoded en ClinicalReflection
    }
  }

  const handleSelectCase = (caseData: CaseData) => {
    setSelectedCase(caseData)
    setIsPreviewOpen(true)
  }

  const handleClosePreview = () => {
    setIsPreviewOpen(false)
    setTimeout(() => {
      setSelectedCase(null)
    }, 300)
  }

  const handleStartCase = () => {
    setIsPreviewOpen(false)
    setTimeout(() => {
      setCurrentStep("student-form")
    }, 300)
  }

  const handleStudentSubmit = (data: StudentData) => {
    setStudentData(data)
    setCurrentStep("audio-test")
  }

  const handleAudioTestComplete = () => {
    setCurrentStep("instructions")
  }

  async function handleStartSimulation() {
    try {
      setIsLoading(true)
      setError(null)

      // Iniciar sesión de simulación en el backend
      const response = await fetch(`${API_BASE_URL}/api/simulation/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          case_id: selectedCase?.id,
          student: studentData,
        }),
      })

      if (!response.ok) {
        throw new Error('Error al iniciar la simulación')
      }

      const data = await response.json()
      setSessionId(data.session_id)
      console.log('✅ Simulación iniciada:', data.session_id)

      setCurrentStep("simulation")
    } catch (err) {
      console.error('Error starting simulation:', err)
      setError('Error al iniciar la simulación. Verifica tu conexión.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEndSimulation = () => {
    setCurrentStep("reflection")
  }

  const handleReflectionComplete = async (reflectionData: any) => {
    try {
      setCurrentStep("loading")
      setIsLoading(true)
      setError(null)

      console.log('📝 Enviando reflexión para evaluación:', reflectionData)

      // Llamar AMBOS endpoints (V2 y V3) en paralelo
      const [responseV2, responseV3] = await Promise.all([
        // V2 (legacy): evaluación con embeddings + reflexión clínica
        fetch(`${API_BASE_URL}/api/simulation/evaluate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            reflection: reflectionData
          }),
        }),
        // V3 (nuevo): evaluación con checklist v2
        fetch(`${API_BASE_URL}/api/evaluate_checklist_v3`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId
          }),
        }).catch(err => {
          console.warn('⚠️ V3 endpoint falló (esperado si no está disponible):', err)
          return null
        })
      ])

      if (!responseV2.ok) {
        throw new Error('Error al evaluar la simulación')
      }

      const resultsV2 = await responseV2.json()

      // Intentar obtener resultados V3 si el endpoint respondió
      let resultsV3 = null
      if (responseV3 && responseV3.ok) {
        resultsV3 = await responseV3.json()
        console.log('✅ Evaluación V3 recibida:', resultsV3)
      }

      // COMBINAR ambos resultados (V3 tiene checklist, V2 tiene reflexión)
      const combinedResults = resultsV3 ? {
        ...resultsV3,
        // Agregar datos de reflexión de V2
        reflection: resultsV2.reflection,
        reflectionScore: resultsV2.reflectionScore,
        // Mantener compatibilidad con V2
        completedItems: resultsV2.completedItems,
        missedItems: resultsV2.missedItems,
      } : resultsV2

      setEvaluationResults(combinedResults)
      console.log('✅ Evaluación final combinada:', combinedResults)

      // Esperar mínimo 2 segundos para la animación de carga
      await new Promise(resolve => setTimeout(resolve, 2000))

      setCurrentStep("results")
    } catch (err) {
      console.error('Error evaluating simulation:', err)
      setError('Error al evaluar la simulación. Verifica tu conexión.')
      // Aún así mostrar resultados (con datos de fallback)
      setTimeout(() => setCurrentStep("results"), 1000)
    } finally {
      setIsLoading(false)
    }
  }

  const handleBackToDashboard = () => {
    setCurrentStep("dashboard")
    setSelectedCase(null)
    setStudentData(null)
  }

  const handleBackToPreview = () => {
    setCurrentStep("dashboard")
    setIsPreviewOpen(true)
  }

  const handleBackToStudentForm = () => {
    setCurrentStep("student-form")
  }

  const handleBackToAudioTest = () => {
    setCurrentStep("audio-test")
  }

  const handleGoToSurvey = () => {
    setCurrentStep("survey")
  }

  const handleSurveyComplete = () => {
    handleBackToDashboard()
  }

  // Mostrar error si hay
  if (error && !isLoading && currentStep === "dashboard") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <h2 className="text-2xl font-bold text-destructive mb-4">Error</h2>
          <p className="text-muted-foreground mb-6">{error}</p>
          <button
            onClick={loadCases}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-background">
      {(currentStep === "dashboard" || isPreviewOpen) && (
        <div className={`transition-all duration-300 ${isPreviewOpen ? "pointer-events-none opacity-50" : ""}`}>
          <Dashboard cases={cases} onSelectCase={handleSelectCase} />
        </div>
      )}

      {selectedCase && (
        <CasePreview
          caseData={selectedCase}
          onClose={handleClosePreview}
          onStart={handleStartCase}
          isOpen={isPreviewOpen}
        />
      )}

      {currentStep === "student-form" && <StudentForm onSubmit={handleStudentSubmit} onBack={handleBackToPreview} />}

      {currentStep === "audio-test" && (
        <AudioTest onComplete={handleAudioTestComplete} onBack={handleBackToStudentForm} />
      )}

      {currentStep === "instructions" && selectedCase && (
        <CaseInstructions caseData={selectedCase} onStart={handleStartSimulation} onBack={handleBackToAudioTest} />
      )}

      {currentStep === "simulation" && selectedCase && sessionId && (
        <SimulationInterface
          caseData={selectedCase}
          sessionId={sessionId}
          onEnd={handleEndSimulation}
        />
      )}

      {currentStep === "reflection" && (
        <ClinicalReflection
          onSubmit={handleReflectionComplete}
          questions={reflectionQuestions}
        />
      )}

      {currentStep === "loading" && <LoadingResults />}

      {currentStep === "results" && selectedCase && studentData && (
        evaluationResults?.blocks ? (
          <ResultsScreenV3
            caseData={selectedCase}
            studentData={studentData}
            evaluationResults={evaluationResults}
            onBackToDashboard={handleBackToDashboard}
            onGoToSurvey={handleGoToSurvey}
          />
        ) : (
          <ResultsScreen
            caseData={selectedCase}
            studentData={studentData}
            evaluationResults={evaluationResults}
            onBackToDashboard={handleBackToDashboard}
            onGoToSurvey={handleGoToSurvey}
          />
        )
      )}

      {currentStep === "survey" && (
        <SurveyScreen
          sessionId={sessionId || undefined}
          onComplete={handleSurveyComplete}
          onSkip={handleSurveyComplete}
        />
      )}
    </main>
  )
}
