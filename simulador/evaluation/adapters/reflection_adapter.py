from typing import Any, Dict, List


FIELD_MAP = [
    ("resumen_caso", "Resumen del caso", "puntuacion_resumen", "resumen_feedback"),
    ("diagnostico_principal", "Diagnóstico principal", "puntuacion_diagnostico", "diagnostico_feedback"),
    ("diagnosticos_diferenciales", "Diagnósticos diferenciales", "puntuacion_diferenciales", "diferenciales_feedback"),
    ("pruebas_diagnosticas", "Pruebas diagnósticas", "puntuacion_pruebas", "pruebas_feedback"),
    ("plan_manejo", "Plan de manejo", "puntuacion_plan", "plan_feedback"),
]


def build_development_questions(
    reflection_answers: Dict[str, Any],
    eval_reflection: Dict[str, Any],
) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    for field, label, score_key, feedback_key in FIELD_MAP:
        answer = reflection_answers.get(field)
        score = eval_reflection.get(score_key)
        feedback = eval_reflection.get(feedback_key)
        if answer is None and score is None and feedback is None:
            continue
        questions.append(
            {
                "id": field,
                "question": label,
                "answer": answer or "",
                "score": int(round(float(score))) if isinstance(score, (int, float)) else 0,
                "feedback": feedback or "",
            }
        )
    return questions
