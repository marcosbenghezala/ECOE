import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from checklist_loader_v2 import load_checklist_v2
except Exception:  # pragma: no cover
    load_checklist_v2 = None  # type: ignore

from evaluation.adapters.reflection_adapter import build_development_questions
from evaluation.adapters.v2_adapter import extract_v2_items
from evaluation.adapters.v3_adapter import index_v3_items
from evaluation.items_registry import load_item_mappings


DEFAULT_WEIGHTS = {"checklist": 0.7, "development": 0.3}


def build_unified_evaluation(
    *,
    case_data: Dict[str, Any],
    eval_transcript: Optional[Dict[str, Any]] = None,
    eval_v3: Optional[Dict[str, Any]] = None,
    eval_reflection: Optional[Dict[str, Any]] = None,
    reflection_answers: Optional[Dict[str, Any]] = None,
    survey: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    weights = weights or DEFAULT_WEIGHTS
    eval_transcript = eval_transcript or {}
    eval_v3 = eval_v3 or {}
    eval_reflection = eval_reflection or {}
    reflection_answers = reflection_answers or {}
    survey = survey or {}

    timestamp = _pick_timestamp(eval_v3, eval_transcript)

    v2_items = extract_v2_items(eval_transcript)
    v2_to_v3, v3_critical = load_item_mappings()

    boosted_v3, boost_info = _apply_v2_boosts(eval_v3, v2_items, v2_to_v3)
    blocks = _build_blocks(boosted_v3, v2_items, v2_to_v3, v3_critical)

    checklist_score, checklist_max, checklist_pct = _score_checklist(boosted_v3, eval_transcript)
    dev_score, dev_max, dev_pct = _score_development(eval_reflection)
    global_score, global_max, global_pct, weights_used = _score_global(
        checklist_pct, dev_pct, weights
    )

    development_questions = build_development_questions(reflection_answers, eval_reflection)
    survey_out = _build_survey(survey)

    formula = (
        f"global = checklist% * {weights_used['checklist']} + "
        f"development% * {weights_used['development']}"
    )

    return {
        "schema_version": "evaluation.v1",
        "timestamp": timestamp,
        "case": {
            "id": case_data.get("id") or case_data.get("case_id") or "unknown",
            "name": case_data.get("titulo") or case_data.get("name") or "caso",
        },
        "scores": {
            "global": {
                "score": global_score,
                "max": global_max,
                "percentage": global_pct,
                "weights": weights_used,
                "formula": formula,
            },
            "checklist": {
                "score": checklist_score,
                "max": checklist_max,
                "percentage": checklist_pct,
                "source": "v3" if eval_v3 else "v2",
                "adjustments": boost_info,
            },
            "development": {
                "score": dev_score,
                "max": dev_max,
                "percentage": dev_pct,
                "source": "reflection_grader" if eval_reflection else "none",
                "formula": "0.4D + 0.2DD + 0.2P + 0.2Plan",
            },
        },
        "blocks": blocks,
        "development": {"questions": development_questions},
        "survey": survey_out,
        "debug": {
            "unmapped_v2_items": _unmapped_v2_items(v2_items, v2_to_v3),
            "boosted_item_ids": boost_info.get("boosted_item_ids", []),
        },
        "legacy": {
            "v2": eval_transcript,
            "v3": boosted_v3,
            "reflection": eval_reflection,
        },
    }


def _pick_timestamp(eval_v3: Dict[str, Any], eval_transcript: Dict[str, Any]) -> str:
    ts = eval_v3.get("timestamp") or eval_transcript.get("fecha_evaluacion")
    if ts:
        return str(ts)
    return datetime.now(timezone.utc).isoformat()


def _score_checklist(
    eval_v3: Dict[str, Any], eval_transcript: Dict[str, Any]
) -> Tuple[int, int, float]:
    if eval_v3:
        score = int(round(float(eval_v3.get("points_obtained") or 0)))
        max_score = int(round(float(eval_v3.get("max_points_case") or 0)))
        pct = float(eval_v3.get("percentage") or 0.0)
        return score, max_score, round(pct, 1)

    puntuacion = eval_transcript.get("puntuacion") or {}
    score = int(round(float(puntuacion.get("total_score") or 0)))
    max_score = int(round(float(puntuacion.get("max_score") or 0)))
    if max_score:
        pct = (score / max_score) * 100
    else:
        pct = float(puntuacion.get("porcentaje") or 0.0)
    return score, max_score, round(float(pct), 1)


def _score_development(eval_reflection: Dict[str, Any]) -> Tuple[int, int, float]:
    if not eval_reflection:
        return 0, 100, 0.0
    diag = float(eval_reflection.get("puntuacion_diagnostico") or 0)
    diff = float(eval_reflection.get("puntuacion_diferenciales") or 0)
    pruebas = float(eval_reflection.get("puntuacion_pruebas") or 0)
    plan = float(eval_reflection.get("puntuacion_plan") or 0)
    score = diag * 0.4 + diff * 0.2 + pruebas * 0.2 + plan * 0.2
    score = round(score, 1)
    return int(round(score)), 100, round(score, 1)


def _score_global(
    checklist_pct: float,
    dev_pct: float,
    weights: Dict[str, float],
) -> Tuple[int, int, float, Dict[str, float]]:
    if checklist_pct == 0 and dev_pct > 0:
        weights_used = {"checklist": 0.0, "development": 1.0}
    elif dev_pct == 0 and checklist_pct > 0:
        weights_used = {"checklist": 1.0, "development": 0.0}
    else:
        weights_used = weights
    pct = checklist_pct * weights_used["checklist"] + dev_pct * weights_used["development"]
    pct = round(pct, 1)
    return int(round(pct)), 100, pct, weights_used


def _apply_v2_boosts(
    eval_v3: Dict[str, Any],
    v2_items: List[Dict[str, Any]],
    v2_to_v3: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not eval_v3 or not v2_items:
        return eval_v3, {"items_added": 0, "points_added": 0, "boosted_item_ids": []}

    boosted = copy.deepcopy(eval_v3)
    done_ids = {item["id"] for item in v2_items if item.get("done") and item.get("id")}

    boost_targets = set()
    for v2_id in done_ids:
        for target in v2_to_v3.get(v2_id, []):
            boost_targets.add(target)

    if not boost_targets:
        return boosted, {"items_added": 0, "points_added": 0, "boosted_item_ids": []}

    points_added = 0
    items_added = 0
    boosted_ids: List[str] = []
    updated_items = []
    for item in boosted.get("items_evaluated", []) or []:
        if item.get("item_id") in boost_targets and not item.get("matched"):
            items_added += 1
            points_added += 1
            boosted_ids.append(str(item.get("item_id")))
            item = {
                **item,
                "matched": True,
                "points": 1,
                "method": "v2_signal",
                "match_details": "from_v2",
            }
        updated_items.append(item)
    boosted["items_evaluated"] = updated_items

    if points_added == 0:
        return boosted, {"items_added": 0, "points_added": 0, "boosted_item_ids": []}

    blocks = boosted.get("blocks") or {}
    for item in updated_items:
        if item.get("method") != "v2_signal":
            continue
        item_id = item.get("item_id") or ""
        prefix = str(item_id).split("_")[0]
        block_key = next((k for k in blocks.keys() if k.startswith(prefix + "_")), None)
        if not block_key:
            continue
        block = blocks.get(block_key) or {}
        block["points_obtained"] = int(block.get("points_obtained") or 0) + 1
        block["items_matched"] = int(block.get("items_matched") or 0) + 1
        max_points = float(block.get("max_points") or 0)
        if max_points:
            block["percentage"] = round((block["points_obtained"] / max_points) * 100, 1)
        blocks[block_key] = block
    boosted["blocks"] = blocks

    points_obtained = int(boosted.get("points_obtained") or 0) + points_added
    max_points = int(boosted.get("max_points_case") or 0)
    boosted["points_obtained"] = points_obtained
    boosted["percentage"] = round((points_obtained / max_points) * 100, 1) if max_points else 0
    boosted["passed"] = points_obtained >= int(boosted.get("min_points_case") or 0)

    summary = boosted.get("summary") or {}
    summary["total_items_matched"] = int(summary.get("total_items_matched") or 0) + items_added
    total_items = int(summary.get("total_items_evaluated") or 0)
    if total_items:
        summary["match_rate"] = round((summary["total_items_matched"] / total_items) * 100, 1)
    boosted["summary"] = summary

    return boosted, {
        "items_added": items_added,
        "points_added": points_added,
        "boosted_item_ids": boosted_ids,
    }


def _build_blocks(
    eval_v3: Dict[str, Any],
    v2_items: List[Dict[str, Any]],
    v2_to_v3: Dict[str, List[str]],
    v3_critical: Dict[str, bool],
) -> List[Dict[str, Any]]:
    if not eval_v3:
        return []

    loader = _safe_load_checklist()
    v3_items = index_v3_items(eval_v3)
    v2_by_id = {item.get("id"): item for item in v2_items if item.get("id")}
    v3_to_v2: Dict[str, List[str]] = {}
    for v2_id, v3_ids in v2_to_v3.items():
        for v3_id in v3_ids:
            v3_to_v2.setdefault(v3_id, []).append(v2_id)

    items_by_block: Dict[str, List[Dict[str, Any]]] = {}
    for item_id, item in v3_items.items():
        block_id = _resolve_block_id(item_id, loader, eval_v3.get("blocks") or {})
        if not block_id:
            continue
        item_entry = _build_item_entry(
            item_id, item, loader, v2_by_id, v3_to_v2, v3_critical
        )
        items_by_block.setdefault(block_id, []).append(item_entry)

    blocks_out: List[Dict[str, Any]] = []
    block_keys = _resolve_block_order(eval_v3.get("blocks") or {}, loader)
    for block_id in block_keys:
        block_stats = (eval_v3.get("blocks") or {}).get(block_id) or {}
        block_name = _resolve_block_name(block_id, loader)
        blocks_out.append(
            {
                "id": block_id,
                "name": block_name,
                "score": int(block_stats.get("points_obtained") or 0),
                "max": int(block_stats.get("max_points") or 0),
                "percentage": float(block_stats.get("percentage") or 0.0),
                "items": sorted(items_by_block.get(block_id, []), key=lambda x: x["id"]),
            }
        )
    return blocks_out


def _build_item_entry(
    item_id: str,
    item: Dict[str, Any],
    loader: Any,
    v2_by_id: Dict[str, Dict[str, Any]],
    v3_to_v2: Dict[str, List[str]],
    v3_critical: Dict[str, bool],
) -> Dict[str, Any]:
    meta = loader.items_by_id.get(item_id) if loader else {}
    label = item.get("label") or meta.get("label") or meta.get("texto") or meta.get("text") or item_id
    max_score = int(meta.get("points") or 1)
    score = int(item.get("points") or 0)
    matched = bool(item.get("matched"))
    evidence = []
    if matched:
        evidence.append(
            {
                "source": "v3",
                "source_item_id": item_id,
                "match_type": item.get("method") or "",
                "detail": item.get("match_details") or "",
            }
        )
        if score == 0:
            score = max_score

    critical = bool(meta.get("critical") or meta.get("critico")) or bool(v3_critical.get(item_id, False))
    for v2_id in v3_to_v2.get(item_id, []):
        v2_item = v2_by_id.get(v2_id)
        if not v2_item or not v2_item.get("done"):
            continue
        evidence.append(
            {
                "source": "v2",
                "source_item_id": v2_id,
                "match_type": v2_item.get("match_type") or "",
                "layer": v2_item.get("layer") or "",
            }
        )
        matched = True
        score = max_score
        if v2_item.get("critico"):
            critical = True

    return {
        "id": item_id,
        "text": label,
        "done": matched,
        "score": score,
        "max_score": max_score,
        "critical": critical,
        "evidence": evidence,
    }


def _unmapped_v2_items(
    v2_items: List[Dict[str, Any]], v2_to_v3: Dict[str, List[str]]
) -> List[str]:
    unmapped = []
    for item in v2_items:
        item_id = item.get("id")
        if not item_id or not item.get("done"):
            continue
        if item_id not in v2_to_v3:
            unmapped.append(str(item_id))
    return sorted(set(unmapped))


def _resolve_block_id(item_id: str, loader: Any, blocks: Dict[str, Any]) -> str:
    if loader and item_id in loader.items_by_id:
        return loader.items_by_id[item_id].get("block_id") or ""
    prefix = str(item_id).split("_")[0]
    return next((key for key in blocks.keys() if key.startswith(prefix + "_")), "")


def _resolve_block_name(block_id: str, loader: Any) -> str:
    if loader and block_id in loader.blocks_by_id:
        return loader.blocks_by_id[block_id].get("name") or block_id
    return block_id


def _resolve_block_order(blocks: Dict[str, Any], loader: Any) -> List[str]:
    if loader:
        ordered = [b["block_id"] for b in loader.blocks if b.get("block_id") in blocks]
        if ordered:
            return ordered
    return sorted(blocks.keys())


def _safe_load_checklist() -> Any:
    if not load_checklist_v2:
        return None
    try:
        return load_checklist_v2()
    except Exception:
        return None


def _build_survey(survey: Dict[str, Any]) -> Dict[str, Any]:
    if not survey:
        return {"average": 0.0, "likert": [], "open": []}
    average = float(survey.get("media_satisfaccion") or survey.get("average") or 0.0)
    likert = survey.get("likert") or survey.get("likert_responses") or []
    open_items = survey.get("abiertas") or survey.get("open") or []
    return {"average": round(average, 2), "likert": likert, "open": open_items}
