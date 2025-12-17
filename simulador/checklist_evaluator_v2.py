import functools
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple


SpeakerRequirement = Literal["student", "patient", "any"]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    text = text.lower()
    text = _strip_accents(text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text, flags=re.UNICODE).strip()
    return text


def extract_student_lines(transcript: str) -> List[str]:
    lines: List[str] = []
    for raw_line in transcript.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Accept both "[ESTUDIANTE] ..." and "[ESTUDIANTE]: ..."
        if line.startswith("[ESTUDIANTE]"):
            content = line[len("[ESTUDIANTE]") :].lstrip()
            if content.startswith(":"):
                content = content[1:].lstrip()
            lines.append(content)
            continue
        if line.startswith("[STUDENT]"):
            content = line[len("[STUDENT]") :].lstrip()
            if content.startswith(":"):
                content = content[1:].lstrip()
            lines.append(content)
            continue
        if line.startswith("[ESTUDIANTE]:"):
            lines.append(line[len("[ESTUDIANTE]:") :].lstrip())
            continue
        if line.startswith("[STUDENT]:"):
            lines.append(line[len("[STUDENT]:") :].lstrip())
            continue

    # Fallback: if no tags exist, treat whole transcript as student text (MVP)
    if not lines and transcript.strip():
        lines = [transcript.strip()]

    return lines


def preprocess_transcript(transcript: str) -> Dict[str, Any]:
    student_lines = extract_student_lines(transcript)
    normalized_lines = [normalize_text(l) for l in student_lines]
    combined_normalized = " ".join([l for l in normalized_lines if l])
    return {
        "student_lines": student_lines,
        "student_lines_normalized": normalized_lines,
        "student_text_normalized": combined_normalized,
    }


def _kw_to_regex(kw_normalized: str) -> re.Pattern:
    kw_normalized = kw_normalized.strip()
    if not kw_normalized:
        return re.compile(r"(?!x)x")

    # Boundaries around first and last "word" are usually enough for phrases.
    return re.compile(rf"(?:^|\b){re.escape(kw_normalized)}(?:\b|$)")


@dataclass(frozen=True)
class DetectedItem:
    item_id: str
    match_type: Literal["keyword", "pattern"]
    snippet: str
    peso_item: float
    bloque_id: str
    subbloque_id: Optional[str]


