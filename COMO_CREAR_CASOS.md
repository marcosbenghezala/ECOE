# Cómo crear casos (SimuPaciente)

El backend genera automáticamente el prompt del paciente a partir de `datos_paciente` para evitar contradicciones (p. ej. primero decir “no tomo nada” y luego listar fármacos). La idea es que `datos_paciente` sea la **fuente de verdad canónica** basada en **hechos estructurados** (no en 130 frases redactadas).

## Esquema simple (recomendado)

Los casos nuevos deben usar este esquema:

- `datos_paciente.frases`: 3–4 frases clave (motivo, relato libre, ICE).
- `datos_paciente.personalidad`: rasgos + verbosidad + registro.
- `datos_paciente.hechos`: hechos clínicos estructurados (sí/no/valores/listas).
- `datos_paciente.checklist_overrides`: opcional para forzar algún NO.

No es necesario rellenar `respuesta_corta`/`respuesta_detalle` por cada ítem: eso queda solo como compatibilidad legacy.

## Estado actual

Hay un caso de ejemplo ya creado: `TO_GITHUB/casos_procesados/caso_dolor_toracico_iam_001.json`.

El endpoint `/api/cases`:
- Ignora ficheros que empiezan por `_` (por eso el template no se lista).
- Lista los casos `.json` reales que haya en `TO_GITHUB/casos_procesados/`.

## A) Quickstart (15–20 min)

1. Copia `TO_GITHUB/casos_procesados/_TEMPLATE_CASO.json`.
2. Renómbralo a `TO_GITHUB/casos_procesados/<id>.json` (ej: `caso_disnea_001.json`).
3. Dentro del archivo, pon exactamente el mismo valor en `"id": "<id>"`.
4. Rellena `informacion_paciente`, `motivo_consulta`, `sintomas_principales`.
5. Rellena `datos_paciente`:
   - `frases` (motivo + relato + ICE)
   - `personalidad`
   - `hechos` (mínimo: HEA/SOCRATES + antecedentes + medicación + alergias + hábitos + 3–4 ROS/negativos importantes)
6. Guarda y verifica que el JSON es válido (sin comas extra).
7. Reinicia backend o redeploy: el caso aparecerá en `/api/cases`.

## B) Reglas de oro (para que NO haya contradicciones)

- `datos_paciente` es **tu verdad absoluta**. Si un dato importante no está ahí, el paciente dirá “no lo sé / no me he fijado”.
- Respuestas **cortas** por defecto: 1–2 frases, 10–20 palabras.
- Mantén consistencia: si te preguntan lo mismo dos veces, responde igual.
- Evita técnica médica: el paciente habla coloquial.
- Español de España (sin modismos latinoamericanos).
- Regla práctica: **si el checklist maestro tiene ese ítem y aplica al caso, rellénalo** (o pon `tiene: false` si es un negativo relevante).

## ⚠️ IMPORTANTE: `items_activos`

El campo `items_activos` en el JSON del caso **no se usa** para activar/desactivar ítems en el runtime actual.

Actualmente:
- La activación/evaluación de ítems se decide de forma automática (por el backend/evaluador) en función de `sintomas_principales` y `contexto_generado` (y el checklist maestro).
- El paciente responde según `datos_paciente` (respuestas canónicas).

¿Qué significa esto?
- No importa qué pongas en `items_activos` para el funcionamiento del paciente.
- Lo importante es rellenar bien `datos_paciente` con respuestas canónicas.

Recomendación:
- Puedes dejar `items_activos` como `[]` o directamente omitirlo (opcional).

## C) Estructura mínima recomendada del caso

Campos principales:
- `id` (obligatorio) + nombre del fichero igual.
- `titulo`, `especialidad`, `dificultad`, `duracion_estimada` (recomendados).
- `motivo_consulta` (obligatorio).
- `informacion_paciente` (obligatorio).
- `sintomas_principales` (recomendado; ayuda a evaluadores).
- `datos_paciente` (obligatorio para casos nuevos).

