import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_ITEMS_PATH = Path(__file__).resolve().parent.parent / "data" / "evaluation_items.json"


def _load_items_raw(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_item_mappings(path: str = "") -> Tuple[Dict[str, List[str]], Dict[str, bool]]:
    """
    Load V2 -> V3 mappings and critical flags.

    Returns:
        v2_to_v3: Dict[v2_id, List[v3_id]]
        v3_critical: Dict[v3_id, bool]
    """
    items_path = Path(path) if path else DEFAULT_ITEMS_PATH
    raw = _load_items_raw(items_path)

    v2_to_v3: Dict[str, List[str]] = {}
    v3_critical: Dict[str, bool] = {}

    for entry in raw.get("mappings", []) or []:
        v2_id = str(entry.get("v2_id") or "").strip()
        v3_ids = [str(x).strip() for x in (entry.get("v3_ids") or []) if str(x).strip()]
        if not v2_id or not v3_ids:
            continue
        v2_to_v3[v2_id] = v3_ids
        if entry.get("critical"):
            for vid in v3_ids:
                v3_critical[vid] = True

    return v2_to_v3, v3_critical
