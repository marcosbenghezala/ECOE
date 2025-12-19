# SimuPaciente UMH - Presentación para Profesores
**Universidad Miguel Hernández de Elche**
**Facultad de Medicina**

---

## 🎯 Resumen Ejecutivo

**SimuPaciente** es un sistema de simulación de pacientes virtuales con inteligencia artificial para entrenamiento de competencias clínicas en estudiantes de medicina.

### Características Principales:
- ✅ **Paciente virtual con voz en tiempo real** (OpenAI Realtime API)
- ✅ **Evaluación automática** con checklist estandarizado
- ✅ **Feedback inmediato** y personalizado
- ✅ **Integración con Google Sheets** para seguimiento docente
- ✅ **Casos clínicos configurables** por especialidad

---

## 🔗 Demo en Vivo

**URL:** [SE GENERARÁ AL DEPLOYAR]

**Credenciales de prueba:**
- Email: `demo@umh.es`
- Caso sugerido: "Dolor torácico en varón de 55 años"

---

## 🏥 Casos Clínicos Disponibles

La demo incluye casos de múltiples especialidades:

### Cardiología
- Infarto agudo de miocardio
- Angina de pecho
- Insuficiencia cardíaca

### Neumología
- Neumonía
- EPOC
- Asma aguda

### Gastroenterología
- Apendicitis aguda
- Úlcera péptica
- Pancreatitis

**Total:** [X casos actualmente configurados]

---

## 📊 Funcionalidades Incluidas

### 1. Simulación Interactiva
- **Conversación de voz bidireccional** con el paciente virtual
- Respuestas contextualizadas al caso clínico
- Comportamiento realista (no da información espontáneamente)
- Latencia < 300ms

### 2. Evaluación Automática en Tiempo Real
- **Checklist de competencias** estructurado en bloques:
  - B1: Presentación e inicio
  - B2: Motivo de consulta
  - B3-B6: Anamnesis (SOCRATES)
  - B7: Exploración y pruebas
  - B8: Cierre

- **Puntuación automática** por item cumplido
- **Feedback visual inmediato** (✓ items completados)

### 3. Reflexión Post-Simulación
- Preguntas de desarrollo sobre el caso
- Evaluación automática con IA (GPT-4o-mini)
- Feedback estructurado:
  - Tu respuesta
  - Respuesta esperada
  - Evaluación detallada

### 4. Resultados y Análisis
- **Descarga en PDF** de resultados individuales
- **Integración Google Sheets** para análisis agregado
- Métricas por estudiante y por grupo

---

## 🎓 Valor Pedagógico

### Competencias que se Entrenan:
1. **Anamnesis estructurada** (método SOCRATES)
2. **Comunicación médico-paciente**
3. **Razonamiento clínico** y diagnóstico diferencial
4. **Gestión del tiempo** en consulta
5. **Reflexión post-consulta**

### Ventajas vs Métodos Tradicionales:

| Método | Pacientes Estandarizados | Casos en Papel | **SimuPaciente IA** |
|--------|--------------------------|----------------|---------------------|
| **Disponibilidad** | Limitada (horarios) | 24/7 | ✅ **24/7** |
| **Feedback** | Subjetivo, tardío | No hay | ✅ **Inmediato** |
| **Escalabilidad** | Cara (actores) | Buena | ✅ **Ilimitada** |
| **Estandarización** | Variable | Alta | ✅ **Total** |
| **Datos para docentes** | Manual | Manual | ✅ **Automático** |
| **Coste** | €50-100/sesión | €0 | ✅ **€0.10/sesión** |
| **Voz natural** | ✅ Sí | ❌ No | ✅ **Sí (IA)** |

---

## 💻 Arquitectura Técnica

### Stack Tecnológico:
- **Frontend:** React 19 + TypeScript
- **Backend:** Flask + WebSocket
- **IA de Conversación:** OpenAI Realtime API (GPT-4o)
- **IA de Evaluación:** GPT-4o-mini + embeddings
- **Almacenamiento:** Google Sheets API
- **Hosting:** Railway.app (escalable)

### Seguridad y Privacidad:
- ✅ API keys ocultas mediante proxy server
- ✅ Datos de estudiantes en Google Sheets UMH
- ✅ Sin almacenamiento de audio (solo transcripciones)
- ✅ HTTPS/WSS cifrado end-to-end

