import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from text_utils import normalize_text


DEFAULT_CHECKLIST_PATH = Path(__file__).parent.parent / "data" / "master-checklist-v2.json"
WEIGHT_ANAMNESIS = 0.7
WEIGHT_DESARROLLO = 0.3
PATIENT_RESPONSE_WINDOW = 3

MIN_WORDS_BY_FIELD = {
    "resumen_caso": 6,
    "diagnostico_principal": 2,
    "diagnosticos_diferenciales": 3,
    "pruebas_diagnosticas": 3,
    "plan_manejo": 3,
}

INVALID_ANSWERS = {
    "",
    "mm",
    "mmm",
    "me",
    "no lo se",
    "no lo se",
    "ns",
    "ni idea",
    "no se",
}

STOPWORDS = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "y",
    "o",
    "por",
    "para",
    "un",
    "una",
    "al",
    "en",
    "con",
    "sin",
    "que",
    "se",
    "su",
    "sus",
}

QUESTION_FIELDS = [
    ("resumen_caso", "Resumen del caso"),
    ("diagnostico_principal", "Diagnostico principal"),
    ("diagnosticos_diferenciales", "Diagnosticos diferenciales"),
    ("pruebas_diagnosticas", "Pruebas diagnosticas"),
    ("plan_manejo", "Plan de manejo"),
]


@dataclass
class ItemRule:
    regex: Tuple[re.Pattern, ...]
    keywords: Tuple[str, ...]


def _normalize_asr(text: str) -> str:
    normalized = normalize_text(text or "")
    replacements = {
        "ola": "hola",
        "ke": "que",
        "q": "que",
        "qe": "que",
        "xq": "porque",
        "porq": "porque",
        "pa": "para",
    }
    for src, dst in replacements.items():
        normalized = re.sub(rf"\\b{re.escape(src)}\\b", dst, normalized)
    return normalized


def _tokenize(text: str) -> List[str]:
    normalized = _normalize_asr(text)
    return [tok for tok in normalized.split() if tok and tok not in STOPWORDS]


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    escaped = re.escape(keyword)
    return re.search(rf"\\b{escaped}\\b", text) is not None


