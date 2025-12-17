import { User, Clock, Target, AlertTriangle, MessageSquare, ArrowRight, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { UMHLogo } from "@/components/umh-logo"
import type { CaseData } from "@/types"

interface CaseInstructionsProps {
  caseData: CaseData
  onStart: () => void
  onBack: () => void
}

export function CaseInstructions({ caseData, onStart, onBack }: CaseInstructionsProps) {
  const instructions = [
    {
      icon: MessageSquare,
      title: "Comunicación por voz",
      description:
        "Habla con el paciente virtual como lo harías en una consulta real. El sistema reconocerá tu voz y responderá.",
    },
    {
      icon: Target,
      title: "Objetivo clínico",
      description: "Realiza la anamnesis completa, explora los síntomas y llega a un diagnóstico diferencial.",
    },
    {
      icon: AlertTriangle,
      title: "Información adicional",
      description: "En ciertos momentos podrían aparecer imágenes o resultados de pruebas relevantes para el caso.",
    },
  ]

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
        <div className="w-full max-w-2xl">
          {/* Case Info */}
          <div className="text-center mb-8">
            <Badge variant="outline" className="mb-4 bg-primary/5 text-primary border-primary/20">
              {caseData.category}
            </Badge>
            <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">{caseData.title}</h1>
            <p className="text-muted-foreground">{caseData.description}</p>
          </div>

          {/* Patient Summary */}
          <div className="bg-card rounded-2xl p-6 border border-border mb-6">
            <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              Información del paciente
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-muted-foreground">Edad</span>
                <p className="font-medium text-foreground">{caseData.patientAge} años</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Sexo</span>
                <p className="font-medium text-foreground">{caseData.patientGender}</p>
              </div>
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">Motivo de consulta</span>
                <p className="font-medium text-foreground">{caseData.chiefComplaint}</p>
              </div>
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-primary/5 rounded-2xl p-6 border border-primary/10 mb-6">
            <h2 className="font-semibold text-foreground mb-4">Instrucciones</h2>
            <div className="space-y-4">
              {instructions.map((instruction, index) => (
                <div key={index} className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <instruction.icon className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground text-sm">{instruction.title}</h3>
                    <p className="text-sm text-muted-foreground">{instruction.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div className="flex items-center justify-center gap-2 text-muted-foreground mb-8">
            <Clock className="w-4 h-4" />
            <span className="text-sm">Duración estimada: {caseData.duration}</span>
          </div>

          <div className="flex gap-3">
            <Button variant="outline" onClick={onBack} className="flex-1 h-14 text-lg font-medium bg-transparent">
              <ArrowLeft className="w-5 h-5 mr-2" />
              Volver
            </Button>
            <Button
              onClick={onStart}
              className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground h-14 text-lg font-medium"
            >
              Comenzar simulación
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
