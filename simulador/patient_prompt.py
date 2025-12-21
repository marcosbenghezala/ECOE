from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_genero(caso: Dict[str, Any]) -> str:
    info = caso.get("informacion_paciente") or {}
    genero_raw = info.get("genero") or caso.get("gender") or caso.get("genero") or ""
    genero = _as_str(genero_raw).lower()

    if genero in {"female", "f", "mujer", "hembra", "femenino"}:
        return "mujer"
    if genero in {"male", "m", "hombre", "masculino"}:
        return "hombre"
    if "mujer" in genero or "femenin" in genero:
        return "mujer"
    if "hombre" in genero or "masculin" in genero:
        return "hombre"
    return "persona"


def _extract_respuestas(item: Any) -> Tuple[Optional[bool], str, str, List[str]]:
    """
    Normaliza un item de `datos_paciente` a:
    - tiene (bool|None)
    - respuesta_corta (str)
    - respuesta_detalle (str)
    - lista (List[str])

    Soporta:
    - str: se interpreta como respuesta_corta
    - dict: keys típicas: tiene, respuesta, respuesta_corta, respuesta_detalle, lista
    """
    if isinstance(item, str):
        text = _as_str(item)
        return None, text, "", []

    if not isinstance(item, dict):
        text = _as_str(item)
        return None, text, "", []

    tiene = item.get("tiene")
    if isinstance(tiene, bool):
        tiene_bool: Optional[bool] = tiene
    else:
        tiene_bool = None

    respuesta = _as_str(item.get("respuesta"))
    respuesta_corta = _as_str(item.get("respuesta_corta")) or respuesta
    respuesta_detalle = _as_str(item.get("respuesta_detalle")) or (
        "" if respuesta_corta == respuesta else respuesta
    )

    lista_raw = item.get("lista")
    lista: List[str] = []
    if isinstance(lista_raw, list):
        for entry in lista_raw:
            text = _as_str(entry)
            if text:
                lista.append(text)

    return tiene_bool, respuesta_corta, respuesta_detalle, lista


def _render_item(label: str, item: Any) -> str:
    tiene, corta, detalle, lista = _extract_respuestas(item)
    lines: List[str] = [f"- {label}:"]

    if corta:
        lines.append(f"  - Respuesta corta: \"{corta}\"")
    elif tiene is False:
        lines.append("  - Respuesta corta: \"No.\"")
    else:
        lines.append("  - Respuesta corta: \"No lo sé / no me he fijado.\"")

    if detalle:
        lines.append(f"  - Si insisten: \"{detalle}\"")

    if lista:
        lines.append("  - Lista (si te piden concretar):")
        for entry in lista:
            lines.append(f"    - {entry}")

    return "\n".join(lines)


def _render_habitos(habitos: Any) -> str:
    if not isinstance(habitos, dict):
        return _render_item("Hábitos tóxicos", habitos)

    parts: List[str] = ["- Hábitos tóxicos:"]
    for key, label in (
        ("tabaco", "Tabaco"),
        ("alcohol", "Alcohol"),
        ("drogas", "Drogas"),
    ):
        if key not in habitos:
            continue
        tiene, corta, detalle, _ = _extract_respuestas(habitos.get(key))

        if isinstance(habitos.get(key), dict):
            extra_bits: List[str] = []
            cantidad = _as_str(habitos[key].get("cantidad"))
            duracion = _as_str(habitos[key].get("duracion"))
            if cantidad:
                extra_bits.append(f"cantidad={cantidad}")
            if duracion:
                extra_bits.append(f"duración={duracion}")
            extra = f" ({', '.join(extra_bits)})" if extra_bits else ""
        else:
            extra = ""

        parts.append(f"  - {label}{extra}:")
        if corta:
            parts.append(f"    - Respuesta corta: \"{corta}\"")
        elif tiene is False:
            parts.append("    - Respuesta corta: \"No.\"")
        else:
            parts.append("    - Respuesta corta: \"No lo sé / no me he fijado.\"")
        if detalle:
            parts.append(f"    - Si insisten: \"{detalle}\"")

    return "\n".join(parts)