Campos opcionales:
- `contexto_generado`, `personalidad_generada` (útiles si NO contradicen `datos_paciente`).
- `multimedia` (ECG, analítica, etc).
- `instrucciones` (objetivos del caso).
- `presentacion_estudiante` (solo documentación del checklist; no afecta al prompt del paciente).

## D) Cómo rellenar `datos_paciente`

### Formato por item

Usa hechos ligeros. Patrones válidos:

```json
false
```

```json
{ "tiene": true, "nota": "opresivo 8/10", "lista": ["..."] }
```

```json
["Enalapril 10 mg (1-0-0)", "Atorvastatina 20 mg (0-0-1)"]
```

```json
"En el centro del pecho"
```

### Cuándo usar `tiene: true` vs `false` vs omitir

- `tiene: true`: el síntoma/dato existe.
- `tiene: false`: el síntoma/dato NO existe (incluye negativos importantes).
- Omitir el campo: solo si no es relevante y prefieres que el paciente diga “no lo sé / no me he fijado”.

### ¿Qué campos son obligatorios vs opcionales?

- Obligatorios (siempre): `id`, `motivo_consulta`, `informacion_paciente`, `datos_paciente`.
- Recomendados (casi siempre): HEA/SOCRATES + ICE + antecedentes + medicación + alergias + hábitos + generales.
- Opcionales: ROS por sistemas completos (rellenar según el caso), psicosociales (si quieres que el caso tenga contexto real), multimedia e instrucciones.

### Síntomas negativos (evitar ambigüedad)

Usa `false` o `{ "tiene": false }` en el hecho correspondiente.

Ejemplo (síncope negativo):

```json
"ros": {
  "cardiovascular": {
    "sincope": false
  }
}
```

### ICE (Ideas/Concerns/Expectations)

Se escribe en `datos_paciente.frases.ice` (texto libre, 1 frase cada uno):

```json
"frases": {
  "ice": {
    "ideas": "Creo que puede ser algo del corazón.",
    "concerns": "Me preocupa que sea grave.",
    "expectations": "Que me hagan pruebas."
  }
}
```

### Hábitos (estructura simple)

```json
"habitos": {
  "tabaco": { "tiene": true, "cantidad": "10 cig/día", "duracion": "5 años" },
  "alcohol": false,
  "drogas": false,
  "actividad_fisica": "Camino 30 min 3 veces/semana"
}
```

## E) Checklist maestro y mapeo (cómo se conecta todo)

- Fuente de verdad del checklist: `TO_GITHUB/data/master_items.json`.
- El backend convierte `datos_paciente` en “hechos canónicos” con `TO_GITHUB/simulador/patient_prompt.py`.
- No necesitas escribir 130 frases: con **hechos** + 3–4 **frases clave** el prompt se genera solo y evita contradicciones.

### Ejemplos de mapeo (orientativo)

El template `TO_GITHUB/casos_procesados/_TEMPLATE_CASO.json` ya tiene la estructura esperada. Algunos ejemplos:

- `SOCR_01` (localización) → `datos_paciente.hechos.hea.localizacion`
- `SOCR_04` (irradiación) → `datos_paciente.hechos.hea.irradiacion`
- `GEN_01` (fiebre) → `datos_paciente.hechos.generales.fiebre`
- `RESP_01` (tos) → `datos_paciente.hechos.ros.respiratorio.tos`
- `CARDIO_01` (dolor torácico) → `datos_paciente.hechos.ros.cardiovascular.dolor_toracico`
- `AP_11` (medicación) → `datos_paciente.hechos.medicacion_actual`

### Overrides (cuando no quieres tocar `hechos`)

Si quieres forzar un NO rápidamente:

```json
"checklist_overrides": {
  "RESP_07": false,
  "hemoptisis": false
}
```

## F) Checklist de calidad (antes de subir a Railway)

- ✅ El JSON es válido.
- ✅ `id` = nombre del fichero.
- ✅ Todos los datos importantes están en `datos_paciente` (no solo en `contexto_generado`).
- ✅ No hay contradicciones entre `datos_paciente`, `contexto_generado` y `personalidad_generada`.
- ✅ Respuestas en español de España, cortas y naturales.
- ✅ No quedan textos “COMPLETAR” dentro del caso final.
