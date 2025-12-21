import unittest

from reflection_grader import analyze_reflection_answers, apply_quality_rules


class ReflectionGraderTests(unittest.TestCase):
    def test_short_invalid_response_scores_zero(self):
        reflection = {"resumen_caso": "mm"}
        analysis = analyze_reflection_answers(reflection)
        eval_reflection = {"puntuacion_resumen": 85}
        result = apply_quality_rules(eval_reflection, reflection, analysis)
        self.assertEqual(result["puntuacion_resumen"], 0)

    def test_minimal_valid_response_keeps_score(self):
        reflection = {"resumen_caso": "Dolor toracico con sudoracion y mareo intenso"}
        analysis = analyze_reflection_answers(reflection)
        eval_reflection = {"puntuacion_resumen": 55}
        result = apply_quality_rules(eval_reflection, reflection, analysis)
        self.assertEqual(result["puntuacion_resumen"], 55)

    def test_well_structured_response_keeps_high_score(self):
        reflection = {
            "resumen_caso": (
                "Paciente con dolor torácico opresivo de inicio súbito, "
                "irradiado a brazo y asociado a sudoración. Refiere factores de riesgo."
            )
        }
        analysis = analyze_reflection_answers(reflection)
        eval_reflection = {"puntuacion_resumen": 90}
        result = apply_quality_rules(eval_reflection, reflection, analysis)
        self.assertEqual(result["puntuacion_resumen"], 90)

    def test_invalid_phrase_scores_zero(self):
        reflection = {"diagnostico_principal": "No lo sé"}
        analysis = analyze_reflection_answers(reflection)
        eval_reflection = {"puntuacion_diagnostico": 70}
        result = apply_quality_rules(eval_reflection, reflection, analysis)
        self.assertEqual(result["puntuacion_diagnostico"], 0)