def _load_checklist(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_turns(transcription: Any) -> List[Dict[str, str]]:
    if isinstance(transcription, list):
        turns = []
        for turn in transcription:
            if not isinstance(turn, dict):
                continue
            role = str(turn.get("role") or "").strip().upper()
            text = str(turn.get("text") or "").strip()
            if not text:
                continue
            if role in {"ESTUDIANTE", "STUDENT"}:
                role = "ESTUDIANTE"
            elif role in {"PACIENTE", "PATIENT"}:
                role = "PACIENTE"
            else:
                role = "DESCONOCIDO"
            turns.append({"role": role, "text": text})
        return turns

    if not isinstance(transcription, str):
        return []

    turns = []
    for raw in transcription.splitlines():
        line = raw.strip()
        if not line:
            continue
        role = "DESCONOCIDO"
        text = line
        if line.startswith("[ESTUDIANTE]"):
            role = "ESTUDIANTE"
            text = line[len("[ESTUDIANTE]") :].lstrip(": ").strip()
        elif line.startswith("[PACIENTE]"):
            role = "PACIENTE"
            text = line[len("[PACIENTE]") :].lstrip(": ").strip()
        elif line.upper().startswith("ESTUDIANTE"):
            role = "ESTUDIANTE"
            text = line[len("ESTUDIANTE") :].lstrip(": ").strip()
        elif line.upper().startswith("PACIENTE"):
            role = "PACIENTE"
            text = line[len("PACIENTE") :].lstrip(": ").strip()
        turns.append({"role": role, "text": text})
    return turns


class EvaluatorProduction:
    def __init__(self, checklist_path: Optional[Path] = None) -> None:
        self.checklist_path = checklist_path or DEFAULT_CHECKLIST_PATH
        self.checklist = _load_checklist(self.checklist_path)
        self.items = self.checklist.get("items", [])
        self.blocks = self.checklist.get("blocks", [])
        self.block_by_id = {block.get("id"): block for block in self.blocks if block.get("id")}
        self.rules = self._compile_rules(self.items)

    def evaluate(
        self,
        transcription: Any,
        checklist: Optional[List[Dict[str, Any]]] = None,
        case_metadata: Optional[Dict[str, Any]] = None,
        reflection_answers: Optional[Dict[str, Any]] = None,
        survey: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        turns = _parse_turns(transcription)
        items = checklist or self.items
        item_results, matched_count = self._evaluate_items(turns, items)
        total_items = len(items)

        anamnesis_pct = (matched_count / total_items * 100) if total_items else 0.0
        score_anamnesis = round(anamnesis_pct * WEIGHT_ANAMNESIS, 1)

        development = self._evaluate_development(reflection_answers or {}, case_metadata or {})
        dev_pct = development.get("percentage", 0.0)
        score_desarrollo = round(dev_pct * WEIGHT_DESARROLLO, 1)

        score_total = round(score_anamnesis + score_desarrollo, 1)

        blocks = self._build_blocks(item_results)

        return {
            "schema_version": "evaluation.production.v1",
            "scores": {
                "global": {"score": score_total, "max": 100, "percentage": score_total},
                "anamnesis": {
                    "score": matched_count,
                    "max": total_items,
                    "percentage": round(anamnesis_pct, 1),
                    "weighted": score_anamnesis,
                    "weight": WEIGHT_ANAMNESIS,
                },
                "checklist": {
                    "score": matched_count,
                    "max": total_items,
                    "percentage": round(anamnesis_pct, 1),
                    "weighted": score_anamnesis,
                    "weight": WEIGHT_ANAMNESIS,
                },
                "development": {
                    "percentage": round(dev_pct, 1),
                    "weighted": score_desarrollo,
                    "weight": WEIGHT_DESARROLLO,
                },
            },
            "items": item_results,
            "blocks": blocks,
            "score_anamnesis": score_anamnesis,
            "score_desarrollo": score_desarrollo,
            "score_total": score_total,
            "percentage": score_total,
            "development": development,
            "survey": survey or {},
        }

    def _compile_rules(self, items: Iterable[Dict[str, Any]]) -> Dict[str, ItemRule]:
        compiled: Dict[str, ItemRule] = {}
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            regexes = []
            for pattern in item.get("regex") or []:
                try:
                    regexes.append(re.compile(pattern))
                except re.error:
                    continue
            keywords = tuple(_normalize_asr(k) for k in (item.get("keywords") or []) if k)
            compiled[item_id] = ItemRule(tuple(regexes), keywords)
        return compiled

    def _evaluate_items(
        self, turns: List[Dict[str, str]], items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        student_turns = [
            (idx, _normalize_asr(turn["text"]))
            for idx, turn in enumerate(turns)
            if turn.get("role") == "ESTUDIANTE" and turn.get("text")
        ]
        item_results: List[Dict[str, Any]] = []
        matched_count = 0

        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            rule = self.rules.get(item_id) or ItemRule((), ())
            matched = self._match_item(item, rule, turns, student_turns)
            if matched:
                matched_count += 1
            points = int(item.get("points") or 1)
            item_results.append(
                {
                    "id": item_id,
                    "bloque": item.get("block_id"),
                    "descripcion": item.get("label") or item.get("text") or item_id,
                    "done": matched,
                    "score": points if matched else 0,
                    "max_score": points,
                }
            )
        return item_results, matched_count

    def _match_item(
        self,
        item: Dict[str, Any],
        rule: ItemRule,
        turns: List[Dict[str, str]],
        student_turns: List[Tuple[int, str]],
    ) -> bool:
        requires_patient = self._requires_patient_response(item)

        for idx, text in student_turns:
            if not self._line_matches(rule, text):
                continue
            if requires_patient and not self._has_patient_reply(idx, turns):
                continue
            return True
        return False

    def _line_matches(self, rule: ItemRule, text: str) -> bool:
        for pattern in rule.regex:
            if pattern.search(text):
                return True
        for keyword in rule.keywords:
            if _contains_keyword(text, keyword):
                return True
        return False

    def _has_patient_reply(self, idx: int, turns: List[Dict[str, str]]) -> bool:
        for offset in range(1, PATIENT_RESPONSE_WINDOW + 1):
            pos = idx + offset
            if pos >= len(turns):
                break
            turn = turns[pos]
            if turn.get("role") == "PACIENTE" and turn.get("text"):
                return True
        return False

    def _requires_patient_response(self, item: Dict[str, Any]) -> bool:
        block_id = item.get("block_id") or ""
        if block_id in {"B0_INTRODUCCION", "B1_MOTIVO_CONSULTA", "B8_CIERRE", "B9_COMUNICACION"}:
            return False
        return True

    def _build_blocks(self, item_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items_by_block: Dict[str, List[Dict[str, Any]]] = {}
        for item in item_results:
            block_id = item.get("bloque") or "SIN_BLOQUE"
            entry = {
                "id": item.get("id"),
                "text": item.get("descripcion"),
                "done": bool(item.get("done")),
                "score": int(item.get("score") or 0),
                "max_score": int(item.get("max_score") or 1),
            }
            items_by_block.setdefault(block_id, []).append(entry)

        blocks_out: List[Dict[str, Any]] = []
        for block in self.blocks:
            block_id = block.get("id")
            block_items = items_by_block.get(block_id, [])
            block_score = sum(i.get("score", 0) for i in block_items)
            block_max = sum(i.get("max_score", 0) for i in block_items)
            blocks_out.append(
                {
                    "id": block_id,
                    "name": block.get("label") or block_id,
                    "score": block_score,
                    "max": block_max,
                    "percentage": round((block_score / block_max) * 100, 1) if block_max else 0.0,
                    "items": block_items,
                }
            )

        if "SIN_BLOQUE" in items_by_block:
            block_items = items_by_block.get("SIN_BLOQUE", [])
            block_score = sum(i.get("score", 0) for i in block_items)
            block_max = sum(i.get("max_score", 0) for i in block_items)
            blocks_out.append(
                {
                    "id": "SIN_BLOQUE",
                    "name": "Sin bloque",
                    "score": block_score,
                    "max": block_max,
                    "percentage": round((block_score / block_max) * 100, 1) if block_max else 0.0,
                    "items": block_items,
                }
            )

        return blocks_out

    def _evaluate_development(
        self, reflection: Dict[str, Any], case_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        questions: List[Dict[str, Any]] = []
        scores: List[int] = []

        for field, label in QUESTION_FIELDS:
            answer = str(reflection.get(field) or "").strip()
            score, feedback = self._score_reflection_field(field, answer, case_metadata)
            questions.append(
                {"question": label, "answer": answer, "score": score, "feedback": feedback}
            )
            scores.append(score)

        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        return {"questions": questions, "percentage": avg}

    def _score_reflection_field(
        self, field: str, answer: str, case_metadata: Dict[str, Any]
    ) -> Tuple[int, str]:
        normalized = _normalize_asr(answer)
        word_count = len(normalized.split()) if normalized else 0
        min_words = MIN_WORDS_BY_FIELD.get(field, 3)

        if not normalized or normalized in INVALID_ANSWERS or word_count < min_words:
            return 0, "Respuesta demasiado breve o no valida."

        if field == "diagnostico_principal":
            expected = str(case_metadata.get("diagnostico_principal") or "")
            if expected:
                expected_norm = _normalize_asr(expected)
                if expected_norm and expected_norm in normalized:
                    return 90, "Diagnostico principal correcto."
                if self._token_overlap(normalized, expected_norm) >= 1:
                    return 70, "Diagnostico parcialmente correcto."
                return 40, "Diagnostico poco preciso."
            return 60, "Diagnostico aportado."

        if field == "diagnosticos_diferenciales":
            expected = case_metadata.get("diagnosticos_diferenciales") or []
            return self._score_list_field(normalized, expected, "diferenciales")

        if field == "pruebas_diagnosticas":
            expected = case_metadata.get("pruebas_esperadas") or []
            return self._score_list_field(normalized, expected, "pruebas")

        if field == "resumen_caso":
            expected_terms = []
            for item in case_metadata.get("sintomas_principales") or []:
                expected_terms.append(str(item))
            motivo = case_metadata.get("motivo_consulta")
            if motivo:
                expected_terms.append(str(motivo))
            if expected_terms:
                hits = self._list_hits(normalized, expected_terms)
                if hits >= 2:
                    return 90, "Resumen completo."
                if hits == 1:
                    return 70, "Resumen correcto pero incompleto."
            return 50, "Resumen poco detallado."

        if field == "plan_manejo":
            if word_count >= 10:
                return 70, "Plan de manejo suficiente."
            return 50, "Plan de manejo muy breve."

        return 60, "Respuesta registrada."

    def _score_list_field(self, normalized: str, expected: List[str], label: str) -> Tuple[int, str]:
        if not expected:
            return 60, f"{label.capitalize()} aportados."
        hits = self._list_hits(normalized, expected)
        if hits == 0:
            return 40, f"No se identifican {label} esperados."
        if hits >= max(2, len(expected)):
            return 90, f"{label.capitalize()} completos."
        return 70, f"{label.capitalize()} parciales."

    def _list_hits(self, normalized: str, expected: List[str]) -> int:
        count = 0
        for item in expected:
            if not item:
                continue
            expected_norm = _normalize_asr(str(item))
            if expected_norm and self._token_overlap(normalized, expected_norm) >= 1:
                count += 1
        return count

    def _token_overlap(self, text: str, expected: str) -> int:
        expected_tokens = set(_tokenize(expected))
        if not expected_tokens:
            return 0
        text_tokens = set(_tokenize(text))
        return len(expected_tokens & text_tokens)
