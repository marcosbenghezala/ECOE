"""
CaseAdapterV2 - Adaptación dinámica del checklist v2 según síntomas del caso.

OBJETIVO:
- Activar bloques universales (B0-B6, B8, B9) completos
- Activar SOLO las subsecciones B7 relevantes según síntomas del caso
- Recalcular max_points_case y min_points_case basado en items activos

EJEMPLO:
Caso "dolor torácico" → activa B7 CARDIOVASCULAR + RESPIRATORIO solamente
  → max_points_case = puntos_universales + puntos_B7_activas
  → min_points_case = recalculado según % de max_points_case
"""

import math
import re
from typing import Dict, List, Set, Optional
from pathlib import Path

from checklist_loader_v2 import ChecklistLoaderV2, load_checklist_v2


class CaseAdapterV2:
    """
    Adapta checklist v2 a un caso específico.

    Uso:
        adapter = CaseAdapterV2()
        adapted = adapter.adapt_to_case(case_data)
        # adapted contiene items activos, max_points_case, min_points_case
    """

    # Mapeo síntomas → subsecciones B7
    # Estructura: {síntoma: [subsecciones_activadas]}
    SYMPTOM_TO_SUBSECTIONS = {
        # Cardiovascular
        "dolor torácico": ["CARDIOVASCULAR", "RESPIRATORIO"],
        "dolor retroesternal": ["CARDIOVASCULAR"],
        "dolor opresivo": ["CARDIOVASCULAR"],
        "dolor precordial": ["CARDIOVASCULAR"],
        "palpitaciones": ["CARDIOVASCULAR"],
        "síncope": ["CARDIOVASCULAR", "NEUROLOGICO"],
        "sincope": ["CARDIOVASCULAR", "NEUROLOGICO"],  # sin tilde
        "mareo": ["CARDIOVASCULAR", "NEUROLOGICO"],
        "edemas": ["CARDIOVASCULAR"],
        "claudicación": ["CARDIOVASCULAR"],
        "claudicacion": ["CARDIOVASCULAR"],  # sin tilde
        "ortopnea": ["CARDIOVASCULAR", "RESPIRATORIO"],
        "disnea paroxística": ["CARDIOVASCULAR", "RESPIRATORIO"],
        "disnea": ["CARDIOVASCULAR", "RESPIRATORIO"],

        # Respiratorio
        "tos": ["RESPIRATORIO"],
        "expectoración": ["RESPIRATORIO"],
        "expectoracion": ["RESPIRATORIO"],  # sin tilde
        "hemoptisis": ["RESPIRATORIO"],
        "sibilancias": ["RESPIRATORIO"],
        "dolor costal": ["RESPIRATORIO"],

        # Digestivo
        "dolor abdominal": ["DIGESTIVO"],
        "náuseas": ["DIGESTIVO"],
        "nauseas": ["DIGESTIVO"],  # sin tilde
        "vómitos": ["DIGESTIVO"],
        "vomitos": ["DIGESTIVO"],  # sin tilde
        "diarrea": ["DIGESTIVO"],
        "estreñimiento": ["DIGESTIVO"],
        "estrenimiento": ["DIGESTIVO"],  # sin tilde
        "melenas": ["DIGESTIVO"],
        "hematoquecia": ["DIGESTIVO"],
        "hematemesis": ["DIGESTIVO"],
        "ictericia": ["DIGESTIVO"],
        "disfagia": ["DIGESTIVO"],
        "pirosis": ["DIGESTIVO"],
        "reflujo": ["DIGESTIVO"],

        # Neurológico
        "cefalea": ["NEUROLOGICO"],
        "mareo": ["NEUROLOGICO", "CARDIOVASCULAR"],
        "vértigo": ["NEUROLOGICO"],
        "vertigo": ["NEUROLOGICO"],  # sin tilde
        "pérdida de conciencia": ["NEUROLOGICO"],
        "perdida de conciencia": ["NEUROLOGICO"],  # sin tilde
        "confusión": ["NEUROLOGICO"],
        "confusion": ["NEUROLOGICO"],  # sin tilde
        "convulsiones": ["NEUROLOGICO"],
        "paresia": ["NEUROLOGICO"],
        "parestesias": ["NEUROLOGICO"],
        "diplopia": ["NEUROLOGICO"],
        "disartria": ["NEUROLOGICO"],

        # Genitourinario
        "disuria": ["GENITOURINARIO"],
        "polaquiuria": ["GENITOURINARIO"],
        "hematuria": ["GENITOURINARIO"],
        "incontinencia urinaria": ["GENITOURINARIO"],
        "dolor lumbar": ["GENITOURINARIO"],
        "dolor testicular": ["GENITOURINARIO"],
        "flujo vaginal": ["GENITOURINARIO"],
        "sangrado vaginal": ["GENITOURINARIO"],

        # Musculoesquelético
        "dolor articular": ["MUSCULOESQUELETICO"],
        "artralgia": ["MUSCULOESQUELETICO"],
        "mialgia": ["MUSCULOESQUELETICO"],
        "rigidez articular": ["MUSCULOESQUELETICO"],
        "inflamación articular": ["MUSCULOESQUELETICO"],
        "inflamacion articular": ["MUSCULOESQUELETICO"],  # sin tilde
        "limitación funcional": ["MUSCULOESQUELETICO"],
        "limitacion funcional": ["MUSCULOESQUELETICO"],  # sin tilde

        # Endocrino
        "poliuria": ["ENDOCRINO", "GENITOURINARIO"],
        "polidipsia": ["ENDOCRINO"],
        "polifagia": ["ENDOCRINO"],
        "pérdida de peso": ["ENDOCRINO"],
        "perdida de peso": ["ENDOCRINO"],  # sin tilde
        "ganancia de peso": ["ENDOCRINO"],
        "intolerancia al frío": ["ENDOCRINO"],
        "intolerancia al calor": ["ENDOCRINO"],
        "sudoración nocturna": ["ENDOCRINO"],
        "sudoracion nocturna": ["ENDOCRINO"],  # sin tilde

        # Dermatológico
        "lesión cutánea": ["DERMATOLOGICO"],
        "lesion cutanea": ["DERMATOLOGICO"],  # sin tilde
        "exantema": ["DERMATOLOGICO"],
        "prurito": ["DERMATOLOGICO"],
        "úlcera": ["DERMATOLOGICO"],
        "ulcera": ["DERMATOLOGICO"],  # sin tilde
        "alopecia": ["DERMATOLOGICO"],

        # Hematológico
        "equimosis": ["HEMATOLOGICO"],
        "petequias": ["HEMATOLOGICO"],
        "hematomas": ["HEMATOLOGICO"],
        "sangrado": ["HEMATOLOGICO"],
        "anemia": ["HEMATOLOGICO"],

        # Psiquiátrico
        "ansiedad": ["PSIQUIATRICO"],
        "depresión": ["PSIQUIATRICO"],
        "depresion": ["PSIQUIATRICO"],  # sin tilde
        "insomnio": ["PSIQUIATRICO"],
        "ánimo bajo": ["PSIQUIATRICO"],
        "animo bajo": ["PSIQUIATRICO"],  # sin tilde
        "pensamientos suicidas": ["PSIQUIATRICO"],
        "alucinaciones": ["PSIQUIATRICO"],
        "delirios": ["PSIQUIATRICO"],
    }

    # IDs de bloques universales (siempre activos)
    UNIVERSAL_BLOCK_IDS = [
        "B0_INTRODUCCION",
        "B1_MOTIVO_CONSULTA",
        "B2_HEA",
        "B3_ANTECEDENTES",
        "B4_MEDICACION_ALERGIAS",
        "B5_SOCIAL",
        "B6_FAMILIAR",
        "B8_CIERRE",
        "B9_COMUNICACION",
    ]

    def __init__(self, checklist_path: Optional[str] = None):
        """
        Inicializa el adaptador.

        Args:
            checklist_path: Ruta custom al checklist (opcional)
        """
        self.loader = load_checklist_v2(checklist_path)

    def _extract_symptoms(self, case_data: Dict) -> Set[str]:
        """
        Extrae síntomas del caso.

        Busca en:
        - case_data["sintomas_principales"] (lista)
        - case_data["motivo_consulta"] (string)
        - case_data["contexto_generado"] (string)

        Returns:
            Set de síntomas normalizados (lowercase)
        """
        symptoms = set()

        # De lista sintomas_principales
        if "sintomas_principales" in case_data:
            for s in case_data["sintomas_principales"]:
                symptoms.add(s.lower().strip())

        # De motivo_consulta (buscar matches con word boundaries)
        if "motivo_consulta" in case_data:
            text = case_data["motivo_consulta"].lower()
            for symptom_key in self.SYMPTOM_TO_SUBSECTIONS.keys():
                # Usar word boundaries para evitar matches parciales (ej: "tos" en "horas")
                pattern = r'\b' + re.escape(symptom_key) + r'\b'
                if re.search(pattern, text):
                    symptoms.add(symptom_key)

        # De contexto_generado (buscar matches con word boundaries)
        if "contexto_generado" in case_data:
            text = case_data["contexto_generado"].lower()
            for symptom_key in self.SYMPTOM_TO_SUBSECTIONS.keys():
                pattern = r'\b' + re.escape(symptom_key) + r'\b'
                if re.search(pattern, text):
                    symptoms.add(symptom_key)

        return symptoms

    def _get_active_subsections(self, symptoms: Set[str]) -> Set[str]:
        """
        Mapea síntomas → subsecciones B7 activas.

        Args:
            symptoms: Set de síntomas (lowercase)

        Returns:
            Set de subsecciones activas (ej: {"CARDIOVASCULAR", "RESPIRATORIO"})
        """
        active_subsections = set()

        for symptom in symptoms:
            if symptom in self.SYMPTOM_TO_SUBSECTIONS:
                for subsection in self.SYMPTOM_TO_SUBSECTIONS[symptom]:
                    active_subsections.add(subsection)

        # Si no hay síntomas que activen B7, activar TODAS las subsecciones (fallback)
        if not active_subsections:
            active_subsections = set(self.loader.list_subsections())

        return active_subsections

    def adapt_to_case(self, case_data: Dict) -> Dict:
        """
        Adapta el checklist completo al caso específico.

        Args:
            case_data: Dict con estructura de caso (sintomas_principales, etc.)

        Returns:
            Dict con:
                - items_activos: List[Dict] items aplicables al caso
                - max_points_case: int puntos máximos del caso
                - min_points_case: int puntos mínimos para aprobar
                - blocks_activos: Dict[block_id, points] puntos por bloque
                - subsections_b7_activas: List[str] subsecciones B7 activadas
        """
        # 1. Extraer síntomas
        symptoms = self._extract_symptoms(case_data)

        # 2. Determinar subsecciones B7 activas
        active_subsections_b7 = self._get_active_subsections(symptoms)

        # 3. Construir lista de items activos
        items_activos = []
        blocks_points = {}

        # Items de bloques universales (todos)
        for block_id in self.UNIVERSAL_BLOCK_IDS:
            block_items = self.loader.get_items_for_block(block_id)
            items_activos.extend(block_items)

            # Calcular puntos del bloque
            block_points = sum(it["points"] for it in block_items if not it.get("no_applicable", False))
            blocks_points[block_id] = block_points

        # Items de B7 (solo subsecciones activas)
        b7_items = []
        for subsection in active_subsections_b7:
            subsection_items = self.loader.get_items_for_subsection(subsection)
            b7_items.extend(subsection_items)

        items_activos.extend(b7_items)

        # Calcular puntos de B7
        b7_points = sum(it["points"] for it in b7_items if not it.get("no_applicable", False))
        blocks_points["B7_ANAMNESIS_APARATOS"] = b7_points

        # 4. Calcular max_points_case
        max_points_case = sum(
            it["points"]
            for it in items_activos
            if not it.get("no_applicable", False)
        )

        # 5. Calcular min_points_case (57.2% de max_points_case)
        passing_percentage = self.loader.metadata["passing_percentage"]
        min_points_case = math.ceil(max_points_case * passing_percentage / 100)

        # 6. Construir resultado
        return {
            "items_activos": items_activos,
            "max_points_case": max_points_case,
            "min_points_case": min_points_case,
            "blocks_activos": blocks_points,
            "subsections_b7_activas": sorted(active_subsections_b7),
            "total_items_activos": len(items_activos),
            "sintomas_detectados": sorted(symptoms),
        }
