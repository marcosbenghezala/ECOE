"""
Sistema de Aprendizaje Automático para el Checklist ECOE
Permite que el sistema aprenda nuevos ítems automáticamente basándose en patrones de uso
"""
import json
import numpy as np
import os
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from datetime import datetime

class LearningSystem:
    """
    Sistema de aprendizaje automático que detecta y sugiere nuevos ítems
    basándose en la similitud semántica con el checklist maestro.
    """

    def __init__(self,
                 master_items_path: str,
                 embeddings_path: str,
                 index_path: str,
                 api_key: str,
                 config: Optional[Dict] = None):
        """
        Inicializa el sistema de aprendizaje.

        Args:
            master_items_path: Ruta al master_items.json
            embeddings_path: Ruta a los embeddings (.npz)
            index_path: Ruta al índice de metadatos (.json)
            api_key: OpenAI API key
            config: Configuración del sistema (umbrales, etc.)
        """
        self.client = OpenAI(api_key=api_key)
        self.master_items_path = master_items_path
        self.embeddings_path = embeddings_path
        self.index_path = index_path

        # Cargar datos maestros
        with open(master_items_path, 'r', encoding='utf-8') as f:
            self.master_data = json.load(f)

        # Cargar embeddings
        embeddings_data = np.load(embeddings_path)
        self.master_embeddings = embeddings_data['embeddings']

        # Cargar índice
        with open(index_path, 'r', encoding='utf-8') as f:
            self.master_index = json.load(f)

        # Configuración del sistema de aprendizaje
        self.config = config or self.master_data.get('sistema_aprendizaje', {})
        self.umbral_similitud_minimo = self.config.get('reglas', {}).get('umbral_similitud_minimo', 0.85)
        self.umbral_similitud_alto = self.config.get('reglas', {}).get('umbral_similitud_alto', 0.92)
        self.minimo_casos_para_aprender = self.config.get('reglas', {}).get('minimo_casos_para_aprender', 3)
        self.requiere_validacion_humana = self.config.get('reglas', {}).get('requiere_validacion_humana', True)

        # Historial de candidatos a nuevos ítems
        self.candidatos_path = os.path.join(
            os.path.dirname(master_items_path),
            'candidatos_nuevos_items.json'
        )
        self.candidatos = self._load_candidatos()

    def _load_candidatos(self) -> Dict:
        """Carga el archivo de candidatos a nuevos ítems"""
        if os.path.exists(self.candidatos_path):
            with open(self.candidatos_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'version': '1.0',
            'fecha_creacion': datetime.now().isoformat(),
            'candidatos': [],
            'aprobados': [],
            'rechazados': []
        }

    def _save_candidatos(self):
        """Guarda el archivo de candidatos"""
        with open(self.candidatos_path, 'w', encoding='utf-8') as f:
            json.dump(self.candidatos, f, ensure_ascii=False, indent=2)

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Genera embedding para un texto usando OpenAI API.

        Args:
            text: Texto a convertir en embedding

        Returns:
            numpy array con el embedding
        """
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calcula similitud coseno entre dos embeddings.

        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding

        Returns:
            Similitud coseno (0-1)
        """
        return np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

    def find_most_similar_item(self, new_text: str) -> Tuple[Dict, float]:
        """
        Encuentra el ítem más similar del maestro a un texto nuevo.

        Args:
            new_text: Texto del posible nuevo ítem

        Returns:
            (item_metadata, similarity_score)
        """
        # Generar embedding del nuevo texto
        new_embedding = self.generate_embedding(new_text)

        # Calcular similitudes con todos los ítems del maestro
        similarities = []
        for i, master_emb in enumerate(self.master_embeddings):
            sim = self.calculate_similarity(new_embedding, master_emb)
            similarities.append((i, sim))

        # Encontrar el más similar
        most_similar_idx, max_similarity = max(similarities, key=lambda x: x[1])
        most_similar_item = self.master_index[most_similar_idx]

        return most_similar_item, max_similarity

    def is_new_item(self, text: str, threshold: Optional[float] = None) -> Tuple[bool, Dict]:
        """
        Determina si un texto representa un ítem verdaderamente nuevo.

        Args:
            text: Texto del posible nuevo ítem
            threshold: Umbral de similitud (usa el del config si no se especifica)

        Returns:
            (is_new, analysis_info)
        """
        threshold = threshold or self.umbral_similitud_minimo

        most_similar, similarity = self.find_most_similar_item(text)

        analysis = {
            'texto_evaluado': text,
            'item_mas_similar': most_similar,
            'similitud': similarity,
            'umbral_usado': threshold,
            'es_nuevo': similarity < threshold,
            'confianza': 'alta' if similarity < self.umbral_similitud_minimo else
                        'media' if similarity < self.umbral_similitud_alto else 'baja'
        }

        return similarity < threshold, analysis

    def register_candidate(self,
                          pregunta_estudiante: str,
                          caso_id: str,
                          contexto: Optional[Dict] = None) -> Dict:
        """
        Registra una pregunta del estudiante como candidato a nuevo ítem.

        Args:
            pregunta_estudiante: Pregunta realizada por el estudiante
            caso_id: ID del caso donde ocurrió
            contexto: Información adicional (síntomas del caso, etc.)

        Returns:
            Información del análisis y registro
        """
        # Analizar si es nueva
        is_new, analysis = self.is_new_item(pregunta_estudiante)

        # Buscar si ya existe como candidato
        candidato_existente = None
        for candidato in self.candidatos['candidatos']:
            if candidato['texto_normalizado'] == pregunta_estudiante.lower().strip():
                candidato_existente = candidato
                break

        if candidato_existente:
            # Incrementar contador de ocurrencias
            candidato_existente['ocurrencias'] += 1
            candidato_existente['casos'].append({
                'caso_id': caso_id,
                'fecha': datetime.now().isoformat(),
                'contexto': contexto
            })
        else:
            # Crear nuevo candidato
            nuevo_candidato = {
                'id': f"CAND_{len(self.candidatos['candidatos']) + 1:03d}",
                'texto': pregunta_estudiante,
                'texto_normalizado': pregunta_estudiante.lower().strip(),
                'fecha_primera_ocurrencia': datetime.now().isoformat(),
                'ocurrencias': 1,
                'casos': [{
                    'caso_id': caso_id,
                    'fecha': datetime.now().isoformat(),
                    'contexto': contexto
                }],
                'analisis': analysis,
                'estado': 'pendiente',  # pendiente, aprobado, rechazado
                'validacion_humana': None
            }
            self.candidatos['candidatos'].append(nuevo_candidato)

        # Guardar candidatos
        self._save_candidatos()

        return {
            'es_nuevo': is_new,
            'analisis': analysis,
            'accion': 'actualizado' if candidato_existente else 'creado'
        }

    def get_candidates_for_review(self, min_ocurrencias: Optional[int] = None) -> List[Dict]:
        """
        Obtiene candidatos que necesitan revisión humana.

        Args:
            min_ocurrencias: Mínimo de ocurrencias para considerar (usa config si no se especifica)

        Returns:
            Lista de candidatos pendientes de revisión
        """
        min_occ = min_ocurrencias or self.minimo_casos_para_aprender

        candidatos_para_revision = []
        for candidato in self.candidatos['candidatos']:
            if (candidato['estado'] == 'pendiente' and
                candidato['ocurrencias'] >= min_occ):
                candidatos_para_revision.append(candidato)

        # Ordenar por ocurrencias (más frecuentes primero)
        return sorted(candidatos_para_revision, key=lambda x: x['ocurrencias'], reverse=True)

    def approve_candidate(self,
                         candidato_id: str,
                         item_metadata: Dict,
                         validador: str) -> Dict:
        """
        Aprueba un candidato y lo añade al master_items.json

        Args:
            candidato_id: ID del candidato a aprobar
            item_metadata: Metadatos completos del nuevo ítem (keywords, peso, etc.)
            validador: Nombre de quien valida (profesor/sistema)

        Returns:
            Información de la aprobación
        """
        # Buscar candidato
        candidato = None
        for c in self.candidatos['candidatos']:
            if c['id'] == candidato_id:
                candidato = c
                break

        if not candidato:
            raise ValueError(f"Candidato {candidato_id} no encontrado")

        # Actualizar estado del candidato
        candidato['estado'] = 'aprobado'
        candidato['validacion_humana'] = {
            'validador': validador,
            'fecha': datetime.now().isoformat(),
            'metadatos': item_metadata
        }

        # Mover a lista de aprobados
        self.candidatos['aprobados'].append(candidato)
        self.candidatos['candidatos'].remove(candidato)

        # Añadir al master_items.json
        # (esto requiere determinar el bloque/sistema correcto)
        nuevo_item = {
            'id': item_metadata['id'],
            'texto': candidato['texto'],
            'descripcion': item_metadata.get('descripcion', ''),
            'keywords': item_metadata.get('keywords', []),
            'sintomas_trigger': item_metadata.get('sintomas_trigger', []),
            'frases_ejemplo': [candidato['texto']],
            'peso': item_metadata.get('peso', 1),
            'critico': item_metadata.get('critico', False),
            'nivel': item_metadata.get('nivel', 'basico'),
            'tipo': item_metadata.get('tipo', 'cardinal'),
            'aprendido_automaticamente': True,
            'fecha_aprobacion': datetime.now().isoformat(),
            'validador': validador
        }

        # Guardar cambios
        self._save_candidatos()

        return {
            'candidato_id': candidato_id,
            'nuevo_item': nuevo_item,
            'mensaje': f'Candidato {candidato_id} aprobado e incorporado al maestro'
        }

    def reject_candidate(self, candidato_id: str, razon: str, validador: str) -> Dict:
        """
        Rechaza un candidato (no es un ítem válido).

        Args:
            candidato_id: ID del candidato a rechazar
            razon: Razón del rechazo
            validador: Nombre de quien valida

        Returns:
            Información del rechazo
        """
        # Buscar candidato
        candidato = None
        for c in self.candidatos['candidatos']:
            if c['id'] == candidato_id:
                candidato = c
                break

        if not candidato:
            raise ValueError(f"Candidato {candidato_id} no encontrado")

        # Actualizar estado
        candidato['estado'] = 'rechazado'
        candidato['validacion_humana'] = {
            'validador': validador,
            'fecha': datetime.now().isoformat(),
            'razon': razon
        }

        # Mover a rechazados
        self.candidatos['rechazados'].append(candidato)
        self.candidatos['candidatos'].remove(candidato)

        self._save_candidatos()

        return {
            'candidato_id': candidato_id,
            'mensaje': f'Candidato {candidato_id} rechazado: {razon}'
        }

    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas del sistema de aprendizaje.

        Returns:
            Diccionario con estadísticas
        """
        return {
            'total_candidatos_pendientes': len(self.candidatos['candidatos']),
            'total_aprobados': len(self.candidatos['aprobados']),
            'total_rechazados': len(self.candidatos['rechazados']),
            'candidatos_listos_para_revision': len(
                self.get_candidates_for_review()
            ),
            'configuracion': {
                'umbral_similitud_minimo': self.umbral_similitud_minimo,
                'umbral_similitud_alto': self.umbral_similitud_alto,
                'minimo_casos_para_aprender': self.minimo_casos_para_aprender,
                'requiere_validacion_humana': self.requiere_validacion_humana
            }
        }
