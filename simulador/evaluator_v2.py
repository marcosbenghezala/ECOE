"""
Evaluador V2 - Sistema de evaluación adaptativo con aprendizaje automático
Integra el sistema de 3 capas (Principal/Diferencial/Screening) y aprendizaje
"""
import json
import re
import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from openai import OpenAI
from datetime import datetime

from text_utils import (
    normalize_text as base_normalize_text,
    preprocess_transcript_by_role,
    extract_student_lines,
)

KEYWORD_MIN_RATIO_DEFAULT = 0.3
KEYWORD_MIN_RATIO_STRICT = 0.45
KEYWORD_MIN_RATIO_CRITICAL = 0.2
EMBEDDING_THRESHOLD_DEFAULT = 0.72
EMBEDDING_THRESHOLD_STRICT = 0.8
EMBEDDING_THRESHOLD_CRITICAL = 0.68
STRONG_KEYWORD_MARGIN = 0.1
STRONG_EMBEDDING_MARGIN = 0.05

CRITICAL_ITEM_IDS = {
    "CARDIO_01",
    "AP_01",
    "AP_11",
    "AF_01",
    "HAB_01",
}

HABIT_QUESTION_KEYWORDS = (
    "habitos",
    "consumo",
    "fumas",
    "fumar",
    "tabaco",
    "alcohol",
    "bebes",
    "bebe",
    "beber",
    "drogas",
)

SMOKING_PATIENT_KEYWORDS = (
    "fumo",
    "fumador",
    "fumadora",
    "cigarr",
    "tabaco",
    "paquete",
    "pitillo",
)

FAMILY_QUESTION_KEYWORDS = (
    "antecedentes familiares",
    "familia",
    "familiares",
    "padre",
    "madre",
    "hermano",
    "hermana",
)

FAMILY_PATIENT_KEYWORDS = (
    "padre",
    "madre",
    "hermano",
    "hermana",
    "familia",
    "familiar",
)

FAMILY_EVENT_KEYWORDS = (
    "infarto",
    "cardiaco",
    "cardiaca",
    "muerte",
    "fallecio",
)

CHRONIC_QUESTION_KEYWORDS = (
    "enfermedades cronicas",
    "enfermedades personales",
    "antecedentes personales",
    "problemas de salud",
)

CHRONIC_PATIENT_KEYWORDS = (
    "hta",
    "hipertension",
    "tension alta",
    "diabetes",
    "colesterol",
    "dislipemia",
)

MEDICATION_QUESTION_KEYWORDS = (
    "medicacion",
    "tratamiento",
    "pastillas",
    "tomas",
    "toma",
)

MEDICATION_PATIENT_KEYWORDS = (
    "enalapril",
    "atorvastatina",
    "atorcan",
    "estatinas",
    "statina",
    "medicacion",
    "tomo",
)

QUESTION_PREFIXES = (
    "pregunta por",
    "preguntar por",
    "pregunta sobre",
    "preguntar sobre",
    "explora",
    "indaga",
)

