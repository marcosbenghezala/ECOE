# Cómo crear casos (SimuPaciente)

El backend genera automáticamente el prompt del paciente a partir de `datos_paciente` para evitar contradicciones (p. ej. primero decir “no tomo nada” y luego listar fármacos). La idea es que `datos_paciente` sea la **fuente de verdad canónica**.

## A) Quickstart (15–20 min)

1. Copia `TO_GITHUB/casos_procesados/_TEMPLATE_CASO.json`.
2. Renómbralo a `TO_GITHUB/casos_procesados/<id>.json` (ej: `caso_disnea_001.json`).
3. Dentro del archivo, pon exactamente el mismo valor en `"id": "<id>"`.
4. Rellena `informacion_paciente`, `motivo_consulta`, `sintomas_principales`.
5. Rellena `datos_paciente` (mínimo: motivo + HEA/SOCRATES + ICE + antecedentes + medicación + alergias + hábitos + generales).
6. Guarda y verifica que el JSON es válido (sin comas extra).
7. Reinicia backend o redeploy: el caso aparecerá en `/api/cases`.

## B) Reglas de oro (para que NO haya contradicciones)

- `datos_paciente` es **tu verdad absoluta**. Si un dato importante no está ahí, el paciente dirá “no lo sé / no me he fijado”.
- Respuestas **cortas** por defecto: 1–2 frases, 10–20 palabras.
- Mantén consistencia: si te preguntan lo mismo dos veces, responde igual.
- Evita técnica médica: el paciente habla coloquial.
- Español de España (sin modismos latinoamericanos).
- Regla práctica: **si el checklist maestro tiene ese ítem y aplica al caso, rellénalo** (o pon `tiene: false` si es un negativo relevante).

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

### ¿Qué campos son obligatorios vs opcionales?

- Obligatorios (siempre): `id`, `motivo_consulta`, `informacion_paciente`, `datos_paciente`.
- Recomendados (casi siempre): HEA/SOCRATES + ICE + antecedentes + medicación + alergias + hábitos + generales.
- Opcionales: ROS por sistemas completos (rellenar según el caso), psicosociales (si quieres que el caso tenga contexto real), multimedia e instrucciones.

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

## E) Checklist maestro → claves del template (completo)

Fuente: `TO_GITHUB/data/master_items.json` (130 ítems).

### E.1 Bloques universales

