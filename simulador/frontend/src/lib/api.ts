import type {
  CaseData,
  StudentData,
  AudioTestResult,
  ClinicalReflection,
  EvaluationResult,
  SurveyPayload,
  SessionData,
} from "@/types"

// Use empty string for relative URLs (works in both localhost and production)
// Backend serves frontend from same domain, so /api routes work automatically
// Updated: 2025-12-19
export const API_BASE_URL = import.meta.env.VITE_API_URL || ""

/**
 * API Client for backend communication
 */

// Session Management
export async function createSession(
  studentData: StudentData,
  caseData: CaseData
): Promise<{ session_id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/session/create`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      student: studentData,
      case: caseData,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to create session")
  }

  return response.json()
}

export async function getSession(sessionId: string): Promise<SessionData> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}`)

  if (!response.ok) {
    throw new Error("Failed to get session")
  }

  return response.json()
}

// Audio Test
export async function saveAudioTest(
  sessionId: string,
  audioTestResult: AudioTestResult
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/audio-test`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(audioTestResult),
  })

  if (!response.ok) {
    throw new Error("Failed to save audio test")
  }
}

// Clinical Reflection
export async function saveClinicalReflection(
  sessionId: string,
  reflection: ClinicalReflection
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/reflection`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(reflection),
  })

  if (!response.ok) {
    throw new Error("Failed to save clinical reflection")
  }
}

// Evaluation
export async function getEvaluation(sessionId: string): Promise<EvaluationResult> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/evaluate`, {
    method: "POST",
  })

  if (!response.ok) {
    throw new Error("Failed to get evaluation")
  }

  return response.json()
}

// Survey
export async function saveSurvey(
  sessionId: string,
  survey: SurveyPayload
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/survey`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(survey),
  })

  if (!response.ok) {
    throw new Error("Failed to save survey")
  }
}

// Cases
export async function getCases(): Promise<CaseData[]> {
  const response = await fetch(`${API_BASE_URL}/api/cases`)

  if (!response.ok) {
    throw new Error("Failed to get cases")
  }

  return response.json()
}

export async function getCase(caseId: string): Promise<CaseData> {
  const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}`)

  if (!response.ok) {
    throw new Error("Failed to get case")
  }

  return response.json()
}

// WebSocket for Real-time Voice
export function createVoiceWebSocket(sessionId: string): WebSocket {
  const wsUrl = API_BASE_URL.replace("http", "ws")
  return new WebSocket(`${wsUrl}/ws/realtime/${sessionId}`)
}

// Utility function to handle errors
export function handleApiError(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  return "An unknown error occurred"
}
