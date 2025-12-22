"""
EvaluatorV3 - Evaluación con checklist v2 (regex + keywords)

DIFERENCIAS vs V2:
- NO usa embeddings/GPT-4 (solo regex + keywords)
- NO usa capas Principal/Diferencial/Screening
- SÍ usa ChecklistLoaderV2 + CaseAdapterV2
- SÍ output por bloques + subsecciones B7
- SÍ evalúa SOLO líneas del estudiante ([ESTUDIANTE])

WORKFLOW:
1. Cargar checklist v2 (ChecklistLoaderV2)
2. Adaptar checklist al caso (CaseAdapterV2)
3. Extraer líneas del estudiante (text_utils)
4. Evaluar cada item con regex + keywords
5. Agrupar resultados por bloques + subsecciones
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from checklist_loader_v2 import ChecklistLoaderV2, load_checklist_v2
from case_adapter_v2 import CaseAdapterV2
from text_utils import extract_student_lines, normalize_text, preprocess_transcript_by_role

HABITOS_TABACO_STUDENT = (
    "fumas",
    "fuma",
    "tabaco",
    "cigarr",
    "fumador",
)
HABITOS_TABACO_PATIENT = (
    "fumo",
    "fumador",
    "cigarr",
    "tabaco",
    "paquete",
)
HABITOS_ALCOHOL_STUDENT = (
    "bebes",
    "bebe",
    "beber",
    "alcohol",
    "cerveza",
    "vino",
)
HABITOS_ALCOHOL_PATIENT = (
    "bebo",
    "bebe",
    "alcohol",
    "cerveza",
    "vino",
    "copas",
    "whisky",
)
FAMILIA_STUDENT = (
    "antecedentes familiares",
    "familia",
    "familiares",
    "historia familiar",
)
FAMILIA_PATIENT = (
    "padre",
    "madre",
    "hermano",
    "hermana",
    "familia",
)
FAMILIA_EVENTOS = (
    "infarto",
    "ictus",
    "muerte",
    "fallecio",
    "murio",
    "cardiaco",
    "cardiaca",
)
B2_LOCALIZACION_STUDENT = (
    "donde",
    "que parte",
    "zona",
    "sitio",
    "localizacion",
)
B2_LOCALIZACION_PATIENT = (
    "pecho",
    "torax",
    "brazo",
    "espalda",
    "hombro",
    "costado",
)
B2_CARACTERISTICAS_STUDENT = (
    "como es",
    "que tipo",
    "que sensacion",
    "opresivo",
    "punzante",
    "quemazon",
)
B2_CARACTERISTICAS_PATIENT = (
    "opresivo",
    "punzante",
    "quemazon",
    "ardor",
)
B2_IRRADIACION_STUDENT = (
    "irrad",
    "se extiende",
    "hacia",
    "baja",
    "sube",
)
B2_IRRADIACION_PATIENT = (
    "irrad",
    "brazo",
    "mandibula",
    "cuello",
    "espalda",
    "hombro",
)


class EvaluatorV3:
    """
    Evaluador V3 - Regex + Keywords sin embeddings.

    Características:
    - Evaluación determinista (regex + keywords)
    - Activación dinámica de B7 por síntomas
    - Output estructurado por bloques
    - Solo evalúa líneas [ESTUDIANTE]
    """

    def __init__(self, checklist_path: Optional[str] = None):
        """
        Inicializa evaluador V3.

        Args:
            checklist_path: Ruta custom al checklist (opcional)
        """
        self.loader = load_checklist_v2(checklist_path)
        self.adapter = CaseAdapterV2(checklist_path)

    def _contains_any(self, text: str, keywords: tuple) -> bool:
        for kw in keywords:
            if kw and kw in text:
                return True
        return False

    def _has_age_reference(self, text: str) -> bool:
        if re.search(r"\b\d{2}\b", text):
            return True
        return "anos" in text

    def _special_match(self, item_id: str, student_text: str, patient_text: str) -> bool:
        if not student_text or not patient_text:
            return False

        if item_id == "B5_006":
            return self._contains_any(student_text, HABITOS_TABACO_STUDENT) and self._contains_any(
                patient_text, HABITOS_TABACO_PATIENT
            )
        if item_id == "B5_007":
            numeric_smoke = bool(re.search(r"\b\d+\b", patient_text)) and self._contains_any(
                patient_text, ("cigarr", "paquete", "dia")
            )
            return self._contains_any(student_text, HABITOS_TABACO_STUDENT) and numeric_smoke
        if item_id == "B5_008":
            return self._contains_any(student_text, HABITOS_ALCOHOL_STUDENT) and self._contains_any(
                patient_text, HABITOS_ALCOHOL_PATIENT
            )
        if item_id == "B5_009":
            numeric_alcohol = bool(re.search(r"\b\d+\b", patient_text)) or self._contains_any(
                patient_text, ("semana", "fines", "diario", "copas", "cerveza")
            )
            return self._contains_any(student_text, HABITOS_ALCOHOL_STUDENT) and numeric_alcohol
        if item_id == "B6_001":
            return self._contains_any(student_text, FAMILIA_STUDENT) and self._contains_any(
                patient_text, FAMILIA_PATIENT
            )
        if item_id == "B6_002":
            return self._contains_any(student_text, FAMILIA_STUDENT) and self._contains_any(
                patient_text, FAMILIA_PATIENT
            ) and self._contains_any(patient_text, FAMILIA_EVENTOS)
        if item_id == "B6_008":
            return self._contains_any(student_text, FAMILIA_STUDENT) and self._contains_any(
                patient_text, FAMILIA_EVENTOS
            ) and self._has_age_reference(patient_text)
        if item_id == "B2_004":
            if self._contains_any(student_text, B2_LOCALIZACION_STUDENT):
                return True
            return self._contains_any(patient_text, B2_LOCALIZACION_PATIENT) and "dolor" in student_text
        if item_id == "B2_005":
            if self._contains_any(student_text, B2_CARACTERISTICAS_STUDENT):
                return True
            return self._contains_any(patient_text, B2_CARACTERISTICAS_PATIENT) and "dolor" in student_text
        if item_id == "B2_006":
            if self._contains_any(student_text, B2_IRRADIACION_STUDENT):
                return True
            return self._contains_any(patient_text, B2_IRRADIACION_PATIENT) and "dolor" in student_text
        return False

    def evaluate_item(self, item: Dict, student_text: str, patient_text: str = "") -> Dict:
        """
        Evalúa un item contra el texto del estudiante.

        Args:
            item: Dict del item (con id, regex, keywords, points)
            student_text: Texto normalizado del estudiante

        Returns:
            Dict con resultado:
            {
                "item_id": str,
                "matched": bool,
                "points": int (0 si no matched, item.points si matched),
                "method": str ("regex" | "keywords" | "none"),
                "match_details": str (qué regex/keyword matcheó)
            }
        """
        item_id = item["id"]
        max_points = item.get("points", 0)
        item_label = item.get("label", item.get("description", item_id))  # Usar label o description

        # 1. Intentar match con regex (compilados)
        compiled_patterns = self.loader.get_compiled_regex(item_id)
        for i, pattern in enumerate(compiled_patterns):
            match = pattern.search(student_text)
            if match:
                return {
                    "item_id": item_id,
                    "label": item_label,  # NUEVO: Agregar label legible
                    "matched": True,
                    "points": max_points,
                    "method": "regex",
                    "match_details": f"regex[{i}]: {pattern.pattern}"
                }

        # 2. Si no match con regex, intentar keywords
        keywords = item.get("keywords", [])
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            # Match por palabra completa (word boundaries)
            pattern = r'\b' + re.escape(keyword_norm) + r'\b'
            if re.search(pattern, student_text):
                return {
                    "item_id": item_id,
                    "label": item_label,  # NUEVO: Agregar label legible
                    "matched": True,
                    "points": max_points,
                    "method": "keywords",
                    "match_details": f"keyword: {keyword}"
                }

        # 3. Heurística mínima con paciente para ítems clave
        if patient_text and self._special_match(item_id, student_text, patient_text):
            return {
                "item_id": item_id,
                "label": item_label,
                "matched": True,
                "points": max_points,
                "method": "heuristic",
                "match_details": "override_by_patient"
            }

        # 4. No match
        return {
            "item_id": item_id,
            "label": item_label,  # NUEVO: Agregar label legible
            "matched": False,
            "points": 0,
            "method": "none",
            "match_details": ""
        }

    def evaluate_transcript(
        self,
        transcript: str,
        case_data: Dict,
        caso_id: Optional[str] = None
    ) -> Dict:
        """
        Evalúa transcripción completa contra checklist adaptado al caso.

        Args:
            transcript: Transcripción completa (con tags [ESTUDIANTE]/[PACIENTE])
            case_data: Dict del caso (sintomas_principales, motivo_consulta, etc.)
            caso_id: ID del caso (opcional, para metadata)

        Returns:
            Dict con evaluación completa:
            {
                "caso_id": str,
                "timestamp": str,
                "max_points_case": int,
                "min_points_case": int,
                "points_obtained": int,
                "percentage": float,
                "passed": bool,
                "subsections_b7_activas": List[str],
                "blocks": Dict[block_id, block_result],
                "items_evaluated": List[item_result],
                "summary": Dict con resumen
            }
        """
        # 1. Adaptar checklist al caso
        adapted = self.adapter.adapt_to_case(case_data)
        items_activos = adapted["items_activos"]
        max_points_case = adapted["max_points_case"]
        min_points_case = adapted["min_points_case"]
        subsections_b7 = adapted["subsections_b7_activas"]

        # 2. Extraer líneas por rol (estudiante + paciente)
        preprocessed = preprocess_transcript_by_role(transcript)
        student_lines = preprocessed.get("student_lines") or extract_student_lines(transcript)
        student_text = " ".join(student_lines)
        student_text_normalized = preprocessed.get("student_text_normalized") or normalize_text(student_text)
        patient_text_normalized = preprocessed.get("patient_text_normalized") or ""

        # 3. Evaluar cada item activo
        items_evaluated = []
        points_obtained = 0

        for item in items_activos:
            result = self.evaluate_item(item, student_text_normalized, patient_text_normalized)
            items_evaluated.append(result)
            points_obtained += result["points"]

        # 4. Agrupar por bloques
        blocks_results = {}
        for block_id, block_max_points in adapted["blocks_activos"].items():
            # Items del bloque
            block_items_ids = {
                it["id"] for it in self.loader.get_items_for_block(block_id)
            }

            # Resultados del bloque
            block_items_results = [
                r for r in items_evaluated if r["item_id"] in block_items_ids
            ]

            block_points = sum(r["points"] for r in block_items_results)
            block_matched = sum(1 for r in block_items_results if r["matched"])

            blocks_results[block_id] = {
                "max_points": block_max_points,
                "points_obtained": block_points,
                "items_total": len(block_items_results),
                "items_matched": block_matched,
                "percentage": round(block_points / block_max_points * 100, 1) if block_max_points > 0 else 0
            }

        # 5. Agrupar subsecciones B7 (solo si B7 está activo)
        b7_subsections_results = {}
        if "B7_ANAMNESIS_APARATOS" in blocks_results:
            for subsection in subsections_b7:
                subsection_items = self.loader.get_items_for_subsection(subsection)
                subsection_items_ids = {it["id"] for it in subsection_items}

                subsection_results = [
                    r for r in items_evaluated if r["item_id"] in subsection_items_ids
                ]

                subsection_points = sum(r["points"] for r in subsection_results)
                subsection_max = sum(it["points"] for it in subsection_items)

                b7_subsections_results[subsection] = {
                    "max_points": subsection_max,
                    "points_obtained": subsection_points,
                    "items_total": len(subsection_results),
                    "items_matched": sum(1 for r in subsection_results if r["matched"]),
                    "percentage": round(subsection_points / subsection_max * 100, 1) if subsection_max > 0 else 0
                }

        # 6. Calcular aprobado/suspenso
        percentage = round(points_obtained / max_points_case * 100, 1) if max_points_case > 0 else 0
        passed = points_obtained >= min_points_case

        # 7. Resumen
        summary = {
            "total_items_evaluated": len(items_evaluated),
            "total_items_matched": sum(1 for r in items_evaluated if r["matched"]),
            "match_rate": round(sum(1 for r in items_evaluated if r["matched"]) / len(items_evaluated) * 100, 1) if items_evaluated else 0,
            "student_lines_count": len(student_lines),
            "student_text_length": len(student_text)
        }

        # 8. Construir resultado final
        return {
            "caso_id": caso_id or case_data.get("id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "max_points_case": max_points_case,
            "min_points_case": min_points_case,
            "points_obtained": points_obtained,
            "percentage": percentage,
            "passed": passed,
            "subsections_b7_activas": subsections_b7,
            "blocks": blocks_results,
            "b7_subsections": b7_subsections_results,
            "items_evaluated": items_evaluated,
            "summary": summary
        }

    def get_detailed_report(self, evaluation: Dict) -> str:
        """
        Genera reporte legible de la evaluación.

        Args:
            evaluation: Dict resultado de evaluate_transcript()

        Returns:
            String con reporte formateado
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"REPORTE DE EVALUACIÓN - {evaluation['caso_id']}")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {evaluation['timestamp']}")
        lines.append(f"")

        # Resultado general
        lines.append("RESULTADO GENERAL:")
        lines.append("-" * 70)
        lines.append(f"  Puntos obtenidos: {evaluation['points_obtained']} / {evaluation['max_points_case']}")
        lines.append(f"  Porcentaje: {evaluation['percentage']}%")
        lines.append(f"  Mínimo requerido: {evaluation['min_points_case']} pts")
        lines.append(f"  Estado: {'✅ APROBADO' if evaluation['passed'] else '❌ SUSPENSO'}")
        lines.append(f"")

        # Bloques
        lines.append("RESULTADOS POR BLOQUE:")
        lines.append("-" * 70)
        for block_id, block_result in evaluation["blocks"].items():
            block = self.loader.get_block(block_id)
            block_name = block.get("name", block_id) if block else block_id
            lines.append(f"  {block_id} ({block_name}):")
            lines.append(f"    Puntos: {block_result['points_obtained']} / {block_result['max_points']}")
            lines.append(f"    Ítems: {block_result['items_matched']} / {block_result['items_total']} ({block_result['percentage']}%)")

        # Subsecciones B7 (si están activas)
        if evaluation.get("b7_subsections"):
            lines.append(f"")
            lines.append("SUBSECCIONES B7 ACTIVADAS:")
            lines.append("-" * 70)
            for subsection, result in evaluation["b7_subsections"].items():
                lines.append(f"  {subsection}:")
                lines.append(f"    Puntos: {result['points_obtained']} / {result['max_points']}")
                lines.append(f"    Ítems: {result['items_matched']} / {result['items_total']} ({result['percentage']}%)")

        # Resumen
        lines.append(f"")
        lines.append("RESUMEN:")
        lines.append("-" * 70)
        summary = evaluation["summary"]
        lines.append(f"  Ítems evaluados: {summary['total_items_evaluated']}")
        lines.append(f"  Ítems cumplidos: {summary['total_items_matched']} ({summary['match_rate']}%)")
        lines.append(f"  Líneas estudiante: {summary['student_lines_count']}")
        lines.append(f"  Caracteres: {summary['student_text_length']}")

        lines.append("=" * 70)

        return "\n".join(lines)
