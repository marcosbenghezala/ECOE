import type React from "react"

import { useState } from "react"
import { User, Mail, CreditCard, Users, Shield, ArrowRight, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { UMHLogo } from "@/components/umh-logo"
import type { StudentData } from "@/types"

interface StudentFormProps {
  onSubmit: (data: StudentData) => void
  onBack: () => void
}

export function StudentForm({ onSubmit, onBack }: StudentFormProps) {
  const [formData, setFormData] = useState({
    nombre: "",
    email: "",
    dni: "",
    sexo: "",
    consentimiento: false,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.nombre.trim()) newErrors.nombre = "El nombre es obligatorio"
    if (!formData.email.trim()) newErrors.email = "El email es obligatorio"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Introduce un email válido"
    }
    if (!formData.dni.trim()) newErrors.dni = "El DNI es obligatorio"
    else if (!/^[0-9]{8}[A-Za-z]$/.test(formData.dni)) {
      newErrors.dni = "Introduce un DNI válido (8 números + letra)"
    }
    if (!formData.sexo) newErrors.sexo = "Selecciona una opción"
    if (!formData.consentimiento) newErrors.consentimiento = "Debes aceptar el consentimiento"

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      onSubmit(formData as StudentData)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center">
          <UMHLogo />
        </div>
      </header>

      {/* Form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
              <User className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">Identificación del Estudiante</h1>
            <p className="text-muted-foreground">Completa tus datos para comenzar la simulación</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="bg-card rounded-2xl p-6 border border-border shadow-sm">
              {/* Nombre */}
              <div className="space-y-2 mb-5">
                <Label htmlFor="nombre" className="text-foreground flex items-center gap-2">
                  <User className="w-4 h-4 text-muted-foreground" />
                  Nombre completo *
                </Label>
                <Input
                  id="nombre"
                  placeholder="Ej: María García López"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  className={errors.nombre ? "border-destructive" : ""}
                />
                {errors.nombre && <p className="text-sm text-destructive">{errors.nombre}</p>}
              </div>

              {/* Email */}
              <div className="space-y-2 mb-5">
                <Label htmlFor="email" className="text-foreground flex items-center gap-2">
                  <Mail className="w-4 h-4 text-muted-foreground" />
                  Correo electrónico *
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="tu.email@umh.es"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className={errors.email ? "border-destructive" : ""}
                />
                {errors.email && <p className="text-sm text-destructive">{errors.email}</p>}
              </div>

              {/* DNI */}
              <div className="space-y-2 mb-5">
                <Label htmlFor="dni" className="text-foreground flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-muted-foreground" />
                  DNI *
                </Label>
                <Input
                  id="dni"
                  placeholder="12345678A"
                  value={formData.dni}
                  onChange={(e) => setFormData({ ...formData, dni: e.target.value.toUpperCase() })}
                  className={errors.dni ? "border-destructive" : ""}
                  maxLength={9}
                />
                {errors.dni && <p className="text-sm text-destructive">{errors.dni}</p>}
              </div>

              {/* Sexo */}
              <div className="space-y-3 mb-5">
                <Label className="text-foreground flex items-center gap-2">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  Sexo *
                </Label>
                <RadioGroup
                  value={formData.sexo}
                  onValueChange={(value) => setFormData({ ...formData, sexo: value })}
                  className="flex gap-6"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="masculino" id="masculino" />
                    <Label htmlFor="masculino" className="font-normal cursor-pointer">
                      Masculino
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="femenino" id="femenino" />
                    <Label htmlFor="femenino" className="font-normal cursor-pointer">
                      Femenino
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="otro" id="otro" />
                    <Label htmlFor="otro" className="font-normal cursor-pointer">
                      Otro
                    </Label>
                  </div>
                </RadioGroup>
                {errors.sexo && <p className="text-sm text-destructive">{errors.sexo}</p>}
              </div>
            </div>

            {/* Consentimiento */}
            <div className="bg-primary/5 rounded-2xl p-6 border border-primary/10">
              <div className="flex items-start space-x-3">
                <Checkbox
                  id="consentimiento"
                  checked={formData.consentimiento}
                  onCheckedChange={(checked) => setFormData({ ...formData, consentimiento: checked as boolean })}
                  className="mt-1"
                />
                <div className="flex-1">
                  <Label htmlFor="consentimiento" className="text-foreground cursor-pointer flex items-start gap-2">
                    <Shield className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                    <span>
                      Acepto que la Universidad Miguel Hernández utilice mis datos y las grabaciones de esta simulación
                      con fines académicos y de investigación, de acuerdo con la política de privacidad de la
                      institución.
                    </span>
                  </Label>
                </div>
              </div>
              {errors.consentimiento && <p className="text-sm text-destructive mt-2 ml-6">{errors.consentimiento}</p>}
            </div>

            <div className="flex gap-3">
              <Button type="button" variant="outline" onClick={onBack} className="flex-1 h-12 text-base bg-transparent">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Volver
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground h-12 text-base"
              >
                Continuar
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