| Bloque | ID | Ítem del checklist | Campo (template) |
|---|---|---|---|
| IDENTIFICACION | ID_01 | Saluda al paciente cordialmente | `presentacion_estudiante.saludo` (acción del estudiante) |
| IDENTIFICACION | ID_02 | Se presenta con nombre y rol | `presentacion_estudiante.presentacion` (acción del estudiante) |
| IDENTIFICACION | ID_03 | Confirma identidad del paciente (nombre, edad) | `presentacion_estudiante.confirma_identidad` (acción del estudiante) |
| MOTIVO_CONSULTA | MC_01 | Realiza pregunta abierta inicial | `datos_paciente.motivo_consulta` (respuesta canónica) |
| MOTIVO_CONSULTA | MC_02 | Recoge motivo principal con palabras del paciente | `datos_paciente.motivo_consulta` |
| MOTIVO_CONSULTA | MC_03 | Permite relato libre sin interrumpir | `datos_paciente.relato_libre` |
| MOTIVO_CONSULTA | MC_04 | Indaga sobre otros motivos de consulta | `datos_paciente.otros_motivos_consulta` |
| MOTIVO_CONSULTA | MC_05 | Resume y verifica comprensión del motivo | `datos_paciente.confirmacion_resumen_motivo` |
| HEA_SOCRATES | SOCR_01 | Localización exacta del síntoma | `datos_paciente.localizacion_dolor` |
| HEA_SOCRATES | SOCR_02 | Cronología e inicio del síntoma | `datos_paciente.inicio` + `datos_paciente.tiempo_evolucion` |
| HEA_SOCRATES | SOCR_03 | Características y cualidad del síntoma | `datos_paciente.caracteristicas_dolor` |
| HEA_SOCRATES | SOCR_04 | Irradiación del síntoma | `datos_paciente.irradiacion` |
| HEA_SOCRATES | SOCR_05 | Intensidad del síntoma | `datos_paciente.intensidad_dolor` |
| HEA_SOCRATES | SOCR_06 | Factores agravantes | `datos_paciente.factores_empeoramiento` |
| HEA_SOCRATES | SOCR_07 | Factores atenuantes | `datos_paciente.factores_alivio` |
| HEA_SOCRATES | SOCR_08 | Evolución temporal y patrón | `datos_paciente.patron_evolucion` |
| HEA_SOCRATES | SOCR_09 | Duración de episodios | `datos_paciente.duracion_episodios` |
| HEA_SOCRATES | SOCR_10 | Síntomas acompañantes | `datos_paciente.sintomas_asociados` |
| HEA_SOCRATES | SOCR_11 | Frecuencia o periodicidad | `datos_paciente.frecuencia_periodicidad` |
| HEA_ICE | ICE_01 | Indaga ideas del paciente sobre la causa | `datos_paciente.ice_ideas` |
| HEA_ICE | ICE_02 | Explora preocupaciones específicas | `datos_paciente.ice_concerns` |
| HEA_ICE | ICE_03 | Revisa expectativas de la consulta | `datos_paciente.ice_expectations` |
| ANTECEDENTES_PERSONALES | AP_01 | Pregunta por enfermedades crónicas | `datos_paciente.enfermedades_cronicas` |
| ANTECEDENTES_PERSONALES | AP_02 | Pregunta por cirugías previas | `datos_paciente.cirugias_previas` |
| ANTECEDENTES_PERSONALES | AP_03 | Pregunta por hospitalizaciones previas | `datos_paciente.hospitalizaciones_previas` |
| ANTECEDENTES_PERSONALES | AP_04 | Pregunta por alergias medicamentosas | `datos_paciente.alergias_medicamentosas` |
| ANTECEDENTES_PERSONALES | AP_05 | Pregunta por alergias no medicamentosas | `datos_paciente.alergias_no_medicamentosas` |
| ANTECEDENTES_PERSONALES | AP_06 | Pregunta por historia transfusional | `datos_paciente.historia_transfusional` |
| ANTECEDENTES_PERSONALES | AP_07 | Pregunta por inmunizaciones/vacunas | `datos_paciente.vacunas_inmunizaciones` |
| ANTECEDENTES_PERSONALES | AP_08 | Pregunta por historia gineco-obstétrica (si procede) | `datos_paciente.historia_gineco_obstetrica` |
| ANTECEDENTES_PERSONALES | AP_09 | Pregunta por accidentes traumáticos relevantes | `datos_paciente.traumatismos_relevantes` |
| ANTECEDENTES_PERSONALES | AP_10 | Pregunta por discapacidad o uso de prótesis | `datos_paciente.discapacidad_protesis` |
| ANTECEDENTES_PERSONALES | AP_11 | Pregunta por tratamientos actuales | `datos_paciente.medicacion_actual` (+ `datos_paciente.tratamientos_no_farmacologicos`) |
| ANTECEDENTES_PERSONALES | AP_12 | Pregunta por historia psiquiátrica relevante | `datos_paciente.historia_psiquiatrica` |
| ANTECEDENTES_FAMILIARES | AF_01 | Pregunta por patología en familiares de primer grado | `datos_paciente.patologia_familiares_primer_grado` |
| ANTECEDENTES_FAMILIARES | AF_02 | Pregunta por causa de fallecimiento de familiares | `datos_paciente.causa_fallecimiento_familiares` |
| ANTECEDENTES_FAMILIARES | AF_03 | Pregunta por muerte súbita o eventos cardiovasculares precoces | `datos_paciente.eventos_cv_precoces` |
| ANTECEDENTES_FAMILIARES | AF_04 | Pregunta por cáncer hereditario relevante | `datos_paciente.cancer_hereditario` |
| PSICOSOCIALES | PS_01 | Pregunta por situación familiar y convivencia | `datos_paciente.situacion_familiar` |
| PSICOSOCIALES | PS_02 | Pregunta por estado civil y soporte social | `datos_paciente.estado_civil_soporte_social` |
| PSICOSOCIALES | PS_03 | Pregunta por vivienda y entorno | `datos_paciente.vivienda` |
| PSICOSOCIALES | PS_04 | Pregunta por situación laboral y profesión | `datos_paciente.situacion_laboral` |
| PSICOSOCIALES | PS_05 | Pregunta por nivel educativo | `datos_paciente.nivel_educativo` |
| PSICOSOCIALES | PS_06 | Pregunta por creencias religiosas si influyen en salud | `datos_paciente.creencias_religiosas_salud` |
| PSICOSOCIALES | PS_07 | Pregunta por estrés vital reciente | `datos_paciente.estres_reciente` |
| PSICOSOCIALES | PS_08 | Pregunta por cuidador primario si aplicable | `datos_paciente.cuidador_primario` |
| PSICOSOCIALES | PS_09 | Pregunta sobre violencia o abuso (si procede y seguro) | `datos_paciente.violencia_abuso` |
| HABITOS | HAB_01 | Pregunta por tabaquismo | `datos_paciente.habitos_toxicos.tabaco` |
| HABITOS | HAB_02 | Pregunta por consumo de alcohol | `datos_paciente.habitos_toxicos.alcohol` |
| HABITOS | HAB_03 | Pregunta por consumo de otras drogas | `datos_paciente.habitos_toxicos.drogas` |
| HABITOS | HAB_04 | Pregunta por alimentación y tipo de dieta | `datos_paciente.alimentacion_dieta` |
| HABITOS | HAB_05 | Pregunta por actividad física regular | `datos_paciente.actividad_fisica` |
| HABITOS | HAB_06 | Pregunta por sueño (duración y calidad) | `datos_paciente.sueno` |
| HABITOS | HAB_07 | Pregunta por sexualidad y conductas de riesgo | `datos_paciente.sexualidad_conductas_riesgo` |
| HABITOS | HAB_08 | Pregunta por animales de compañía o exposiciones zoonóticas | `datos_paciente.animales_compania_exposiciones` |
| GENERALES | GEN_01 | Pregunta por fiebre | `datos_paciente.fiebre` |
| GENERALES | GEN_02 | Pregunta por pérdida de peso involuntaria | `datos_paciente.perdida_peso_involuntaria` |
| GENERALES | GEN_03 | Pregunta por sudoración nocturna | `datos_paciente.sudoracion_nocturna` |
| GENERALES | GEN_04 | Pregunta por astenia o cansancio | `datos_paciente.astenia` |
| GENERALES | GEN_05 | Pregunta por anorexia o pérdida de apetito | `datos_paciente.anorexia` |

