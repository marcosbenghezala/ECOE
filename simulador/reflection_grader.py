"""
Reglas generales para evaluar respuestas abiertas (reflexión clínica).
Incluye validaciones previas y ajustes post-modelo.
"""
import os
import re
from typing import Dict, Any

from text_utils import normalize_text

MIN_WORDS_PER_ANSWER = int(os.getenv("REFLECTION_MIN_WORDS", "6"))

_INVALID_ANSWERS_RAW = {
    "",
    "mm",
    "mmm",
    "me",
    "no lo se",
    "no lo sé",
    "ns",
    "ni idea",
    "no sé",
    "no se",
}

INVALID_ANSWERS = {normalize_text(a) for a in _INVALID_ANSWERS_RAW}

ANSWER_FIELDS = {
    "resumen_caso": {
        "score_key": "puntuacion_resumen",
        "feedback_key": "resumen_feedback",
        "label": "Resumen del caso",
    },
    "diagnostico_principal": {
        "score_key": "puntuacion_diagnostico",
        "feedback_key": "diagnostico_feedback",
        "label": "Diagnóstico principal",
    },
    "diagnosticos_diferenciales": {
        "score_key": "puntuacion_diferenciales",
        "feedback_key": "diferenciales_feedback",
        "label": "Diagnósticos diferenciales",
    },
    "pruebas_diagnosticas": {
        "score_key": "puntuacion_pruebas",
        "feedback_key": "pruebas_feedback",
        "label": "Pruebas diagnósticas",
    },
    "plan_manejo": {
        "score_key": "puntuacion_plan",
        "feedback_key": "plan_feedback",
        "label": "Plan de manejo",
    },
}


def count_words(text: str) -> int:
    cleaned = normalize_text(text or "")
    if not cleaned:
        return 0
    return len(re.findall(r"\b\w+\b", cleaned))


def analyze_answer(text: str) -> Dict[str, Any]:
    normalized = normalize_text(text or "")
    word_count = count_words(normalized)
    is_invalid = normalized in INVALID_ANSWERS
    is_too_short = word_count < MIN_WORDS_PER_ANSWER
    return {
        "normalized": normalized,
        "word_count": word_count,
        "is_invalid": is_invalid,
        "is_too_short": is_too_short,
    }


def analyze_reflection_answers(reflection: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        field: analyze_answer(reflection.get(field, ""))
        for field in ANSWER_FIELDS
    }


def apply_quality_rules(
    eval_reflection: Dict[str, Any],
    reflection: Dict[str, Any],
    analysis: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    for field, meta in ANSWER_FIELDS.items():
        info = analysis.get(field) or analyze_answer(reflection.get(field, ""))
        score_key = meta["score_key"]
        feedback_key = meta["feedback_key"]

        if info["is_invalid"] or info["is_too_short"]:
            eval_reflection[score_key] = 0
            if feedback_key and not eval_reflection.get(feedback_key):
                eval_reflection[feedback_key] = "Respuesta demasiado breve o no válida."

    return eval_reflection


def build_quality_instructions() -> str:
    invalid_examples = ", ".join(sorted(_INVALID_ANSWERS_RAW))
    return (
        "REGLAS GENERALES (OBLIGATORIAS):\n"
        f"- Si la respuesta tiene menos de {MIN_WORDS_PER_ANSWER} palabras, la puntuación debe ser 0.\n"
        f"- Si la respuesta es vacía o coincide con respuestas no válidas ({invalid_examples}), puntuación 0.\n"
        "- Respuestas muy cortas o sin contenido nunca pueden superar 10/100.\n"
        "- Valora claridad, estructura mínima y cobertura de información clave del caso.\n"
    )