def generar_prompt_paciente(caso: Dict[str, Any]) -> str:
    """
    Genera un system prompt para OpenAI Realtime API basado en `datos_paciente`
    (respuestas canónicas) para evitar contradicciones.

    Requisitos de diseño:
    - Respuestas cortas (1-2 frases, 10-20 palabras) por defecto.
    - NO inventar información; si no está en datos_paciente, decir "no lo sé".
    - Mantener consistencia: si te preguntan lo mismo, responder igual.
    - Español de España (castellano peninsular).
    """
    info = caso.get("informacion_paciente") or {}
    nombre = _as_str(info.get("nombre") or "Paciente")
    ocupacion = _as_str(info.get("ocupacion") or "No especificada")
    genero = _normalize_genero(caso)

    edad_val = info.get("edad")
    if isinstance(edad_val, (int, float)):
        edad_str = f"{int(edad_val)} años"
    else:
        edad_str = _as_str(edad_val) or "No especificada"

    motivo = _as_str(caso.get("motivo_consulta"))
    contexto = _as_str(caso.get("contexto_generado"))
    personalidad = _as_str(caso.get("personalidad_generada")) or "Eres un paciente colaborador y educado."

    datos_paciente = caso.get("datos_paciente")
    if not isinstance(datos_paciente, dict):
        datos_paciente = {}

    # Orden sugerido de campos (si existen)
    ordered_keys: List[Tuple[str, str]] = [
        ("presentacion", "Presentación / identidad"),
        ("motivo_consulta", "Motivo de consulta (si te lo preguntan)"),
        ("tiempo_evolucion", "Tiempo de evolución"),
        ("inicio", "Inicio"),
        ("localizacion_dolor", "Localización del dolor / síntoma"),
        ("caracteristicas_dolor", "Características del dolor / síntoma"),
        ("intensidad_dolor", "Intensidad"),
        ("irradiacion", "Irradiación"),
        ("factores_empeoramiento", "Factores de empeoramiento"),
        ("factores_alivio", "Factores de alivio"),
        ("sintomas_asociados", "Síntomas asociados"),
        ("fiebre", "Fiebre"),
        ("tos", "Tos"),
        ("expectoracion", "Expectoración"),
        ("disnea", "Disnea"),
        ("nauseas", "Náuseas"),
        ("vomitos", "Vómitos"),
        ("diarrea", "Diarrea"),
        ("disuria", "Disuria"),
        ("hematuria", "Hematuria"),
        ("factores_riesgo_cardiovascular", "Factores de riesgo cardiovascular"),
        ("antecedentes_personales", "Antecedentes personales"),
        ("antecedentes_familiares", "Antecedentes familiares"),
        ("medicacion_actual", "Medicación habitual"),
        ("alergias", "Alergias"),
        ("habitos_toxicos", "Hábitos tóxicos"),
        ("ice_ideas", "ICE - Ideas"),
        ("ice_concerns", "ICE - Preocupaciones"),
        ("ice_expectations", "ICE - Expectativas"),
        ("claudicacion", "Claudicación"),
        ("ortopnea", "Ortopnea"),
        ("disnea_paroxistica_nocturna", "Disnea paroxística nocturna"),
        ("palpitaciones", "Palpitaciones"),
        ("sincope", "Síncope"),
        ("edemas", "Edemas"),
    ]

    canonical_lines: List[str] = []
    seen: set[str] = set()
    for key, label in ordered_keys:
        if key not in datos_paciente:
            continue
        if key.startswith("_"):
            continue
        seen.add(key)
        if key == "habitos_toxicos":
            canonical_lines.append(_render_habitos(datos_paciente.get(key)))
        else:
            canonical_lines.append(_render_item(label, datos_paciente.get(key)))

    # Campos extra no listados arriba (pero presentes en datos_paciente)
    extras = [k for k in datos_paciente.keys() if k not in seen and not str(k).startswith("_")]
    for key in sorted(extras):
        canonical_lines.append(_render_item(key.replace("_", " ").capitalize(), datos_paciente.get(key)))

    canonical_section = ""
    if canonical_lines:
        canonical_section = (
            "═══════════════════════════════════════\n"
            "📌 RESPUESTAS CANÓNICAS (NO CAMBIAN)\n"
            "═══════════════════════════════════════\n\n"
            "Lo siguiente es tu verdad absoluta. NUNCA te contradigas.\n"
            "Si el estudiante repite una pregunta (aunque con otras palabras), responde IGUAL.\n"
            "Si te preguntan algo que NO está aquí, di: \"No lo sé\" / \"No me he fijado\".\n\n"
            + "\n\n".join(canonical_lines)
            + "\n"
        )

    # Prompt final (alineado con lo que ya usa el proyecto)
    prompt = f"""Eres {nombre}, {genero} de {edad_str}.

{personalidad}

INFORMACIÓN BÁSICA
- Nombre: {nombre}
- Edad: {edad_str}
- Género: {genero}
- Ocupación: {ocupacion}

═══════════════════════════════════════
🏥 CONTEXTO CLÍNICO (TU CASO)
═══════════════════════════════════════

Motivo de consulta (1 frase): {motivo or "No especificado"}

{contexto}

{canonical_section}

═══════════════════════════════════════
👤 TU COMPORTAMIENTO COMO PACIENTE
═══════════════════════════════════════

⚠️⚠️⚠️ REGLA DE ORO: RESPUESTAS CORTAS Y NATURALES ⚠️⚠️⚠️

- Responde con 1–2 FRASES MÁXIMO por turno.
- Máximo 10–20 palabras por respuesta.
- NO des monólogos largos.
- NO sueltes toda tu información médica de golpe.
- Solo das más detalles si el estudiante pregunta ESPECÍFICAMENTE.

✅ EJEMPLOS (CORTOS)
- "¿Cómo te encuentras?" → "Me duele el pecho. Estoy preocupado."
- "¿Qué te pasa?" → "Me duele aquí, en el pecho."
- "¿Tomas medicación?" → Responde según las RESPUESTAS CANÓNICAS.

═══════════════════════════════════════
📏 REGLAS DE DOSIFICACIÓN (MODO EXAMEN) - MUY ESTRICTO
═══════════════════════════════════════

- Responde SOLO a la pregunta actual. 1–2 frases máximo por defecto.
- Si el médico dice algo que NO es pregunta ("vale", "entiendo"), contesta breve ("sí", "de acuerdo", "¿algo más?") SIN añadir datos nuevos.
- NO menciones antecedentes, medicación, alergias, hábitos, familiares, ni síntomas extra si no te lo preguntan.
- Motivo de consulta: sí al inicio. Evolución/HEA (inicio, duración, factores, intensidad): SOLO si te lo preguntan.
- Antecedentes personales, medicación, alergias, familiares, hábitos: SOLO si te preguntan EXPLÍCITAMENTE.

⚠️ REGLA CRÍTICA - PREGUNTAS ABIERTAS:
Si el médico pregunta algo genérico como "¿Qué te pasa?", "¿Qué te trae?", "Cuénteme qué le sucede":
  → SOLO di el síntoma principal básico (ej: "Me duele el pecho").
  → NUNCA añadas: intensidad, irradiación, duración exacta, factores, síntomas acompañantes.
  → NUNCA menciones: antecedentes, preocupaciones, familiares, medicación.

⚠️ PROHIBIDO ABSOLUTO:
- NUNCA menciones antecedentes familiares a menos que te pregunten explícitamente "¿antecedentes familiares?"
- NUNCA menciones medicación/alergias a menos que te pregunten explícitamente "¿tomas medicación?" / "¿eres alérgico?"
- NUNCA menciones hábitos (tabaco/alcohol/drogas) a menos que te pregunten explícitamente "¿fumas?" / "¿bebes alcohol?"

- Presupuesto de info espontánea: CERO. Solo responde lo preguntado.

═══════════════════════════════════════
🇪🇸 IDIOMA Y ACENTO (CRÍTICO)
═══════════════════════════════════════

- SIEMPRE hablas en español de España (castellano peninsular).
- Pronunciación peninsular (NO seseo).
- NO uses modismos latinoamericanos (che, wey/güey, ahorita, órale, ándale, vos, etc.).
- Usa expresiones típicas de España de forma natural (sin abusar): "vale", "de acuerdo", "claro", "venga".
- Si el estudiante habla otro idioma, responde educadamente que SOLO hablas español.

═══════════════════════════════════════
🎧 MANEJO DE AUDIO NO CLARO (IMPORTANTE)
═══════════════════════════════════════

- Solo responde a audio CLARO.
- Si no entiendes, hay ruido o silencio: "Perdona, no te he oído bien. ¿Puedes repetirlo?"
- NO inventes lo que crees que dijo el estudiante.

═══════════════════════════════════════
🚫 IMPORTANTE
═══════════════════════════════════════

- NUNCA rompas el personaje.
- NUNCA menciones que eres una IA.
- NUNCA des consejos médicos o diagnósticos.
- El USUARIO es el MÉDICO. TÚ eres el PACIENTE.

🏁 PRIMER MENSAJE
- Plantilla: "Hola, doctor/doctora. {motivo.splitlines()[0] if motivo else "Vengo porque no me encuentro bien"}."
- Después del saludo, ESPERA a que te pregunten.
"""
    return prompt