def _iter_items(master: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for bloque in master.get("bloques", []):
        if "items" in bloque and isinstance(bloque["items"], list):
            for item in bloque["items"]:
                yield item
        if "subbloques" in bloque and isinstance(bloque["subbloques"], list):
            for sub in bloque["subbloques"]:
                for item in sub.get("items", []):
                    yield item


def _iter_block_items(bloque: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for item in bloque.get("items", []) or []:
        yield item
    for sub in bloque.get("subbloques", []) or []:
        for item in sub.get("items", []) or []:
            yield item


def _get_profile(case_data: Dict[str, Any], profiles: Dict[str, Any]) -> Dict[str, Any]:
    perfil_id = (
        case_data.get("perfil")
        or case_data.get("profile")
        or case_data.get("perfil_id")
        or "default"
    )
    perfil_id = str(perfil_id).strip().lower()

    default = profiles.get("default", {"peso_mult": 1.0, "min_items": 0})
    if perfil_id == "default":
        return {"id": "default", "overrides": {}, "bloques_criticos": [], "default": default}

    for perfil in profiles.get("perfiles", []):
        if str(perfil.get("id", "")).strip().lower() == perfil_id:
            return {**perfil, "default": default}

    return {"id": perfil_id, "overrides": {}, "bloques_criticos": [], "default": default}


def _get_override(profile: Dict[str, Any], bloque_id: str) -> Dict[str, Any]:
    overrides = profile.get("overrides", {}) or {}
    return overrides.get(bloque_id, {}) or {}


def _get_suboverride(profile: Dict[str, Any], bloque_id: str, subbloque_id: str) -> Dict[str, Any]:
    override = _get_override(profile, bloque_id)
    subbloques = override.get("subbloques", {}) or {}
    return subbloques.get(subbloque_id, {}) or {}


def _peso_mult_for_item(profile: Dict[str, Any], bloque_id: str, subbloque_id: Optional[str]) -> float:
    default_mult = float(profile.get("default", {}).get("peso_mult", 1.0))
    override = _get_override(profile, bloque_id)
    mult = float(override.get("peso_mult", default_mult))
    if subbloque_id:
        suboverride = _get_suboverride(profile, bloque_id, subbloque_id)
        mult = float(suboverride.get("peso_mult", mult))
    return mult


def _min_items_for(profile: Dict[str, Any], bloque_id: str, subbloque_id: Optional[str]) -> int:
    default_min = int(profile.get("default", {}).get("min_items", 0))
    override = _get_override(profile, bloque_id)
    min_items = int(override.get("min_items", default_min))
    if subbloque_id:
        suboverride = _get_suboverride(profile, bloque_id, subbloque_id)
        min_items = int(suboverride.get("min_items", min_items))
    return min_items


@functools.lru_cache(maxsize=1)
def load_master_checklist_cached(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_case_profiles_cached(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_items(preprocessed: Dict[str, Any], master: Dict[str, Any]) -> List[DetectedItem]:
    transcript_norm: str = preprocessed["student_text_normalized"]
    detected_by_id: Dict[str, DetectedItem] = {}

    for item in _iter_items(master):
        item_id = str(item.get("id", "")).strip()
        if not item_id or item_id in detected_by_id:
            continue

        requires_speaker: SpeakerRequirement = item.get("requires_speaker", "student")
        if requires_speaker not in ("student", "any"):
            continue

        bloque_id = str(item.get("bloque_id") or "").strip()
        subbloque_id = item.get("subbloque_id")
        if subbloque_id is not None:
            subbloque_id = str(subbloque_id).strip() or None

        peso_item = float(item.get("peso", 1.0))

        negatives = [normalize_text(str(n)) for n in (item.get("negatives") or [])]
        if any(neg and neg in transcript_norm for neg in negatives):
            continue

        patterns = item.get("patterns") or []
        for p in patterns:
            p_norm = str(p)
            if not p_norm:
                continue
            m = re.search(p_norm, transcript_norm)
            if m:
                detected_by_id[item_id] = DetectedItem(
                    item_id=item_id,
                    match_type="pattern",
                    snippet=m.group(0),
                    peso_item=peso_item,
                    bloque_id=bloque_id,
                    subbloque_id=subbloque_id,
                )
                break

        if item_id in detected_by_id:
            continue

        keywords = item.get("keywords") or []
        for kw in keywords:
            kw_norm = normalize_text(str(kw))
            if not kw_norm:
                continue
            if _kw_to_regex(kw_norm).search(transcript_norm):
                detected_by_id[item_id] = DetectedItem(
                    item_id=item_id,
                    match_type="keyword",
                    snippet=kw_norm,
                    peso_item=peso_item,
                    bloque_id=bloque_id,
                    subbloque_id=subbloque_id,
                )
                break

    return list(detected_by_id.values())


def evaluate_checklist_v2(
    transcript: str,
    case_data: Dict[str, Any],
    master_checklist_path: str,
    case_profiles_path: str,
) -> Dict[str, Any]:
    master = load_master_checklist_cached(master_checklist_path)
    profiles = load_case_profiles_cached(case_profiles_path)
    profile = _get_profile(case_data, profiles)

    pre = preprocess_transcript(transcript or "")
    detected = detect_items(pre, master)

    detected_ids = {d.item_id for d in detected}

    scored_items: List[Dict[str, Any]] = []
    for d in detected:
        mult = _peso_mult_for_item(profile, d.bloque_id, d.subbloque_id)
        puntos = d.peso_item * mult
        scored_items.append(
            {
                "item_id": d.item_id,
                "bloque_id": d.bloque_id,
                "subbloque_id": d.subbloque_id,
                "match_type": d.match_type,
                "snippet": d.snippet,
                "peso": d.peso_item,
                "peso_mult": mult,
                "puntos": puntos,
            }
        )

    # Precompute maximum points by profile (theoretical).
    puntos_maximos = 0.0
    for item in _iter_items(master):
        bloque_id = str(item.get("bloque_id") or "").strip()
        subbloque_id = item.get("subbloque_id")
        if subbloque_id is not None:
            subbloque_id = str(subbloque_id).strip() or None
        peso_item = float(item.get("peso", 1.0))
        mult = _peso_mult_for_item(profile, bloque_id, subbloque_id)
        puntos_maximos += peso_item * mult

    puntuacion_total = sum(i["puntos"] for i in scored_items)
    puntos_maximos = float(master.get("puntos_maximos", puntos_maximos))
    porcentaje = (puntuacion_total / puntos_maximos * 100.0) if puntos_maximos > 0 else 0.0

    # Build per-block summaries.
    bloques_out: Dict[str, Any] = {}
    for bloque in master.get("bloques", []):
        bloque_id = str(bloque.get("id") or "").strip()
        if not bloque_id:
            continue

        items_all = list(_iter_block_items(bloque))
        items_ids = [str(i.get("id") or "") for i in items_all if str(i.get("id") or "")]
        items_missing = [iid for iid in items_ids if iid not in detected_ids]
        items_detected = [iid for iid in items_ids if iid in detected_ids]

        puntos_bloque = sum(
            i["puntos"] for i in scored_items if i["bloque_id"] == bloque_id and i.get("subbloque_id") is None
        )
        puntos_max_bloque = 0.0
        for item in items_all:
            iid = str(item.get("id") or "").strip()
            if not iid:
                continue
            subbloque_id = item.get("subbloque_id")
            if subbloque_id is not None:
                subbloque_id = str(subbloque_id).strip() or None
            peso_item = float(item.get("peso", 1.0))
            mult = _peso_mult_for_item(profile, bloque_id, subbloque_id)
            puntos_max_bloque += peso_item * mult

        # Block-level min is evaluated over all items in the block, unless overridden.
        min_requerido = _min_items_for(profile, bloque_id, None)
        cumple_minimos = len(items_detected) >= min_requerido

        bloque_out: Dict[str, Any] = {
            "nombre": bloque.get("nombre", bloque_id),
            "items_detectados": items_detected,
            "items_faltantes": items_missing,
            "puntos": round(puntos_bloque, 2),
            "puntos_max": round(puntos_max_bloque, 2),
            "min_requerido": min_requerido,
            "cumple_minimos": bool(cumple_minimos),
        }

        # Subblocks (e.g. "7-aparatos")
        if bloque.get("subbloques"):
            sub_out: Dict[str, Any] = {}
            for sub in bloque.get("subbloques", []) or []:
                sub_id = str(sub.get("id") or "").strip()
                if not sub_id:
                    continue
                sub_items = sub.get("items", []) or []
                sub_item_ids = [str(i.get("id") or "") for i in sub_items if str(i.get("id") or "")]
                sub_detected = [iid for iid in sub_item_ids if iid in detected_ids]
                sub_missing = [iid for iid in sub_item_ids if iid not in detected_ids]

                sub_points = sum(
                    i["puntos"] for i in scored_items if i["bloque_id"] == bloque_id and i.get("subbloque_id") == sub_id
                )
                sub_max = 0.0
                for item in sub_items:
                    peso_item = float(item.get("peso", 1.0))
                    mult = _peso_mult_for_item(profile, bloque_id, sub_id)
                    sub_max += peso_item * mult

                sub_min = _min_items_for(profile, bloque_id, sub_id)
                sub_ok = len(sub_detected) >= sub_min

                sub_out[sub_id] = {
                    "nombre": sub.get("nombre", sub_id),
                    "items_detectados": sub_detected,
                    "items_faltantes": sub_missing,
                    "puntos": round(sub_points, 2),
                    "puntos_max": round(sub_max, 2),
                    "min_requerido": sub_min,
                    "cumple_minimos": bool(sub_ok),
                }

            bloque_out["subbloques"] = sub_out

            # For blocks with subblocks, include *all* points at block level (including subblocks).
            bloque_out["puntos"] = round(
                sum(i["puntos"] for i in scored_items if i["bloque_id"] == bloque_id), 2
            )

        bloques_out[bloque_id] = bloque_out

    # Critical failures support both bloque ids and subbloque ids.
    criticos = set(profile.get("bloques_criticos", []) or [])
    bloques_criticos_fallados: List[str] = []
    for bid in criticos:
        bid = str(bid).strip()
        if not bid:
            continue
        if bid in bloques_out and not bloques_out[bid].get("cumple_minimos", True):
            bloques_criticos_fallados.append(bid)
            continue
        # search in subblocks
        for bloque_id, binfo in bloques_out.items():
            sub = (binfo.get("subbloques") or {}).get(bid)
            if sub and not sub.get("cumple_minimos", True):
                bloques_criticos_fallados.append(bid)
                break

    return {
        "case_id": case_data.get("id") or case_data.get("case_id") or "unknown",
        "perfil": profile.get("id", case_data.get("perfil")),
        "puntuacion_total": round(float(puntuacion_total), 2),
        "puntos_maximos": round(float(puntos_maximos), 2),
        "porcentaje": round(float(porcentaje), 1),
        "aprobado": bool(float(puntuacion_total) >= 70.0),
        "bloques": bloques_out,
        "bloques_criticos_fallados": bloques_criticos_fallados,
        "items_detectados": scored_items,
        "meta": {
            "solo_estudiante": True,
            "student_lines": len(pre["student_lines"]),
        },
    }

