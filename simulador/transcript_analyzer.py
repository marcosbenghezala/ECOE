#!/usr/bin/env python3
"""
Analizador de Transcript para detección inteligente de ítems del checklist.
Usa GPT-4 para inferir qué preguntas del checklist fueron realizadas.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path


def load_checklist_items(checklist_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Carga los ítems del checklist maestro."""
    if checklist_path is None:
        checklist_path = Path(__file__).parent / "data" / "master-checklist-v2.json"

    with open(checklist_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get("items", [])


def build_analysis_prompt(transcript: str, checklist_items: List[Dict[str, Any]]) -> str:
    """
    Construye el prompt para GPT-4 que analiza el transcript e identifica
    qué ítems del checklist fueron preguntados.
    """

    # Crear lista compacta de items (solo los más importantes para reducir tokens)
    items_summary = []
    for item in checklist_items:
        item_id = item.get("id", "")
        label = item.get("label", "")
        keywords = item.get("keywords", [])

        # Solo incluir items críticos o de mínimo para reducir el tamaño del prompt
        if item.get("is_minimum") or item.get("critical"):
            items_summary.append({
                "id": item_id,
                "label": label,
                "keywords": keywords[:5]  # Solo primeros 5 keywords
            })

    items_json = json.dumps(items_summary, ensure_ascii=False, indent=2)

    prompt = f"""Eres un evaluador médico experto. Analiza la siguiente conversación entre un ESTUDIANTE de medicina y un PACIENTE virtual.

Tu tarea es identificar QUÉ ÍTEMS DEL CHECKLIST fueron preguntados por el estudiante, basándote en:
1. Las preguntas explícitas del estudiante
2. Las respuestas del paciente (que revelan qué se le preguntó)
3. El contexto de la conversación

TRANSCRIPT:
```
{transcript}
```

ÍTEMS DEL CHECKLIST (solo ítems críticos/mínimos):
```json
{items_json}
```

INSTRUCCIONES:
- Devuelve SOLO un array JSON con los IDs de los ítems que fueron preguntados
- Ejemplo: ["B0_001", "B1_001", "B2_001"]
- NO inventes items que no fueron preguntados
- Si el estudiante preguntó sobre un tema aunque fuera de forma indirecta, cuenta
- Si el paciente respondió con información que claramente fue solicitada, cuenta

IMPORTANTE:
- Si el estudiante preguntó "¿Fumas?" o el paciente respondió sobre tabaco → B5_006
- Si preguntó sobre alcohol → B5_008
- Si preguntó sobre drogas → B5_010
- Si preguntó intensidad del dolor (1-10, escala) → B2_007
- Si preguntó dónde/localización del síntoma → B2_004
- Si preguntó irradiación (se extiende, va a algún lado, brazo) → B2_006

Devuelve SOLO el JSON, sin explicaciones:
"""

    return prompt


def analyze_transcript_with_gpt4(
    transcript: str,
    openai_client: Any,
    checklist_items: Optional[List[Dict[str, Any]]] = None
) -> List[str]:
    """
    Analiza el transcript usando GPT-4 para identificar ítems preguntados.

    Args:
        transcript: El transcript completo de la conversación
        openai_client: Cliente de OpenAI inicializado
        checklist_items: Lista de items del checklist (se carga si no se pasa)

    Returns:
        Lista de item_ids que fueron preguntados (ej: ["B5_006", "B2_007"])
    """
    if not transcript or not transcript.strip():
        return []

    if checklist_items is None:
        checklist_items = load_checklist_items()

    prompt = build_analysis_prompt(transcript, checklist_items)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un evaluador médico experto. Devuelves SOLO JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content.strip()

        # Intentar parsear el JSON
        try:
            result = json.loads(result_text)
            # Puede venir como {"items": [...]} o directamente [...]
            if isinstance(result, dict):
                items_asked = result.get("items", [])
            elif isinstance(result, list):
                items_asked = result
            else:
                items_asked = []

            # Validar que todos son strings
            items_asked = [str(item_id) for item_id in items_asked if item_id]

            print(f"📊 GPT-4 detectó {len(items_asked)} ítems preguntados: {items_asked[:10]}")
            return items_asked

        except json.JSONDecodeError as e:
            print(f"⚠️ Error parseando respuesta de GPT-4: {e}")
            print(f"   Respuesta: {result_text}")
            return []

    except Exception as e:
        print(f"❌ Error analizando transcript con GPT-4: {e}")
        import traceback
        traceback.print_exc()
        return []


def merge_detected_items(
    items_by_keywords: List[str],
    items_by_ai: List[str]
) -> List[str]:
    """
    Combina ítems detectados por keywords y por AI, eliminando duplicados.

    Args:
        items_by_keywords: Ítems detectados por el método tradicional (keywords)
        items_by_ai: Ítems detectados por GPT-4 analizando el transcript

    Returns:
        Lista unificada de item_ids únicos
    """
    all_items = set(items_by_keywords) | set(items_by_ai)
    return sorted(list(all_items))
