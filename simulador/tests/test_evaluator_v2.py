import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from evaluator_v2 import EvaluatorV2


def _build_evaluator(tmp_path: Path) -> EvaluatorV2:
    items = [
        {
            "id": "AF_01",
            "texto": "Pregunta por antecedentes familiares",
            "tipo": "contexto",
            "critico": False,
            "peso": 1,
            "keywords": ["antecedentes familiares", "familia", "familiares"],
        },
        {
            "id": "AP_01",
            "texto": "Pregunta por enfermedades crónicas",
            "tipo": "contexto",
            "critico": False,
            "peso": 1,
            "keywords": ["enfermedades cronicas", "tension alta", "hipertension", "colesterol"],
        },
        {
            "id": "AP_11",
            "texto": "Pregunta por medicación actual",
            "tipo": "contexto",
            "critico": False,
            "peso": 1,
            "keywords": ["medicacion", "tratamiento", "pastillas"],
        },
        {
            "id": "HAB_01",
            "texto": "Pregunta por tabaco",
            "tipo": "contexto",
            "critico": False,
            "peso": 1,
            "keywords": ["tabaco", "fumas", "fumador"],
        },
        {
            "id": "RESP_05",
            "texto": "Pregunta por disnea paroxística nocturna",
            "tipo": "diagnostico_diferencial",
            "critico": False,
            "peso": 1,
            "keywords": ["disnea paroxistica nocturna", "disnea nocturna"],
        },
    ]

    master_data = {
        "bloques_universales": {
            "general": {"items": items}
        },
        "items_por_sistemas": {},
    }
    index_data = [{"id": item["id"]} for item in items]

    master_path = tmp_path / "master_items.json"
    index_path = tmp_path / "master_items_index.json"
    emb_path = tmp_path / "master_items_embeddings.npz"

    master_path.write_text(json.dumps(master_data), encoding="utf-8")
    index_path.write_text(json.dumps(index_data), encoding="utf-8")
    np.savez(emb_path, embeddings=np.zeros((len(items), 3), dtype=float))

    return EvaluatorV2(
        api_key="test",
        master_items_path=str(master_path),
        embeddings_path=str(emb_path),
        index_path=str(index_path),
        learning_system=None,
    )


def _items_by_id(result: dict) -> dict:
    out = {}
    for capa in result.get("evaluacion_por_capas", {}).values():
        for item in capa.get("items", []):
            out[item["id"]] = item
    return out


class EvaluatorV2ConversationTests(unittest.TestCase):
    def test_case_a_student_questions_mark_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = _build_evaluator(Path(tmp))
            transcript = (
                "[ESTUDIANTE]: ¿Hay antecedentes familiares?\n"
                "[PACIENTE]: Mi padre tuvo un infarto a los 58.\n"
                "[ESTUDIANTE]: ¿Tiene enfermedades crónicas?\n"
                "[PACIENTE]: Tengo la tensión alta y colesterol.\n"
                "[ESTUDIANTE]: ¿Tomas alguna medicación?\n"
                "[PACIENTE]: Enalapril y atorvastatina.\n"
            )
            result = evaluator.evaluate_transcript(
                transcript=transcript,
                sintomas_caso=[],
                caso_id="TEST_A",
                incluir_aprendizaje=False,
                use_embeddings=False,
            )
            items = _items_by_id(result)
            self.assertTrue(items["AF_01"]["done"])
            self.assertTrue(items["AP_01"]["done"])
            self.assertTrue(items["AP_11"]["done"])
            self.assertFalse(items["HAB_01"]["done"])

    def test_case_b_patient_only_does_not_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = _build_evaluator(Path(tmp))
            transcript = (
                "[PACIENTE]: Mi padre tuvo un infarto a los 58.\n"
                "[PACIENTE]: Tengo disnea paroxística nocturna.\n"
                "[PACIENTE]: Tomo enalapril y atorvastatina.\n"
                "[ESTUDIANTE]: Vale.\n"
            )
            result = evaluator.evaluate_transcript(
                transcript=transcript,
                sintomas_caso=[],
                caso_id="TEST_B",
                incluir_aprendizaje=False,
                use_embeddings=False,
            )
            items = _items_by_id(result)
            self.assertFalse(items["AF_01"]["done"])
            self.assertFalse(items["AP_01"]["done"])
            self.assertFalse(items["AP_11"]["done"])
            self.assertFalse(items["RESP_05"]["done"])

    def test_case_c_vague_question_marks_af(self):
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = _build_evaluator(Path(tmp))
            transcript = (
                "[ESTUDIANTE]: ¿Algún problema en la familia?\n"
                "[PACIENTE]: Mi padre falleció por un infarto.\n"
            )
            result = evaluator.evaluate_transcript(
                transcript=transcript,
                sintomas_caso=[],
                caso_id="TEST_C",
                incluir_aprendizaje=False,
                use_embeddings=False,
            )
            items = _items_by_id(result)
            self.assertTrue(items["AF_01"]["done"])
