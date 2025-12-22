from typing import Any, Dict


def index_v3_items(eval_v3: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Index EvaluatorV3 items by item_id.
    """
    indexed: Dict[str, Dict[str, Any]] = {}
    for item in eval_v3.get("items_evaluated", []) or []:
        if not isinstance(item, dict):
            continue
        item_id = item.get("item_id")
        if not item_id:
            continue
        indexed[str(item_id)] = item
    return indexed
