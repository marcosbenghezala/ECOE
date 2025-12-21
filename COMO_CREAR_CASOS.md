# Cómo crear casos (SimuPaciente)

El backend genera automáticamente el prompt del paciente a partir de `datos_paciente` para evitar contradicciones (p. ej. primero decir “no tomo nada” y luego listar fármacos). La idea es que `datos_paciente` sea la **fuente de verdad canónica**.

## A) Quickstart (15–20 min)

1. Copia `TO_GITHUB/casos_procesados/_TEMPLATE_CASO.json`.
2. Renómbralo a `TO_GITHUB/casos_procesados/<id>.json` (ej: `caso_disnea_001.json`).
3. Dentro del archivo, pon exactamente el mismo valor en `"id": "<id>"`.
4. Rellena `informacion_paciente`, `motivo_consulta`, `sintomas_principales`.
5. Rellena `datos_paciente` (mínimo: HEA + antecedentes + medicación + alergias + hábitos + ICE).
6. Guarda y verifica que el JSON es válido (sin comas extra).
7. Reinicia backend o redeploy: el caso aparecerá en `/api/cases`.

## B) Reglas de oro (para que NO haya contradicciones)

- `datos_paciente` es **tu verdad absoluta**. Si un dato importante no está ahí, el paciente dirá “no lo sé / no me he fijado”.
- Respuestas **cortas** por defecto: 1–2 frases, 10–20 palabras.
- Mantén consistencia: si te preguntan lo mismo dos veces, responde igual.
- Evita técnica médica: el paciente habla coloquial.
- Español de España (sin modismos latinoamericanos).

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

## D) Cómo rellenar `datos_paciente`

### Formato por item

Usa este patrón:

```json
"alergias": {
  "tiene": false,
  "respuesta_corta": "No, que yo sepa no tengo alergias.",
  "respuesta_detalle": "No tengo alergias conocidas a medicamentos ni alimentos."
}
```

Claves recomendadas:
- `tiene`: `true`/`false` (para sí/no).
- `respuesta_corta`: lo que dice por defecto.
- `respuesta_detalle`: si el estudiante insiste (“¿algo más?”, “¿cuál exactamente?”).
- `lista`: si hay elementos a listar (medicación, antecedentes, síntomas asociados).

### Cuándo usar `tiene: true` vs `false` vs omitir

- `tiene: true`: el síntoma/dato existe.
- `tiene: false`: el síntoma/dato NO existe (incluye negativos importantes).
- Omitir el campo: solo si no es relevante y prefieres que el paciente diga “no lo sé / no me he fijado”.

### Síntomas negativos (evitar ambigüedad)

Mal:
- “No” (sin contexto)

Bien:
- `respuesta_corta`: “No, no me he desmayado.”
- `respuesta_detalle`: “No, no he perdido el conocimiento en ningún momento.”

### ICE (Ideas/Concerns/Expectations)

Ejemplos:
- `ice_ideas`: “Creo que puede ser asma / algo del corazón / una apendicitis…”
- `ice_concerns`: “Me preocupa que sea grave.”
- `ice_expectations`: “Que me miren rápido y me hagan pruebas.”

### Hábitos tóxicos (estructura completa)

```json
"habitos_toxicos": {
  "tabaco": { "tiene": true, "cantidad": "10 cig/día", "duracion": "5 años", "respuesta_corta": "...", "respuesta_detalle": "..." },
  "alcohol": { "tiene": false, "respuesta_corta": "No, no suelo beber.", "respuesta_detalle": "..." },
  "drogas": { "tiene": false, "respuesta_corta": "No.", "respuesta_detalle": "..." }
}
```

## E) Tabla de items (guía práctica)

Esta tabla refleja las claves recomendadas en `datos_paciente`. Puedes añadir más claves si las necesitas.

| Item Checklist (clave) | ¿Obligatorio? | Tipo | Ejemplo `datos_paciente` |
|---|---:|---|---|
| `tiempo_evolucion` | Sí | Objeto | `{ "respuesta_corta": "Desde hace 2 horas", "respuesta_detalle": "..." }` |
| `inicio` | Recomendado | Objeto | `{ "respuesta_corta": "Empezó de repente", "respuesta_detalle": "..." }` |
| `localizacion_dolor` | Sí (si hay dolor) | Objeto | `{ "respuesta_corta": "En el centro del pecho", "respuesta_detalle": "..." }` |
| `caracteristicas_dolor` | Sí (si hay dolor/síntoma) | Objeto | `{ "respuesta_corta": "Como una presión", "respuesta_detalle": "..." }` |
| `intensidad_dolor` | Recomendado | Objeto | `{ "respuesta_corta": "Un 8/10", "respuesta_detalle": "..." }` |
| `irradiacion` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `factores_alivio` | Recomendado | Objeto | `{ "tiene": false, "respuesta_corta": "No mejora", "respuesta_detalle": "..." }` |
| `factores_empeoramiento` | Recomendado | Objeto | `{ "tiene": true, "respuesta_corta": "Al caminar", "respuesta_detalle": "..." }` |
| `sintomas_asociados` | Recomendado | Objeto+lista | `{ "tiene": true, "lista": ["Náuseas"], "respuesta_corta": "...", "respuesta_detalle": "..." }` |
| `antecedentes_personales` | Sí | Objeto+lista | `{ "tiene": true, "lista": ["Asma"], "respuesta_corta": "...", "respuesta_detalle": "..." }` |
| `antecedentes_familiares` | Recomendado | Objeto+lista | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `medicacion_actual` | Sí | Objeto+lista | `{ "tiene": true, "lista": ["Salbutamol"], "respuesta_corta": "...", "respuesta_detalle": "..." }` |
| `alergias` | Sí | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `habitos_toxicos` | Recomendado | Objeto anidado | `{ "tabaco": {...}, "alcohol": {...}, "drogas": {...} }` |
| `ice_ideas` | Recomendado | Objeto | `{ "respuesta_corta": "Creo que...", "respuesta_detalle": "..." }` |
| `ice_concerns` | Recomendado | Objeto | `{ "respuesta_corta": "Me preocupa...", "respuesta_detalle": "..." }` |
| `ice_expectations` | Recomendado | Objeto | `{ "respuesta_corta": "Quiero que...", "respuesta_detalle": "..." }` |
| `fiebre` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No he tenido fiebre", "respuesta_detalle": "..." }` |
| `tos` | Opcional | Objeto | `{ "tiene": true, "respuesta_corta": "Sí, tos seca", "respuesta_detalle": "..." }` |
| `expectoracion` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `disnea` | Opcional | Objeto | `{ "tiene": true, "respuesta_corta": "Me falta el aire", "respuesta_detalle": "..." }` |
| `nauseas` | Opcional | Objeto | `{ "tiene": true, "respuesta_corta": "Sí", "respuesta_detalle": "..." }` |
| `vomitos` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `diarrea` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `disuria` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `hematuria` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `palpitaciones` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `sincope` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `edemas` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `ortopnea` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `disnea_paroxistica_nocturna` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |
| `claudicacion` | Opcional | Objeto | `{ "tiene": false, "respuesta_corta": "No", "respuesta_detalle": "..." }` |

## F) Checklist de calidad (antes de subir a Railway)

- ✅ El JSON es válido.
- ✅ `id` = nombre del fichero.
- ✅ Todos los datos importantes están en `datos_paciente` (no solo en `contexto_generado`).
- ✅ No hay contradicciones entre `datos_paciente`, `contexto_generado` y `personalidad_generada`.
- ✅ Respuestas en español de España, cortas y naturales.