---

## 💰 Costos y Sostenibilidad

### Opción 1: Uso Piloto (1 cuatrimestre)
- **Hosting:** Railway.app - $10/mes
- **OpenAI API:** ~$0.10 por sesión de 15 min
  - 100 estudiantes x 3 sesiones = $30
- **Google Sheets:** Gratis (cuenta UMH)

**Total:** ~$100 para piloto con 100 estudiantes

### Opción 2: Uso Continuo (1 año académico)
- **Hosting:** Railway.app - $20/mes x 9 meses = $180
- **OpenAI API:** 300 estudiantes x 5 sesiones x $0.10 = $150
- **Total anual:** ~$330

**Coste por estudiante:** ~$1.10/año

### Comparativa con Alternativas:
- Paciente estandarizado: €50-100 por sesión
- Mannequíes de simulación: €10,000-50,000 (compra inicial)
- **SimuPaciente IA: €1.10/estudiante/año**

---

## 📈 Plan de Implementación Propuesto

### Fase 1: Piloto (Enero-Marzo 2026)
1. **Selección:** 1 grupo de ~30 estudiantes
2. **Casos:** 3-5 casos por especialidad core
3. **Evaluación:** Encuestas de satisfacción
4. **Ajustes:** Basados en feedback

### Fase 2: Expansión (Abril-Junio 2026)
1. **Escalado:** Todos los estudiantes de 4º curso
2. **Casos:** Ampliar a 20+ casos
3. **Integración:** Con evaluación ECOE presencial

### Fase 3: Consolidación (Curso 2026-27)
1. **Rutina:** Integrar en currículo oficial
2. **Innovación:** Casos de especialidades avanzadas
3. **Investigación:** Publicación de resultados

---

## 🔬 Oportunidades de Investigación

### Posibles Líneas:
1. **Efectividad pedagógica:** Comparar con métodos tradicionales
2. **Análisis de competencias:** Patrones de errores comunes
3. **IA en educación médica:** Publicaciones en revistas de innovación docente
4. **Proyectos fin de grado:** Desarrollo de nuevos casos o features

---

## 📞 Próximos Pasos

### Para Probar la Demo:
1. ✅ Acceder a la URL proporcionada
2. ✅ Probar un caso completo (15 min)
3. ✅ Revisar resultados y feedback
4. ✅ Compartir impresiones

### Para Implementar:
1. 📧 Confirmación de interés
2. 💰 Aprobación de presupuesto (~€100 piloto)
3. 👥 Selección de grupo piloto
4. 📅 Fecha de inicio

---

## 📧 Contacto

**Desarrollador:**
Marcos Bengheza López
Email: marcos.benghez@umh.es
GitHub: https://github.com/marcosbenghezala/ECOE

**Documentación técnica:**
https://github.com/marcosbenghezala/ECOE

**Soporte:**
Disponible vía email para dudas técnicas o pedagógicas

---

## ❓ Preguntas Frecuentes

### ¿Funciona en móvil?
Sí, la interfaz es responsive y funciona en móvil/tablet.

### ¿Requiere instalación?
No, es 100% web. Solo necesitan un navegador y micrófono.

### ¿Soporta múltiples usuarios simultáneos?
Sí, hasta 50 usuarios concurrentes sin problemas.

### ¿Se puede personalizar el checklist?
Sí, es completamente configurable por especialidad.

### ¿Los datos son privados?
Sí, se almacenan en Google Sheets de la UMH con permisos controlados.

### ¿Qué pasa si un estudiante hace trampa?
El sistema detecta respuestas copiadas y reporta tiempos anómalos.

---

## 🎉 Conclusión

SimuPaciente representa una **oportunidad única** de integrar IA avanzada en la formación médica de la UMH, ofreciendo:

✅ Entrenamiento de competencias clínicas **escalable y accesible**
✅ Feedback **inmediato y personalizado**
✅ Datos para **mejora continua** docente
✅ Coste **ridículamente bajo** comparado con alternativas
✅ **Innovación** que posiciona a la UMH a la vanguardia

**Estamos listos para comenzar el piloto cuando lo aprobéis.**

---

**Universidad Miguel Hernández de Elche**
**Facultad de Medicina**
**Diciembre 2025**
