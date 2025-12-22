from typing import Any, Dict, List


def extract_v2_items(eval_transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract item-level signals from EvaluatorV2 output.
    """
    items: List[Dict[str, Any]] = []
    capas = eval_transcript.get("evaluacion_por_capas") or {}
    for capa_nombre, capa_data in capas.items():
        for item in capa_data.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "id": item.get("id"),
                    "done": bool(item.get("done")),
                    "critico": bool(item.get("critico")),
                    "match_type": item.get("match_type") or "",
                    "layer": capa_nombre,
                }
            )
    return items
