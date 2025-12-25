# 🏥 SimuPaciente - Simulador de Pacientes Virtuales

Sistema de simulación de entrevistas clínicas con pacientes virtuales con voz, utilizando IA generativa (OpenAI GPT-4o + Realtime API) para práctica y evaluación de estudiantes de medicina.

**Universidad Miguel Hernández de Elicante**

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Tecnologías](#-tecnologías)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API Endpoints](#-api-endpoints)
- [Documentación](#-documentación)
- [Problemas Conocidos](#-problemas-conocidos)
- [Roadmap](#-roadmap)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

---

## ✨ Características

### Funcionalidades Implementadas ✅

- **Dashboard Interactivo**: Selección de casos clínicos con información detallada
- **Simulación con Audio en Tiempo Real**: Conversación por voz con paciente virtual usando OpenAI Realtime API
- **Captura de Audio**: MediaRecorder API para grabar voz del estudiante
- **Reflexión Clínica**: preguntas de razonamiento clínico definidas por cada caso
- **Evaluación Automatizada**:
  - Análisis de la entrevista con checklist determinista (regex + keywords)
  - Evaluación de reflexión clínica con reglas clínicas básicas
  - Puntuación detallada por ítems
- **Pantalla de Resultados**: Visualización completa de la evaluación con:
  - Puntuación general y por categorías
  - Ítems completados y no completados
  - Feedback personalizado
  - Fortalezas y áreas de mejora
- **Integración con Google Sheets**: Registro de sesiones y resultados
- **Diseño Responsivo**: Interfaz moderna con Tailwind CSS v4
- **Branding UMH**: Colores institucionales en sistema OKLCH

### En Desarrollo ⚠️

- **Audio Playback**: Reproducción de respuestas del paciente virtual (pendiente Web Audio API)
- **Modo DEMO**: Fallback cuando OpenAI Realtime API no está disponible
- **Timeout Frontend**: Prevenir cuelgue indefinido en conexión WebSocket

---

## 🏗️ Arquitectura

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   React SPA     │◄────────┤  Flask Server    │◄────────┤  OpenAI APIs    │
│  (Frontend)     │  REST/WS│   (Backend)      │  HTTPS  │                 │
├─────────────────┤         ├──────────────────┤         ├─────────────────┤
│ • Dashboard     │         │ • REST API       │         │ • Realtime API  │
│ • Simulation    │         │ • WebSocket      │         │ • GPT-4o-mini   │
│ • Reflection    │         │ • Evaluation     │         │                 │
│ • Results       │         │ • Google Sheets  │         └─────────────────┘
└─────────────────┘         └──────────────────┘
     :5173                       :5001
```

### Flujo de Datos

1. **Inicio de Sesión**: Frontend → `POST /api/simulation/start` → Backend crea sesión
2. **WebSocket Audio**: Frontend ↔ `WS /ws/realtime/{session_id}` ↔ Backend ↔ OpenAI
3. **Evaluación**: Frontend → `POST /api/simulation/evaluate` → Backend → OpenAI → Google Sheets
4. **Resultados**: Backend devuelve JSON con puntuación, feedback y detalles

---

## 🛠️ Tecnologías

### Frontend
- **React 19.2.0** - Framework UI
- **TypeScript 5.6.2** - Type safety
- **Vite 6.0.0** - Build tool & dev server
- **Tailwind CSS 4.0.0** - Styling framework
- **Radix UI** - Componentes accesibles
- **Lucide React** - Iconos
- **MediaRecorder API** - Captura de audio

### Backend
- **Python 3.9+** - Lenguaje servidor
- **Flask 3.0.0** - Web framework
- **Flask-Sock** - WebSocket support
- **OpenAI SDK 2.8.1** - APIs de IA
- **gspread** - Google Sheets integration

### APIs Externas
- **OpenAI Realtime API** - Conversación de voz en tiempo real
- **OpenAI GPT-4o-mini** - (opcional) Evaluación de reflexión clínica
- **Google Sheets API** - Persistencia de datos

---

## 📦 Instalación

### Requisitos Previos

- Node.js 18+ y npm
- Python 3.9+
- Cuenta de OpenAI con acceso a Realtime API
- (Opcional) Cuenta de servicio de Google Cloud para Sheets

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/simulador.git
cd simulador
```

### 2. Configurar Backend

```bash
# Instalar dependencias Python
pip3 install -r requirements.txt
```

### 3. Configurar Variables de Entorno

**IMPORTANTE:** El proyecto usa variables de entorno para secretos. **NUNCA** commitees archivos con secretos reales.

Crea un archivo `.env` en la raíz del proyecto:

```bash
# .env (NO commitear - ya está en .gitignore)
OPENAI_API_KEY=sk-proj-...tu-api-key...
```

**Opcional - Google Sheets (RESUMEN + detalle por simulación):**

Si quieres guardar resultados en Google Sheets al finalizar `POST /api/simulation/evaluate`:

```bash
# En .env (o Railway Variables):
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_SPREADSHEET_ID=15dJ9GPUvA0LFfoJShS29ujV_YsI_48NsBu010cq2vk0
GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"..."}'
```

El spreadsheet debe tener una pestaña llamada `RESUMEN` con cabeceras en A–G:

`Timestamp | Estudiante | Email | Caso | Duración (min) | Puntuación | Ver Detalles`

Para obtener las credenciales:
1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear proyecto nuevo o seleccionar existente
3. Habilitar Google Sheets API
4. Crear cuenta de servicio (Service Account)
5. Descargar JSON de credenciales
6. Compartir el spreadsheet con el email de la service account (rol Editor)
7. Copiar TODO el contenido del JSON en la variable `GOOGLE_SHEETS_CREDENTIALS`

### 4. Build del Frontend

El backend sirve el frontend compilado desde `frontend/dist`:

```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Iniciar Servidor

El servidor Flask sirve tanto el frontend (en `/`) como la API (en `/api`):

```bash
python3 colab_server.py
```

El servidor estará disponible en:
- **Frontend:** http://localhost:8080
- **API:** http://localhost:8080/api
- **WebSocket:** ws://localhost:8080/ws/realtime/{session_id}

### Modo Desarrollo (Opcional)

Si estás desarrollando el frontend y quieres hot-reload:

**Terminal 1 - Backend:**
```bash
python3 colab_server.py
# API en http://localhost:8080/api
```

**Terminal 2 - Frontend Dev Server:**
```bash
cd frontend
npm run dev
# Frontend con hot-reload en http://localhost:5173
```

En este modo, el frontend dev (puerto 5173) hace peticiones al backend (puerto 8080).

---

## 🚀 Deployment

Para desplegar la aplicación en producción, consulta **[DEPLOY_RAILWAY.md](../DEPLOY_RAILWAY.md)** en la raíz del proyecto.

La guía incluye instrucciones paso a paso para:
- Crear cuenta en Railway.app
- Configurar variables de entorno
- Generar dominio público
- Solución de problemas comunes

**Tiempo estimado de deployment:** 10 minutos

---

## 🚀 Uso

### 1. Acceder a la Aplicación
Abrir http://localhost:8080 en el navegador

### 2. Seleccionar Caso Clínico
- Ingresar datos del estudiante (nombre, código, email)
- Seleccionar caso clínico del catálogo disponible

### 3. Realizar Simulación
- Click en "Iniciar Entrevista"
- Permitir acceso al micrófono cuando el navegador lo solicite
- **Push-to-Talk:** Mantener presionado el botón azul para hablar
- Soltar el botón para que el paciente virtual responda
- El paciente responderá con voz sintética en tiempo real

### 4. Completar Reflexión Clínica
Después de la simulación, responde las preguntas definidas en el caso.

### 5. Ver Resultados
La pantalla de resultados muestra:
- **Puntuación general** y calificación (SB/NT/AP/SF/SS)
- **Resultados por bloque:** Introducción, Motivo consulta, HEA, Antecedentes, etc.
- **Ítems cumplidos/no cumplidos** con detalles
- **Feedback de las preguntas de desarrollo** con respuestas esperadas
- Opción de descargar PDF (próximamente)

### Creación de Casos Clínicos

Los casos se pueden crear en formato **JSON** (recomendado) o **pickle** (legacy).

**Formato JSON recomendado** (`../casos_procesados/mi_caso.json`):

```json
{
  "id": "mi_caso_id",
  "autor_profesor": "profesor@umh.es",
  "titulo": "Dolor torácico en varón de 55 años",
  "especialidad": "Cardiología",
  "dificultad": "Intermedio",
  "duracion_estimada": 15,
  "motivo_consulta": "Paciente que acude por dolor torácico...",
  "informacion_paciente": {
    "nombre": "Juan García",
    "edad": 55,
    "genero": "male",
    "ocupacion": "Comercial"
  },
  "sintomas_principales": ["dolor torácico", "sudoración"],
  "diagnostico_principal": "Infarto agudo de miocardio",
  "diagnosticos_diferenciales": ["Angina inestable", "Pericarditis"],
  "pruebas_esperadas": ["ECG urgente", "Troponinas"],
  "antecedentes": {
    "personales": ["HTA", "Tabaquismo"],
    "familiares": ["Padre IAM a los 60 años"]
  },
  "preguntas_reflexion": [
    {
      "id": 1,
      "question": "Resume el motivo de consulta y los síntomas más importantes.",
      "field_name": "resumen_caso",
      "max_score": 100,
      "min_words": 6,
      "rubric": [
        { "key": "sintoma_principal", "label": "Menciona dolor torácico", "weight": 30, "terms": ["dolor torácico", "dolor en el pecho"] },
        { "key": "irradiacion", "label": "Menciona irradiación", "weight": 25, "terms": ["irradiado", "brazo izquierdo", "mandíbula"] },
        { "key": "tiempo", "label": "Menciona inicio o duración", "weight": 25, "terms": ["hace", "desde", "horas", "inicio brusco"] },
        { "key": "vegetativos", "label": "Síntomas vegetativos", "weight": 20, "terms": ["sudoración", "náuseas", "disnea"] }
      ]
    },
    {
      "id": 2,
      "question": "¿Cuál es tu diagnóstico más probable? Justifica con datos clínicos.",
      "field_name": "diagnostico_principal",
      "max_score": 100,
      "min_words": 3,
      "rubric": [
        { "key": "dx", "label": "Diagnóstico principal", "weight": 60, "terms": ["infarto agudo de miocardio", "iam", "síndrome coronario agudo"] },
        { "key": "datos", "label": "Justifica con datos clínicos", "weight": 40, "terms": ["dolor opresivo", "irradiación", "sudoración", "náuseas"] }
      ]
    }
  ],

}
```

Ejemplo completo listo para usar: `../casos_procesados/iam_001.json`.

Actualmente no hay más casos precargados.

Para crear un nuevo caso:
- Copia `../casos_procesados/_TEMPLATE_CASO.json`
- Renómbralo a `caso_<nombre>_001.json`
- Rellena los campos según `TO_GITHUB/COMO_CREAR_CASOS.md`
  
El template se ignora en `/api/cases` (no aparece en el dashboard).

---

## 📁 Estructura del Proyecto

```
simulador/
├── .gitignore                    # Archivos a ignorar (secretos, .env, etc.)
├── frontend/                     # React 19 + TypeScript
│   ├── src/
│   │   ├── components/           # Componentes React
│   │   │   ├── dashboard.tsx
│   │   │   ├── simulation-interface-v3.tsx
│   │   │   ├── clinical-reflection.tsx
│   │   │   ├── results-screen-v3.tsx
│   │   │   ├── case-preview.tsx
│   │   │   └── ui/               # Componentes UI (Radix)
│   │   ├── lib/                  # Utilidades
│   │   │   └── utils.ts
│   │   ├── types/                # TypeScript types
│   │   │   └── index.ts
│   │   ├── App.tsx               # Componente principal
│   │   └── main.tsx              # Entry point
│   ├── dist/                     # Build compilado (servido por Flask)
│   ├── package.json
│   └── vite.config.ts
├── ../casos_procesados/          # Casos clínicos (JSON + pickle)
│   ├── _TEMPLATE_CASO.json       # Template (NO se lista en /api/cases)
│   └── *.bin                     # Casos legacy (pickle)
├── data/                         # Checklist master y utilidades
│   ├── master-checklist-v2.json  # Checklist 180 ítems
│   ├── iam_gold_expected.json    # Verdades de oro para pruebas
│   └── iam_gold_expected.csv
├── sessions/                     # Sesiones de simulación (runtime)
│   └── *.json
├── colab_server.py               # Backend Flask principal
├── evaluator_production.py       # Evaluador único (checklist v2)
├── realtime_voice.py             # WebSocket OpenAI Realtime API
├── requirements.txt              # Dependencias Python
├── .env                          # Variables entorno (NO commitear)
└── README.md                     # Este archivo
```

---

## 🔌 API Endpoints

### REST Endpoints

#### `POST /api/simulation/start`
Iniciar nueva sesión de simulación

**Request:**
```json
{
  "student_name": "María García",
  "student_code": "12345678",
  "student_email": "maria@example.com",
  "case_id": "caso_1"
}
```

**Response:**
```json
{
  "session_id": "abc123...",
  "case_data": {
    "id": "caso_1",
    "title": "Dolor Torácico",
    "description": "...",
    ...
  }
}
```

#### `POST /api/simulation/evaluate`
Evaluar simulación completada

**Request:**
```json
{
  "session_id": "abc123...",
  "reflection": {
    "diagnostico_principal": "...",
    "diagnosticos_diferenciales": "...",
    "pruebas_diagnosticas": "...",
    "plan_manejo": "..."
  }
}
```

**Response (schema `evaluation.production.v1`):**
```json
{
  "schema_version": "evaluation.production.v1",
  "scores": {
    "global": { "score": 62.5, "max": 100, "percentage": 62.5 },
    "checklist": { "score": 88, "max": 180, "percentage": 48.9, "weighted": 34.2 },
    "development": { "percentage": 95.0, "weighted": 28.5 }
  },
  "items": [
    { "id": "B2_001", "bloque": "B2_HEA", "descripcion": "Inicio del dolor", "done": true, "score": 1, "max_score": 1 }
  ],
  "blocks": [
    { "id": "B2_HEA", "name": "HEA", "score": 10, "max": 20, "percentage": 50.0, "items": [] }
  ],
  "development": {
    "percentage": 95.0,
    "questions": [
      { "question": "Resumen del caso", "answer": "...", "score": 90, "max_score": 100, "feedback": "Cumple: ..." }
    ]
  },
  "survey": {}
}
```

#### `GET /api/cases`
Obtener lista de casos clínicos disponibles

**Response:**
```json
{
  "cases": [
    {
      "id": "caso_1",
      "title": "Dolor Torácico",
      "description": "...",
      "category": "Cardiología",
      "difficulty": "Medio"
    },
    ...
  ]
}
```

### WebSocket Endpoints

#### `WS /ws/realtime/{session_id}`
Conexión WebSocket para audio en tiempo real con OpenAI

**Mensajes del Cliente:**
```json
{
  "type": "audio",
  "audio": "base64_encoded_audio_pcm16..."
}
```

**Mensajes del Servidor:**
```json
{"type": "connected", "message": "OpenAI Realtime API conectada"}
{"type": "agent_audio", "audio": "base64_pcm16..."}
{"type": "response_done"}
{"type": "error", "error": "..."}
```

---

## 📚 Documentación

La documentación técnica completa está en la carpeta `.claude/`:

- **[README.md](.claude/README.md)** - Índice de toda la documentación
- **[ESTADO_ACTUAL_PROYECTO.md](.claude/ESTADO_ACTUAL_PROYECTO.md)** - Estado completo del proyecto:
  - Estructura detallada
  - Documentación de endpoints
  - Análisis de problemas
  - Soluciones implementadas
  - Código de referencia
  - Troubleshooting
  - Próximos pasos
- **[SESION_2025-12-03.md](.claude/SESION_2025-12-03.md)** - Trabajo de sesión anterior

---

## ⚠️ Problemas Conocidos

### ✅ Bugs Corregidos (v0.9)

- **BUG #1 - Audio solapado**: ✅ Implementada cola FIFO para reproducción secuencial de chunks PCM16
- **BUG #2 - Multimedia 404**: ✅ Desactivada multimedia de prueba hardcodeada
- **BUG #3 - combinedTotal undefined**: ✅ Calculado desde evaluationItems
- **BUG #4 - Paciente da demasiadas pistas**: ✅ Prompt reforzado con reglas estrictas SOCRATES
- **BUG #5 - Feedback sin respuesta esperada**: ✅ Formato actualizado con Tu respuesta/Respuesta esperada/Feedback
- **BUG #6 - Respuestas cruzadas en reflexión**: ✅ Agregado resumen_caso al prompt de evaluación

### Problemas Activos

### 1. OpenAI Realtime API No Conecta
**Síntoma:** WebSocket falla con `ConnectionClosed: 1005`

**Posibles Causas:**
- API key sin créditos o sin acceso a Realtime API
- Red universitaria bloqueando WebSocket
- Firewall/proxy interceptando SSL

**Solución Actual:**
- Verificar que `OPENAI_API_KEY` está configurada correctamente
- Comprobar que la API key tiene acceso a Realtime API (beta)
- Timeout de 15 segundos con reintentos automáticos (3 intentos)

---

## 🗺️ Roadmap

### Versión 1.0 (Diciembre 2025)
- ✅ Sistema de simulación con WebSocket
- ✅ Evaluación automatizada con IA
- ✅ Pantalla de resultados completa
- ⚠️ Timeout y modo DEMO
- ⚠️ Reproducción de audio
- 🔲 Exportación de resultados a PDF

### Versión 1.1 (Q1 2026)
- 🔲 Dashboard de analytics para profesores
- 🔲 Más casos clínicos (10+ casos)
- 🔲 Feedback en tiempo real durante simulación
- 🔲 Sistema de logros y gamificación

### Versión 2.0 (Q2 2026)
- 🔲 Exploración física virtual (3D)
- 🔲 Solicitud de pruebas diagnósticas
- 🔲 Modo multijugador (varios estudiantes, un caso)
- 🔲 Integración con LMS (Moodle, Canvas)

---

## 🤝 Contribución

Este proyecto es parte de un proyecto de investigación educativa de la Universidad Miguel Hernández.

Para contribuir:
1. Fork el repositorio
2. Crear branch de feature (`git checkout -b feature/amazing-feature`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Abrir Pull Request

---

## 📄 Licencia

Copyright © 2025 Universidad Miguel Hernández de Elicante

Este software es para uso educativo e investigación. Todos los derechos reservados.

---

## 📞 Contacto

**Proyecto:** SimuPaciente
**Universidad:** Miguel Hernández de Elicante
**Email:** [Contacto institucional]

---

## 🙏 Agradecimientos

- OpenAI por Realtime API y GPT-4o
- Estudiantes de medicina participantes en las pruebas
- Profesores del departamento de medicina de la UMH
- Comunidad open source de React, Vite, Flask

---

**Última actualización:** 17 de diciembre de 2025
**Versión:** 0.9.5 (Release Candidate)