class EvaluatorV2:
    """
    Evaluador mejorado que:
    1. Usa master_items.json y embeddings
    2. Activa ítems basándose en SÍNTOMAS (no especialidad)
    3. Integra sistema de aprendizaje automático
    4. Sistema de 3 capas: Principal/Diferencial/Screening
    """

    def __init__(self,
                 api_key: str,
                 master_items_path: str,
                 embeddings_path: str,
                 index_path: str,
                 learning_system=None):
        """
        Inicializa el evaluador V2.

        Args:
            api_key: OpenAI API key
            master_items_path: Ruta al master_items.json
            embeddings_path: Ruta a embeddings (.npz)
            index_path: Ruta al índice de metadatos
            learning_system: Instancia de LearningSystem (opcional)
        """
        # Inicialización compatible con múltiples versiones de openai
        try:
            self.client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)
        except:
            self.client = OpenAI(api_key=api_key)

        # Cargar master items
        with open(master_items_path, 'r', encoding='utf-8') as f:
            self.master_data = json.load(f)

        # Cargar embeddings
        embeddings_data = np.load(embeddings_path)
        self.master_embeddings = embeddings_data['embeddings']

        # Cargar índice
        with open(index_path, 'r', encoding='utf-8') as f:
            self.master_index = json.load(f)
        self._embedding_index_by_id = {
            meta.get("id"): idx
            for idx, meta in enumerate(self.master_index)
            if meta.get("id")
        }

        # Sistema de aprendizaje (opcional)
        self.learning_system = learning_system
        self.embedding_threshold = EMBEDDING_THRESHOLD_DEFAULT
        self.embedding_threshold_strict = EMBEDDING_THRESHOLD_STRICT
        self.embedding_threshold_critical = EMBEDDING_THRESHOLD_CRITICAL
        self.keyword_min_ratio = KEYWORD_MIN_RATIO_DEFAULT
        self.keyword_min_ratio_strict = KEYWORD_MIN_RATIO_STRICT
        self.keyword_min_ratio_critical = KEYWORD_MIN_RATIO_CRITICAL
        self._synonym_patterns = [
            (re.compile(r"\bdecentes familiares\b"), ["antecedentes familiares"]),
            (re.compile(r"\bhistoria familiar\b"), ["antecedentes familiares"]),
            (re.compile(r"\bfamiliares\b"), ["antecedentes familiares"]),
            (re.compile(r"\bfamilia con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bpadre con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bmadre con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bmedicacion para la tension\b"), ["enfermedades cronicas", "medicacion actual"]),
            (re.compile(r"\bmedicacion\b.*\btension\b"), ["enfermedades cronicas", "medicacion actual"]),
            (re.compile(r"\bhta\b|\bhipertension\b|\btension alta\b"), ["enfermedades cronicas"]),
            (re.compile(r"\bdislipemia\b|\bcolesterol alto\b|\bcolesterol\b"), ["enfermedades cronicas"]),
            (re.compile(r"\bmedicacion\b|\btratamiento actual\b|\benalapril\b|\batorvastatina\b|\batorcan\b"), ["medicacion actual"]),
            (re.compile(r"\bfumas\b|\bfumador\b|\btabaco\b|\bcigarr"), ["habitos tabaco"]),
            (re.compile(r"\bbebes\b|\bbebe\b|\bbeber\b|\bcerveza\b|\bvino\b|\bwhisky\b|\bginebra\b|\bvodka\b"), ["alcohol", "habitos alcohol"]),
            (re.compile(r"\bconsumo de alcohol\b|\balcohol\b"), ["habitos alcohol"]),
        ]

    def normalize_text(self, text: str) -> str:
        """Normaliza texto para comparación"""
        return base_normalize_text(text)

    def normalize_text_with_synonyms(self, text: str) -> str:
        normalized = base_normalize_text(text)
        return self._expand_synonyms(normalized)

    def _expand_synonyms(self, text: str) -> str:
        if not text:
            return ""
        expanded = text
        for pattern, additions in self._synonym_patterns:
            if pattern.search(expanded):
                for addition in additions:
                    if addition not in expanded:
                        expanded = f"{expanded} {addition}"
        return expanded.strip()

    def _contains_any(self, text: str, keywords: Tuple[str, ...]) -> bool:
        if not text:
            return False
        for kw in keywords:
            if kw and kw in text:
                return True
        return False

    def _special_item_match(self, item_id: str, student_text: str, patient_text: str) -> Optional[str]:
        student_norm = self.normalize_text_with_synonyms(student_text)
        patient_norm = self.normalize_text_with_synonyms(patient_text)

        if item_id == "HAB_01":
            patient_smoking = self._contains_any(patient_norm, SMOKING_PATIENT_KEYWORDS)
            student_habits = self._contains_any(student_norm, HABIT_QUESTION_KEYWORDS)
            if patient_smoking and student_habits:
                return "keyword"

        if item_id == "AF_01":
            student_family = self._contains_any(student_norm, FAMILY_QUESTION_KEYWORDS)
            patient_family = (
                self._contains_any(patient_norm, FAMILY_PATIENT_KEYWORDS)
                and self._contains_any(patient_norm, FAMILY_EVENT_KEYWORDS)
            )
            if student_family and patient_family:
                return "keyword"

        if item_id == "AP_01":
            student_chronic = self._contains_any(student_norm, CHRONIC_QUESTION_KEYWORDS)
            patient_chronic = self._contains_any(patient_norm, CHRONIC_PATIENT_KEYWORDS)
            if student_chronic and patient_chronic:
                return "keyword"

        if item_id == "AP_11":
            student_med = self._contains_any(student_norm, MEDICATION_QUESTION_KEYWORDS)
            patient_med = self._contains_any(patient_norm, MEDICATION_PATIENT_KEYWORDS)
            if student_med and patient_med:
                return "keyword"

        return None

    def _is_question_item(self, item_text: str) -> bool:
        normalized = self.normalize_text(item_text)
        return normalized.startswith(QUESTION_PREFIXES)

    def _is_critical_item(self, item_id: str, item: Dict) -> bool:
        if item.get("critico"):
            return True
        return item_id in CRITICAL_ITEM_IDS

    def _keyword_match_stats(self, text: str, item: Dict) -> Tuple[int, int, float]:
        normalized_text = self.normalize_text_with_synonyms(text)
        keywords = item.get('keywords', []) or []
        if not keywords:
            return 0, 0, 0.0

        normalized_keywords = []
        for kw in keywords:
            kw_norm = self.normalize_text(kw)
            if kw_norm:
                normalized_keywords.append(kw_norm)

        if not normalized_keywords:
            return 0, 0, 0.0

        hits = 0
        for kw_norm in normalized_keywords:
            pattern = r"\b" + re.escape(kw_norm) + r"\b"
            if re.search(pattern, normalized_text):
                hits += 1

        ratio = hits / len(normalized_keywords)
        return hits, len(normalized_keywords), ratio

    def _patient_confirm(self, patient_text: str, item: Dict) -> bool:
        hits, total, _ratio = self._keyword_match_stats(patient_text, item)
        if total == 0:
            return False
        return hits >= 1

    def _max_embedding_similarity(
        self,
        transcript_embeddings: List[np.ndarray],
        item_embedding: Optional[np.ndarray],
    ) -> float:
        if not transcript_embeddings or item_embedding is None:
            return 0.0
        max_sim = 0.0
        for chunk_emb in transcript_embeddings:
            similarity = self.calculate_similarity(item_embedding, chunk_emb)
            if similarity > max_sim:
                max_sim = similarity
        return max_sim

    def _get_item_embedding(self, item_id: str) -> Optional[np.ndarray]:
        idx = self._embedding_index_by_id.get(item_id)
        if idx is None:
            return None
        try:
            return self.master_embeddings[idx]
        except Exception:
            return None

    def _match_item(
        self,
        item: Dict,
        capa_nombre: str,
        student_text: str,
        patient_text: str,
        transcript_embeddings: List[np.ndarray],
        use_embeddings: bool,
    ) -> Tuple[bool, Optional[str]]:
        item_text = item.get('texto') or item.get('item') or ''
        item_id = item.get('id', 'UNKNOWN')
        is_question_item = self._is_question_item(item_text)
        is_critical = self._is_critical_item(item_id, item)

        keyword_ratio = self.keyword_min_ratio
        embedding_threshold = self.embedding_threshold
        strict_group = capa_nombre in {"DIFERENCIAL", "SCREENING"}
        if strict_group and not is_critical:
            keyword_ratio = self.keyword_min_ratio_strict
            embedding_threshold = self.embedding_threshold_strict
        elif is_critical:
            keyword_ratio = self.keyword_min_ratio_critical
            embedding_threshold = self.embedding_threshold_critical

        hits, total, ratio = self._keyword_match_stats(student_text, item)
        keyword_match = total > 0 and ratio >= keyword_ratio

        embedding_match = False
        max_similarity = 0.0
        if use_embeddings and transcript_embeddings:
            item_emb = self._get_item_embedding(item_id)
            max_similarity = self._max_embedding_similarity(transcript_embeddings, item_emb)
            embedding_match = max_similarity >= embedding_threshold

        student_match = keyword_match or embedding_match
        special_match = self._special_item_match(item_id, student_text, patient_text)
        if special_match:
            return True, special_match

        if is_question_item and not student_match:
            return False, None

        if not student_match:
            return False, None

        patient_confirm = self._patient_confirm(patient_text, item)

        strong_keyword = keyword_match and ratio >= (keyword_ratio + STRONG_KEYWORD_MARGIN)
        strong_embedding = embedding_match and max_similarity >= (embedding_threshold + STRONG_EMBEDDING_MARGIN)
        strong_match = strong_keyword or strong_embedding or keyword_match

        if strict_group and not is_critical and embedding_match and not keyword_match:
            # En ítems estrictos evitamos match solo semántico sin confirmación del paciente.
            if not patient_confirm:
                return False, None

        if not strong_match and not patient_confirm:
            return False, None

        match_type = "keyword" if keyword_match else "embedding"
        return True, match_type

    def get_embedding(self, text: str) -> np.ndarray:
        """Genera embedding para un texto"""
        text = text.replace("\n", " ")
        response = self.client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return np.array(response.data[0].embedding)

    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calcula similitud coseno entre dos embeddings"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def activate_items_by_symptoms(self, sintomas_caso: List[str]) -> Dict:
        """
        Activa ítems basándose en los síntomas del caso (no en especialidad).

        Args:
            sintomas_caso: Lista de síntomas principales del caso

        Returns:
            Diccionario con ítems activados organizados por capas
        """
        # SIEMPRE activar bloques universales
        bloques_universales = self.master_data['bloques_universales']

        # Activar items por sistemas según síntomas
        items_activados_sistemas = {}
        items_por_sistemas = self.master_data['items_por_sistemas']

        for sistema_key, sistema_data in items_por_sistemas.items():
            sistema_items = []
            for item in sistema_data['items']:
                sintomas_trigger = item.get('sintomas_trigger', [])

                # Verificar si algún síntoma del caso coincide con triggers del ítem
                for sintoma_caso in sintomas_caso:
                    sintoma_caso_norm = self.normalize_text(sintoma_caso)
                    for trigger in sintomas_trigger:
                        if self.normalize_text(trigger) in sintoma_caso_norm or \
                           sintoma_caso_norm in self.normalize_text(trigger):
                            sistema_items.append(item)
                            break  # No añadir duplicados

            if sistema_items:
                items_activados_sistemas[sistema_key] = {
                    'nombre': sistema_data['nombre'],
                    'items': sistema_items
                }

        return {
            'bloques_universales': bloques_universales,
            'items_por_sistemas': items_activados_sistemas
        }

    def organize_by_layers(self, items_activados: Dict) -> Dict:
        """
        Organiza los ítems activados en 3 capas: Principal/Diferencial/Screening

        Args:
            items_activados: Ítems activados por síntomas

        Returns:
            Diccionario con capas organizadas
        """
        capa_principal = []    # Ítems críticos o cardinales
        capa_diferencial = []  # Diagnóstico diferencial
        capa_screening = []    # Contexto y comunicación

        # Procesar bloques universales
        for bloque_key, bloque_data in items_activados['bloques_universales'].items():
            for item in bloque_data['items']:
                tipo = item.get('tipo', 'cardinal')
                critico = item.get('critico', False)

                if critico or tipo == 'cardinal':
                    capa_principal.append(item)
                elif tipo == 'diagnostico_diferencial':
                    capa_diferencial.append(item)
                else:  # comunicacion, contexto
                    capa_screening.append(item)

        # Procesar items por sistemas
        for sistema_key, sistema_data in items_activados['items_por_sistemas'].items():
            for item in sistema_data['items']:
                tipo = item.get('tipo', 'cardinal')
                critico = item.get('critico', False)

                if critico or tipo == 'cardinal':
                    capa_principal.append(item)
                elif tipo == 'diagnostico_diferencial':
                    capa_diferencial.append(item)
                else:
                    capa_screening.append(item)

        return {
            'PRINCIPAL': capa_principal,
            'DIFERENCIAL': capa_diferencial,
            'SCREENING': capa_screening
        }

    def check_item_keyword(self, transcript: str, item: Dict, min_ratio: Optional[float] = None) -> bool:
        """Verifica ítem usando keywords"""
        hits, total, _ratio = self._keyword_match_stats(transcript, item)
        if total == 0:
            return False
        ratio = self.keyword_min_ratio if min_ratio is None else min_ratio
        min_hits = max(1, int(math.ceil(total * ratio)))
        return hits >= min_hits

    def check_item_embedding(self,
                            transcript_embeddings: List[np.ndarray],
                            item_embedding: np.ndarray,
                            threshold: Optional[float] = None) -> bool:
        """Verifica ítem usando similitud semántica"""
        if not transcript_embeddings or item_embedding is None:
            return False

        threshold = self.embedding_threshold if threshold is None else threshold
        for chunk_emb in transcript_embeddings:
            similarity = self.calculate_similarity(item_embedding, chunk_emb)
            if similarity >= threshold:
                return True

        return False

    def _dedupe_items_by_id(self, items: List[Dict]) -> List[Dict]:
        seen = set()
        deduped = []
        for item in items:
            item_id = item.get("id")
            if not item_id:
                deduped.append(item)
                continue
            if item_id in seen:
                continue
            seen.add(item_id)
            deduped.append(item)
        return deduped

    def detect_student_questions(self, transcript: str) -> List[str]:
        """
        Detecta preguntas realizadas por el estudiante en la transcripción.
        Útil para el sistema de aprendizaje automático.

        Args:
            transcript: Transcripción completa

        Returns:
            Lista de preguntas detectadas
        """
        student_lines = extract_student_lines(transcript)
        student_text = "\n".join(student_lines) if student_lines else transcript
        questions = re.findall(r'[^.!?]*\?', student_text)
        # Limpiar y filtrar
        questions = [q.strip() for q in questions if len(q.strip()) > 10]

        return questions

    def evaluate_transcript(self,
                           transcript: str,
                           sintomas_caso: List[str],
                           caso_id: str,
                           incluir_aprendizaje: bool = True,
                           use_embeddings: bool = True) -> Dict:
        """
        Evalúa una transcripción completa usando el sistema V2.

        Args:
            transcript: Transcripción de la conversación
            sintomas_caso: Síntomas principales del caso
            caso_id: ID del caso evaluado
            incluir_aprendizaje: Si debe registrar candidatos para aprendizaje
            use_embeddings: Si se deben usar embeddings semánticos

        Returns:
            Reporte completo de evaluación
        """
        print(f"🔍 Evaluando transcripción del caso {caso_id}...")

        # 1. Activar ítems según síntomas
        items_activados = self.activate_items_by_symptoms(sintomas_caso)

        # 2. Organizar por capas (3 niveles)
        items_por_capas = self.organize_by_layers(items_activados)

        # 3. Separar turnos por rol y preparar embeddings (solo estudiante)
        preprocessed = preprocess_transcript_by_role(transcript)
        student_lines = preprocessed.get("student_lines") or []
        patient_lines = preprocessed.get("patient_lines") or []
        student_text = "\n".join(student_lines).strip() or transcript.strip()
        patient_text = "\n".join(patient_lines).strip()

        transcript_embeddings: List[np.ndarray] = []
        if use_embeddings:
            chunks = []
            source_lines = student_lines if student_lines else [transcript]
            for line in source_lines:
                for chunk in re.split(r'[.!?]\s+', line):
                    if len(chunk.strip()) > 10:
                        chunks.append(chunk.strip())

            if chunks:
                try:
                    resp = self.client.embeddings.create(
                        input=chunks,
                        model="text-embedding-3-small"
                    )
                    transcript_embeddings = [np.array(d.embedding) for d in resp.data]
                except Exception as e:
                    print(f"⚠️ Error generando embeddings: {e}")

        # 4. Evaluar cada capa
        evaluacion_por_capas = {}
        total_score = 0
        max_score = 0

        for capa_nombre, items in items_por_capas.items():
            resultados_capa = []
            deduped_items = self._dedupe_items_by_id(items)

            for item in deduped_items:
                peso = item.get('peso', 1)
                max_score += peso

                item_text = item.get('texto', 'Unknown Item')
                item_id = item.get('id', 'UNKNOWN')
                is_done, match_type = self._match_item(
                    item=item,
                    capa_nombre=capa_nombre,
                    student_text=student_text,
                    patient_text=patient_text,
                    transcript_embeddings=transcript_embeddings,
                    use_embeddings=use_embeddings,
                )

                score = peso if is_done else 0
                total_score += score

                resultados_capa.append({
                    'id': item_id,
                    'item': item_text,
                    'tipo': item.get('tipo', 'cardinal'),
                    'critico': item.get('critico', False),
                    'done': is_done,
                    'match_type': match_type,
                    'score': score,
                    'max_score': peso
                })

            evaluacion_por_capas[capa_nombre] = {
                'items': resultados_capa,
                'total_items': len(deduped_items),
                'items_completados': sum(1 for r in resultados_capa if r['done']),
                'score': sum(r['score'] for r in resultados_capa),
                'max_score': sum(r['max_score'] for r in resultados_capa)
            }

        # 5. Sistema de aprendizaje automático (detectar nuevos ítems)
        candidatos_detectados = []
        if incluir_aprendizaje and self.learning_system:
            preguntas_estudiante = self.detect_student_questions(transcript)

            for pregunta in preguntas_estudiante:
                try:
                    resultado = self.learning_system.register_candidate(
                        pregunta_estudiante=pregunta,
                        caso_id=caso_id,
                        contexto={'sintomas_caso': sintomas_caso}
                    )
                    if resultado['es_nuevo']:
                        candidatos_detectados.append({
                            'pregunta': pregunta,
                            'analisis': resultado['analisis']
                        })
                except Exception as e:
                    print(f"⚠️ Error en aprendizaje automático: {e}")

        # 6. Calcular puntuación final
        porcentaje = (total_score / max_score * 100) if max_score > 0 else 0

        # Determinar calificación (Sobresaliente/Notable/Bien/Suficiente/Insuficiente)
        if porcentaje >= 90:
            calificacion = "Sobresaliente"
        elif porcentaje >= 75:
            calificacion = "Notable"
        elif porcentaje >= 60:
            calificacion = "Bien"
        elif porcentaje >= 50:
            calificacion = "Suficiente"
        else:
            calificacion = "Insuficiente"

        # 7. Generar reporte completo
        reporte = {
            'caso_id': caso_id,
            'fecha_evaluacion': datetime.now().isoformat(),
            'sintomas_caso': sintomas_caso,
            'puntuacion': {
                'total_score': total_score,
                'max_score': max_score,
                'porcentaje': round(porcentaje, 2),
                'calificacion': calificacion
            },
            'evaluacion_por_capas': evaluacion_por_capas,
            'estadisticas': {
                'total_items_activados': max_score,
                'items_completados': sum(
                    capa['items_completados'] for capa in evaluacion_por_capas.values()
                ),
                'items_criticos_completados': sum(
                    1 for capa in evaluacion_por_capas.values()
                    for item in capa['items']
                    if item['critico'] and item['done']
                ),
                'items_criticos_totales': sum(
                    1 for capa in evaluacion_por_capas.values()
                    for item in capa['items']
                    if item['critico']
                )
            },
            'aprendizaje_automatico': {
                'habilitado': incluir_aprendizaje and self.learning_system is not None,
                'candidatos_nuevos_detectados': len(candidatos_detectados),
                'candidatos': candidatos_detectados
            }
        }

        print(f"✅ Evaluación completada: {calificacion} ({porcentaje:.1f}%)")

        return reporte

    def generate_feedback(self, reporte: Dict) -> str:
        """
        Genera feedback cualitativo usando GPT-4 basado en el reporte.

        Args:
            reporte: Reporte de evaluación generado

        Returns:
            Feedback en texto natural
        """
        # Preparar información para GPT-4
        items_no_completados = []
        for capa_nombre, capa_data in reporte['evaluacion_por_capas'].items():
            for item in capa_data['items']:
                if not item['done']:
                    items_no_completados.append({
                        'capa': capa_nombre,
                        'item': item['item'],
                        'critico': item['critico']
                    })

        prompt = f"""Eres un profesor de medicina evaluando a un estudiante en una simulación ECOE.

Calificación obtenida: {reporte['puntuacion']['calificacion']} ({reporte['puntuacion']['porcentaje']:.1f}%)

Items completados: {reporte['estadisticas']['items_completados']}/{reporte['estadisticas']['total_items_activados']}

Items críticos: {reporte['estadisticas']['items_criticos_completados']}/{reporte['estadisticas']['items_criticos_totales']}

Items NO completados:
{json.dumps(items_no_completados, ensure_ascii=False, indent=2)}

Genera un feedback constructivo (3-5 párrafos) que:
1. Felicite por los logros
2. Señale áreas de mejora específicas
3. Dé consejos prácticos
4. Sea motivador y educativo

Usa un tono cercano y profesional."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un profesor experto en medicina clínica."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Error generando feedback: {e}")
            return "Feedback no disponible en este momento."


if __name__ == "__main__":
    # Test básico
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    evaluator = EvaluatorV2(
        api_key=api_key,
        master_items_path=os.path.join(BASE_DIR, 'data', 'master_items.json'),
        embeddings_path=os.path.join(BASE_DIR, 'data', 'master_items_embeddings.npz'),
        index_path=os.path.join(BASE_DIR, 'data', 'master_items_index.json')
    )

    # Test de evaluación
    transcript = """
    Hola, buenos días. Soy Juan, estudiante de medicina.
    ¿Cómo se encuentra hoy? Vengo a tomarle la historia clínica.
    ¿Cuál es el motivo de su consulta?
    Me dice que tiene dolor en el pecho. ¿Desde cuándo tiene ese dolor?
    ¿El dolor es constante o va y viene?
    ¿Qué intensidad tiene del 1 al 10?
    """

    sintomas = ["dolor torácico", "disnea"]

    reporte = evaluator.evaluate_transcript(
        transcript=transcript,
        sintomas_caso=sintomas,
        caso_id="TEST_001",
        incluir_aprendizaje=False
    )

    print("\n" + "="*70)
    print("REPORTE DE EVALUACIÓN")
    print("="*70)
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
