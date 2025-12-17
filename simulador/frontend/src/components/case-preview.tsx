import { X, Clock, User, AlertCircle, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { CaseData } from "@/types"

interface CasePreviewProps {
  caseData: CaseData
  onClose: () => void
  onStart: () => void
  isOpen: boolean
}

export function CasePreview({ caseData, onClose, onStart, isOpen }: CasePreviewProps) {
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "Básico":
        return "bg-success/10 text-success border-success/20"
      case "Intermedio":
        return "bg-warning/10 text-warning-foreground border-warning/20"
      case "Avanzado":
        return "bg-primary/10 text-primary border-primary/20"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  return (
    <div
      className={`fixed inset-0 z-50 transition-all duration-300 ${
        isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      <div
        className={`absolute inset-0 bg-black/70 backdrop-blur-[2px] transition-all duration-300 ${
          isOpen ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
      />

      <button
        onClick={onClose}
        className={`absolute top-6 right-6 z-20 w-11 h-11 rounded-full bg-card/90 border border-border flex items-center justify-center hover:bg-card transition-all duration-300 ${
          isOpen ? "opacity-100 scale-100" : "opacity-0 scale-75"
        }`}
        style={{ transitionDelay: isOpen ? "150ms" : "0ms" }}
      >
        <X className="w-5 h-5 text-foreground" />
      </button>

      <div className="absolute inset-0 flex items-center justify-center p-6 overflow-y-auto">
        <div
          className={`bg-card rounded-2xl shadow-2xl w-full max-w-2xl my-auto transition-all duration-300 ease-out ${
            isOpen ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-8"
          }`}
        >
          {/* Case Header */}
          <div className="p-8 border-b border-border bg-primary/5 rounded-t-2xl">
            <div className="flex items-center gap-3 mb-4">
              {caseData.difficulty && (
                <Badge variant="outline" className={`${getDifficultyColor(caseData.difficulty)} font-medium`}>
                  {caseData.difficulty}
                </Badge>
              )}
              <Badge variant="secondary">{caseData.category}</Badge>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-2">{caseData.title}</h2>
            <p className="text-muted-foreground">{caseData.description}</p>
          </div>

          {/* Case Details */}
          <div className="p-8">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
              Información del Paciente
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-xl">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Paciente</div>
                  <div className="font-medium text-foreground">
                    {caseData.patientAge} años, {caseData.patientGender}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-xl">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Duración estimada</div>
                  <div className="font-medium text-foreground">{caseData.duration}</div>
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-4 bg-primary/5 rounded-xl border border-primary/10 mb-8">
              <AlertCircle className="w-5 h-5 text-primary mt-0.5 shrink-0" />
              <div>
                <div className="font-medium text-foreground mb-1">Motivo de consulta</div>
                <div className="text-sm text-muted-foreground">{caseData.chiefComplaint}</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-8">
              {caseData.tags.map((tag) => (
                <span key={tag} className="text-sm px-3 py-1.5 bg-secondary rounded-lg text-secondary-foreground">
                  {tag}
                </span>
              ))}
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <Button variant="outline" className="flex-1 bg-transparent" onClick={onClose}>
                Volver
              </Button>
              <Button className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground" onClick={onStart}>
                Comenzar caso
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
