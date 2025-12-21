"""
Evaluador V2 - Sistema de evaluación adaptativo con aprendizaje automático
Integra el sistema de 3 capas (Principal/Diferencial/Screening) y aprendizaje
"""
import json
import re
import numpy as np
from typing import Dict, List, Tuple, Optional
from openai import OpenAI
from datetime import datetime

from text_utils import normalize_text as base_normalize_text

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

        # Sistema de aprendizaje (opcional)
        self.learning_system = learning_system
        self.embedding_threshold = 0.75
        self._synonym_patterns = [
            (re.compile(r"\bdecentes familiares\b"), ["antecedentes familiares"]),
            (re.compile(r"\bhistoria familiar\b"), ["antecedentes familiares"]),
            (re.compile(r"\bfamilia con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bpadre con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bmadre con infarto\b"), ["antecedentes familiares"]),
            (re.compile(r"\bmedicacion para la tension\b"), ["enfermedades cronicas", "medicacion actual"]),
            (re.compile(r"\bmedicacion\b.*\btension\b"), ["enfermedades cronicas", "medicacion actual"]),
            (re.compile(r"\bhta\b|\bhipertension\b|\btension alta\b"), ["enfermedades cronicas"]),
            (re.compile(r"\bdislipemia\b|\bcolesterol alto\b"), ["enfermedades cronicas"]),
            (re.compile(r"\bmedicacion\b|\btratamiento actual\b|\benalapril\b|\batorvastatina\b|\batorcan\b"), ["medicacion actual"]),
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

    def check_item_keyword(self, transcript: str, item: Dict) -> bool:
        """Verifica ítem usando keywords"""
        normalized_transcript = self.normalize_text_with_synonyms(transcript)
        keywords = item.get('keywords', []) or []

        if not keywords:
            return False

        normalized_keywords = []
        for kw in keywords:
            kw_norm = self.normalize_text(kw)
            if kw_norm:
                normalized_keywords.append(kw_norm)

        if not normalized_keywords:
            return False

        hits = 0
        for kw_norm in normalized_keywords:
            pattern = r"\b" + re.escape(kw_norm) + r"\b"
            if re.search(pattern, normalized_transcript):
                hits += 1

        # Umbral flexible para mejorar recall sin disparar falsos positivos.
        min_hits = max(1, int(len(normalized_keywords) * 0.34))
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
        # Detectar preguntas (texto seguido de ?)
        questions = re.findall(r'[^.!?]*\?', transcript)
        # Limpiar y filtrar
        questions = [q.strip() for q in questions if len(q.strip()) > 10]

        return questions

    def evaluate_transcript(self,
                           transcript: str,
                           sintomas_caso: List[str],
                           caso_id: str,
                           incluir_aprendizaje: bool = True) -> Dict:
        """
        Evalúa una transcripción completa usando el sistema V2.

        Args:
            transcript: Transcripción de la conversación
            sintomas_caso: Síntomas principales del caso
            caso_id: ID del caso evaluado
            incluir_aprendizaje: Si debe registrar candidatos para aprendizaje

        Returns:
            Reporte completo de evaluación
        """
        print(f"🔍 Evaluando transcripción del caso {caso_id}...")

        # 1. Activar ítems según síntomas
        items_activados = self.activate_items_by_symptoms(sintomas_caso)

        # 2. Organizar por capas (3 niveles)
        items_por_capas = self.organize_by_layers(items_activados)

        # 3. Pre-calcular embeddings de la transcripción
        chunks = re.split(r'[.!?]\s+', transcript)
        chunks = [c for c in chunks if len(c) > 10]

        transcript_embeddings = []
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

                # Método 1: Keywords
                is_done = self.check_item_keyword(transcript, item)
                match_type = "keyword" if is_done else None

                # Método 2: Embedding (si no encontrado por keywords)
                if not is_done:
                    # Buscar embedding del item en master_embeddings
                    item_idx = None
                    for idx, meta in enumerate(self.master_index):
                        if meta['id'] == item_id:
                            item_idx = idx
                            break

                    if item_idx is not None:
                        item_emb = self.master_embeddings[item_idx]
                        if self.check_item_embedding(transcript_embeddings, item_emb):
                            is_done = True
                            match_type = "embedding"

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