### E.2 ROS por sistemas

| Sistema | ID | Ítem del checklist | Campo (template) |
|---|---|---|---|
| RESPIRATORIO | RESP_01 | Pregunta por tos | `datos_paciente.tos` |
| RESPIRATORIO | RESP_02 | Pregunta por características de la tos | `datos_paciente.caracteristicas_tos` |
| RESPIRATORIO | RESP_03 | Pregunta por disnea | `datos_paciente.disnea` |
| RESPIRATORIO | RESP_04 | Pregunta por ortopnea | `datos_paciente.ortopnea` |
| RESPIRATORIO | RESP_05 | Pregunta por disnea paroxística nocturna | `datos_paciente.disnea_paroxistica_nocturna` |
| RESPIRATORIO | RESP_06 | Pregunta por dolor pleurítico | `datos_paciente.dolor_pleuritico` |
| RESPIRATORIO | RESP_07 | Pregunta por hemoptisis | `datos_paciente.hemoptisis` |
| RESPIRATORIO | RESP_08 | Pregunta por sibilancias | `datos_paciente.sibilancias` |
| RESPIRATORIO | RESP_09 | Pregunta por exposición laboral/polvo/tabaco | `datos_paciente.exposicion_laboral_respiratoria` |
| RESPIRATORIO | RESP_10 | Pregunta por antecedentes de tuberculosis | `datos_paciente.antecedentes_tuberculosis` |
| CARDIOVASCULAR | CARDIO_01 | Pregunta por dolor torácico | `datos_paciente.dolor_toracico` (+ SOCRATES) |
| CARDIOVASCULAR | CARDIO_02 | Caracteriza dolor torácico con SOCRATES | `datos_paciente.*` (bloque HEA_SOCRATES) |
| CARDIOVASCULAR | CARDIO_03 | Pregunta por relación con esfuerzo/reposo | `datos_paciente.relacion_dolor_esfuerzo` |
| CARDIOVASCULAR | CARDIO_04 | Pregunta por síntomas vegetativos asociados | `datos_paciente.sintomas_vegetativos` |
| CARDIOVASCULAR | CARDIO_05 | Pregunta por palpitaciones | `datos_paciente.palpitaciones` |
| CARDIOVASCULAR | CARDIO_06 | Pregunta por síncope o presíncope | `datos_paciente.sincope` (+ `datos_paciente.sincope_caracteristicas`) |
| CARDIOVASCULAR | CARDIO_07 | Pregunta por edemas en miembros inferiores | `datos_paciente.edemas` |
| CARDIOVASCULAR | CARDIO_08 | Pregunta por claudicación intermitente | `datos_paciente.claudicacion` |
| DIGESTIVO | DIGEST_01 | Pregunta por dolor abdominal | `datos_paciente.dolor_abdominal` |
| DIGESTIVO | DIGEST_02 | Pregunta por náuseas o vómitos | `datos_paciente.nauseas` + `datos_paciente.vomitos` |
| DIGESTIVO | DIGEST_03 | Pregunta por cambios en el ritmo intestinal | `datos_paciente.cambios_ritmo_intestinal` |
| DIGESTIVO | DIGEST_04 | Pregunta por melenas, rectorragia o hematemesis | `datos_paciente.melenas` + `datos_paciente.rectorragia` + `datos_paciente.hematemesis` |
| DIGESTIVO | DIGEST_05 | Pregunta por disfagia | `datos_paciente.disfagia` |
| DIGESTIVO | DIGEST_06 | Pregunta por pirosis o reflujo | `datos_paciente.pirosis` |
| DIGESTIVO | DIGEST_07 | Pregunta por distensión abdominal | `datos_paciente.distension_abdominal` |
| DIGESTIVO | DIGEST_08 | Pregunta por ictericia | `datos_paciente.ictericia` |
| GENITOURINARIO | GU_01 | Pregunta por disuria | `datos_paciente.disuria` |
| GENITOURINARIO | GU_02 | Pregunta por polaquiuria o nicturia | `datos_paciente.polaquiuria` + `datos_paciente.nicturia` |
| GENITOURINARIO | GU_03 | Pregunta por hematuria | `datos_paciente.hematuria` |
| GENITOURINARIO | GU_04 | Pregunta por incontinencia urinaria | `datos_paciente.incontinencia_urinaria` |
| GENITOURINARIO | GU_05 | Pregunta por urgencia miccional | `datos_paciente.urgencia_miccional` |
| GENITOURINARIO | GU_06 | Pregunta por dolor lumbar o en flancos | `datos_paciente.dolor_lumbar_flancos` |
| GENITOURINARIO | GU_07 | Pregunta por secreción genital | `datos_paciente.secrecion_genital` |
| GENITOURINARIO | GU_08 | Pregunta por síntomas prostáticos (si hombre) | `datos_paciente.sintomas_prostaticos` |
| NEUROLÓGICO | NEURO_01 | Pregunta por cefalea | `datos_paciente.cefalea` |
| NEUROLÓGICO | NEURO_02 | Caracteriza patrón de cefalea | `datos_paciente.cefalea_patron` |
| NEUROLÓGICO | NEURO_03 | Pregunta por focalidad neurológica | `datos_paciente.focalidad_neurologica` |
| NEUROLÓGICO | NEURO_04 | Pregunta por mareo o vértigo | `datos_paciente.mareo_vertigo` |
| NEUROLÓGICO | NEURO_05 | Pregunta por alteración del nivel de conciencia | `datos_paciente.alteracion_nivel_conciencia` |
| NEUROLÓGICO | NEURO_06 | Pregunta por signos meníngeos | `datos_paciente.signos_meningeos` |
| NEUROLÓGICO | NEURO_07 | Pregunta por alteración del lenguaje | `datos_paciente.alteracion_lenguaje` |
| NEUROLÓGICO | NEURO_08 | Pregunta por convulsiones | `datos_paciente.convulsiones` |
| NEUROLÓGICO | NEURO_09 | Pregunta por problemas de memoria | `datos_paciente.alteracion_memoria` |
| NEUROLÓGICO | NEURO_10 | Pregunta por alteraciones visuales | `datos_paciente.alteracion_vision` |
| OSTEOMUSCULAR | OSTEO_01 | Pregunta por dolor articular | `datos_paciente.dolor_articular` |
| OSTEOMUSCULAR | OSTEO_02 | Pregunta por rigidez matutina | `datos_paciente.rigidez_matutina` |
| OSTEOMUSCULAR | OSTEO_03 | Pregunta por tumefacción articular | `datos_paciente.tumefaccion_articular` |
| OSTEOMUSCULAR | OSTEO_04 | Pregunta por debilidad muscular | `datos_paciente.debilidad_muscular` |
| OSTEOMUSCULAR | OSTEO_05 | Pregunta por limitación de movilidad | `datos_paciente.limitacion_movilidad` |
| OSTEOMUSCULAR | OSTEO_06 | Pregunta por traumatismos recientes | `datos_paciente.traumatismo_reciente` |

## F) Checklist de calidad (antes de subir a Railway)

- ✅ El JSON es válido.
- ✅ `id` = nombre del fichero.
- ✅ Todos los datos importantes están en `datos_paciente` (no solo en `contexto_generado`).
- ✅ No hay contradicciones entre `datos_paciente`, `contexto_generado` y `personalidad_generada`.
- ✅ Respuestas en español de España, cortas y naturales.
- ✅ No quedan textos “COMPLETAR” dentro del caso final.
