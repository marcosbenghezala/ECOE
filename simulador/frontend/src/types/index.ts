// Case Data Types (adaptado al formato del backend)
export interface CaseData {
  id: string
  title: string
  description: string
  difficulty?: "Básico" | "Intermedio" | "Avanzado"  // Opcional - no rompe si caso no lo tiene
  duration: string
  category: string
  tags: string[]
  patientAge: number
  patientGender: string
  chiefComplaint: string
  // Campos adicionales del backend
  especialidad?: string
  duracion_estimada?: number
  motivo_consulta?: string
  informacion_paciente?: {
    nombre: string
    edad: number
    genero: string
    ocupacion?: string
  }
}

// Student Data Types
export interface StudentData {
  nombre: string
  email: string
  dni: string
  sexo: string
  consentimiento: boolean
}

// Audio Test Types
export interface AudioTestResult {
  microphoneTest: boolean
  speakerTest: boolean
  timestamp: string
}

// Clinical Reflection Types (dinámico por caso)
export type ClinicalReflection = Record<string, string>

// Simulation Types
export interface SimulationState {
  isConnected: boolean
  isRecording: boolean
  transcript: string
  aiResponse: string
  timeElapsed: number
  conversationHistory: ConversationEntry[]
}

export interface ConversationEntry {
  role: "user" | "assistant"
  content: string
  timestamp: string
}

// Results Types (schema evaluation.production.v1)
export interface EvaluationItem {
  id: string
  bloque: string
  descripcion: string
  done: boolean
  score: number
  max_score: number
  critical?: boolean
}

export interface EvaluationBlock {
  id: string
  name: string
  score: number
  max: number
  percentage: number
  items: EvaluationItem[]
}

export interface EvaluationDevelopmentQuestion {
  question: string
  answer: string
  score: number
  max_score: number
  feedback: string
}

export interface EvaluationDevelopment {
  percentage: number
  questions: EvaluationDevelopmentQuestion[]
}

export interface EvaluationScoreBucket {
  score?: number
  max?: number
  percentage?: number
  weighted?: number
  weight?: number
}

export interface EvaluationScores {
  global: EvaluationScoreBucket
  checklist: EvaluationScoreBucket
  anamnesis?: EvaluationScoreBucket
  development: EvaluationScoreBucket
}

export interface EvaluationResult {
  schema_version: string
  checklist_meta?: Record<string, any>
  scores: EvaluationScores
  items: EvaluationItem[]
  blocks: EvaluationBlock[]
  development: EvaluationDevelopment
  survey?: Record<string, any>
}

// Survey Types
export interface SurveyResponse {
  realismo: number
  utilidad: number
  interfaz: number
  dificultad: number
  confianza_antes: number
  confianza_despues: number
  recomendacion: number
  volver_a_usar: number
  comentarios_positivos: string
  sugerencias_mejora: string
}

export interface SurveyAnswer {
  pregunta: string
  respuesta: string
}

export interface SurveyPayload {
  responses: SurveyAnswer[]
}

// Session Types
export interface SessionData {
  session_id: string
  student: StudentData
  case: CaseData
  audio_test: AudioTestResult
  simulation: SimulationState
  reflection: ClinicalReflection
  evaluation: EvaluationResult
  survey: SurveyResponse
  timestamps: {
    started: string
    audio_tested: string
    simulation_started: string
    simulation_ended: string
    reflection_completed: string
    results_viewed: string
    survey_completed: string
  }
}

// App State Types
export type SimulationStep =
  | "dashboard"
  | "preview"
  | "student-form"
  | "audio-test"
  | "instructions"
  | "simulation"
  | "reflection"
  | "loading"
  | "results"
  | "survey"

export type AppScreen = SimulationStep

export interface AppState {
  currentScreen: AppScreen
  selectedCase: CaseData | null
  studentData: StudentData | null
  audioTestResult: AudioTestResult | null
  clinicalReflection: ClinicalReflection | null
  evaluationResult: EvaluationResult | null
  surveyResponse: SurveyResponse | null
  sessionId: string | null
}
