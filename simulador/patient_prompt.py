from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_genero(caso: Dict[str, Any]) -> str:
    info = caso.get("informacion_paciente") or {}
    genero_raw = info.get("genero") or caso.get("gender") or caso.get("genero") or ""
    genero = _as_str(genero_raw).lower()

    if genero in {"female", "f", "mujer", "hembra", "femenino"}:
        return "mujer"
    if genero in {"male", "m", "hombre", "masculino"}:
        return "hombre"
    if "mujer" in genero or "femenin" in genero:
        return "mujer"
    if "hombre" in genero or "masculin" in genero:
        return "hombre"
    return "persona"


def _extract_respuestas(item: Any) -> Tuple[Optional[bool], str, str, List[str]]:
    """
    Normaliza un item de `datos_paciente` a:
    - tiene (bool|None)
    - respuesta_corta (str)
    - respuesta_detalle (str)
    - lista (List[str])

    Soporta:
    - str: se interpreta como respuesta_corta
    - dict: keys típicas: tiene, respuesta, respuesta_corta, respuesta_detalle, lista
    """
    if isinstance(item, str):
        text = _as_str(item)
        return None, text, "", []

    if not isinstance(item, dict):
        text = _as_str(item)
        return None, text, "", []

    tiene = item.get("tiene")
    if isinstance(tiene, bool):
        tiene_bool: Optional[bool] = tiene
    else:
        tiene_bool = None

    respuesta = _as_str(item.get("respuesta"))
    respuesta_corta = _as_str(item.get("respuesta_corta")) or respuesta
    respuesta_detalle = _as_str(item.get("respuesta_detalle")) or (
        "" if respuesta_corta == respuesta else respuesta
    )

    lista_raw = item.get("lista")
    lista: List[str] = []
    if isinstance(lista_raw, list):
        for entry in lista_raw:
            text = _as_str(entry)
            if text:
                lista.append(text)

    return tiene_bool, respuesta_corta, respuesta_detalle, lista


# ========== NUEVO ESQUEMA (hechos estructurados) ==========

JsonPath = Tuple[str, ...]


def _repo_root() -> Path:
    # simulador/patient_prompt.py -> simulador -> TO_GITHUB
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _load_master_items() -> Dict[str, Dict[str, Any]]:
    """
    Carga `data/master_items.json` como fuente de verdad del checklist maestro (130 ítems).
    Devuelve dict: item_id -> metadata (texto, bloque/sistema).
    """
    path = _repo_root() / "data" / "master_items.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    items: Dict[str, Dict[str, Any]] = {}

    bloques_universales = data.get("bloques_universales") or {}
    if isinstance(bloques_universales, dict):
        for bloque_name, bloque in bloques_universales.items():
            for it in (bloque.get("items") or []):
                item_id = _as_str(it.get("id"))
                if not item_id:
                    continue
                items[item_id] = {
                    "id": item_id,
                    "texto": it.get("texto"),
                    "bloque": bloque_name,
                    "sistema": None,
                    "tipo_bloque": "universal",
                }

    items_por_sistemas = data.get("items_por_sistemas") or {}
    if isinstance(items_por_sistemas, dict):
        for sistema_name, sistema in items_por_sistemas.items():
            for it in (sistema.get("items") or []):
                item_id = _as_str(it.get("id"))
                if not item_id:
                    continue
                items[item_id] = {
                    "id": item_id,
                    "texto": it.get("texto"),
                    "bloque": None,
                    "sistema": sistema_name,
                    "tipo_bloque": "sistema",
                }

    return items


def _walk_template_for_ids(node: Any, path: JsonPath, out: Dict[str, Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        node_id = node.get("_id")
        if isinstance(node_id, str) and node_id.strip():
            out[node_id.strip()] = {
                "id": node_id.strip(),
                "path": path,
                "kind": node.get("_kind") or "patient_fact",
                "label": node.get("_label"),
            }

        for key, value in node.items():
            if key.startswith("_"):
                continue
            _walk_template_for_ids(value, path + (str(key),), out)
    elif isinstance(node, list):
        # No recorremos listas porque en el template los nodos con `_id` deben ser dicts
        return


@lru_cache(maxsize=1)
def _load_template_mapping() -> Dict[str, Dict[str, Any]]:
    """
    Extrae el mapping ID -> path desde `casos_procesados/_TEMPLATE_CASO.json`.
    Preferencia:
    1) Sección explícita `_mapping_checklist` (recomendado).
    2) Nodos mapeables con `_id` (fallback).
    """
    path = _repo_root() / "casos_procesados" / "_TEMPLATE_CASO.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    mapping: Dict[str, Dict[str, Any]] = {}

    explicit = data.get("_mapping_checklist")
    if isinstance(explicit, dict):
        for item_id, entry in explicit.items():
            item_id = _as_str(item_id)
            if not item_id:
                continue
            if not isinstance(entry, dict):
                continue
            raw_path = _as_str(entry.get("path"))
            if not raw_path:
                continue
            # Permitimos paths relativos a `datos_paciente` (ej: "hechos.ros.respiratorio.tos")
            parts = tuple([p for p in raw_path.split(".") if p])
            mapping[item_id] = {
                "id": item_id,
                "path": parts,
                "kind": entry.get("kind") or "patient_fact",
                "label": entry.get("label"),
            }

        if mapping:
            return mapping

    # Fallback: recorrer el template buscando `_id` dentro de `datos_paciente`
    datos_paciente = data.get("datos_paciente") or {}
    _walk_template_for_ids(datos_paciente, tuple(), mapping)

    if mapping:
        return mapping

    # Último fallback: mapping por convención basado en IDs del checklist maestro.
    # Mantiene el sistema funcionando incluso si el template no incluye `_mapping_checklist`/`_id`.
    return _build_default_mapping_from_master()


def _build_default_mapping_from_master() -> Dict[str, Dict[str, Any]]:
    master = _load_master_items()
    mapping: Dict[str, Dict[str, Any]] = {}
    for item_id in master.keys():
        entry = _default_mapping_for_item_id(item_id)
        mapping[item_id] = entry
    return mapping


def _default_mapping_for_item_id(item_id: str) -> Dict[str, Any]:
    """
    Convención de paths relativa a `datos_paciente`.
    Diseñada para el esquema:
      datos_paciente.frases, datos_paciente.personalidad, datos_paciente.hechos.*
    """
    item_id = _as_str(item_id)

    # IDENTIFICACION (acciones del estudiante)
    if item_id in {"ID_01", "ID_02", "ID_03"}:
        return {"id": item_id, "path": tuple(), "kind": "student_action"}

    # MOTIVO_CONSULTA: solo algunas se asocian a frases/hechos
    if item_id in {"MC_01", "MC_05"}:
        return {"id": item_id, "path": tuple(), "kind": "student_action"}
    if item_id in {"MC_02"}:
        return {"id": item_id, "path": ("frases", "motivo_consulta"), "kind": "patient_fact"}
    if item_id in {"MC_03"}:
        return {"id": item_id, "path": ("frases", "relato_libre"), "kind": "patient_fact"}
    if item_id in {"MC_04"}:
        return {"id": item_id, "path": ("hechos", "motivo", "otros_motivos"), "kind": "patient_fact"}

    # HEA_SOCRATES
    socrates_map = {
        "SOCR_01": ("hechos", "hea", "localizacion"),
        "SOCR_02": ("hechos", "hea", "inicio"),
        "SOCR_03": ("hechos", "hea", "caracteristicas"),
        "SOCR_04": ("hechos", "hea", "irradiacion"),
        "SOCR_05": ("hechos", "hea", "intensidad_0_10"),
        "SOCR_06": ("hechos", "hea", "agravantes"),
        "SOCR_07": ("hechos", "hea", "atenuantes"),
        "SOCR_08": ("hechos", "hea", "evolucion"),
        "SOCR_09": ("hechos", "hea", "duracion_episodios"),
        "SOCR_10": ("hechos", "hea", "asociados"),
        "SOCR_11": ("hechos", "hea", "frecuencia"),
    }
    if item_id in socrates_map:
        return {"id": item_id, "path": socrates_map[item_id], "kind": "patient_fact"}

    # ICE
    ice_map = {
        "ICE_01": ("frases", "ice", "ideas"),
        "ICE_02": ("frases", "ice", "concerns"),
        "ICE_03": ("frases", "ice", "expectations"),
    }
    if item_id in ice_map:
        return {"id": item_id, "path": ice_map[item_id], "kind": "patient_fact"}

    # ANTECEDENTES PERSONALES
    ap_map = {
        "AP_01": ("hechos", "antecedentes", "cronicas"),
        "AP_02": ("hechos", "antecedentes", "cirugias"),
        "AP_03": ("hechos", "antecedentes", "hospitalizaciones"),
        "AP_04": ("hechos", "alergias", "medicamentos"),
        "AP_05": ("hechos", "alergias", "no_medicamentos"),
        "AP_06": ("hechos", "antecedentes", "transfusiones"),
        "AP_07": ("hechos", "antecedentes", "vacunas"),
        "AP_08": ("hechos", "antecedentes", "gineco_obstetrica"),
        "AP_09": ("hechos", "antecedentes", "traumatismos"),
        "AP_10": ("hechos", "antecedentes", "discapacidad_protesis"),
        "AP_11": ("hechos", "medicacion_actual"),
        "AP_12": ("hechos", "antecedentes", "psiquiatria"),
    }
    if item_id in ap_map:
        return {"id": item_id, "path": ap_map[item_id], "kind": "patient_fact"}

    # ANTECEDENTES FAMILIARES
    af_map = {
        "AF_01": ("hechos", "familiares", "patologias_primer_grado"),
        "AF_02": ("hechos", "familiares", "causas_fallecimiento"),
        "AF_03": ("hechos", "familiares", "eventos_cv_precoces"),
        "AF_04": ("hechos", "familiares", "cancer_hereditario"),
    }
    if item_id in af_map:
        return {"id": item_id, "path": af_map[item_id], "kind": "patient_fact"}

    # PSICOSOCIALES
    ps_map = {
        "PS_01": ("hechos", "psicosocial", "convivencia"),
        "PS_02": ("hechos", "psicosocial", "estado_civil_soporte"),
        "PS_03": ("hechos", "psicosocial", "vivienda"),
        "PS_04": ("hechos", "psicosocial", "laboral"),
        "PS_05": ("hechos", "psicosocial", "educacion"),
        "PS_06": ("hechos", "psicosocial", "creencias"),
        "PS_07": ("hechos", "psicosocial", "estres"),
        "PS_08": ("hechos", "psicosocial", "cuidador"),
        "PS_09": ("hechos", "psicosocial", "violencia_abuso"),
    }
    if item_id in ps_map:
        return {"id": item_id, "path": ps_map[item_id], "kind": "patient_fact"}

    # HABITOS
    hab_map = {
        "HAB_01": ("hechos", "habitos", "tabaco"),
        "HAB_02": ("hechos", "habitos", "alcohol"),
        "HAB_03": ("hechos", "habitos", "drogas"),
        "HAB_04": ("hechos", "habitos", "dieta"),
        "HAB_05": ("hechos", "habitos", "actividad_fisica"),
        "HAB_06": ("hechos", "habitos", "sueno"),
        "HAB_07": ("hechos", "habitos", "sexualidad"),
        "HAB_08": ("hechos", "habitos", "animales_exposiciones"),
    }
    if item_id in hab_map:
        return {"id": item_id, "path": hab_map[item_id], "kind": "patient_fact"}

    # GENERALES
    gen_map = {
        "GEN_01": ("hechos", "generales", "fiebre"),
        "GEN_02": ("hechos", "generales", "perdida_peso"),
        "GEN_03": ("hechos", "generales", "sudoracion_nocturna"),
        "GEN_04": ("hechos", "generales", "astenia"),
        "GEN_05": ("hechos", "generales", "anorexia"),
    }
    if item_id in gen_map:
        return {"id": item_id, "path": gen_map[item_id], "kind": "patient_fact"}

    # SISTEMAS (ROS)
    if item_id.startswith("RESP_"):
        resp_map = {
            "RESP_01": "tos",
            "RESP_02": "caracteristicas_tos",
            "RESP_03": "disnea",
            "RESP_04": "ortopnea",
            "RESP_05": "disnea_paroxistica_nocturna",
            "RESP_06": "dolor_pleuritico",
            "RESP_07": "hemoptisis",
            "RESP_08": "sibilancias",
            "RESP_09": "exposicion_laboral",
            "RESP_10": "tuberculosis",
        }
        leaf = resp_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "respiratorio", leaf), "kind": "patient_fact"}

    if item_id.startswith("CARDIO_"):
        if item_id == "CARDIO_02":
            return {"id": item_id, "path": tuple(), "kind": "student_action"}
        cardio_map = {
            "CARDIO_01": "dolor_toracico",
            "CARDIO_03": "relacion_esfuerzo",
            "CARDIO_04": "sintomas_vegetativos",
            "CARDIO_05": "palpitaciones",
            "CARDIO_06": "sincope",
            "CARDIO_07": "edemas",
            "CARDIO_08": "claudicacion",
        }
        leaf = cardio_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "cardiovascular", leaf), "kind": "patient_fact"}

    if item_id.startswith("DIGEST_"):
        digest_map = {
            "DIGEST_01": "dolor_abdominal",
            "DIGEST_02": "nauseas_vomitos",
            "DIGEST_03": "ritmo_intestinal",
            "DIGEST_04": "sangrado_digestivo",
            "DIGEST_05": "disfagia",
            "DIGEST_06": "pirosis_reflujo",
            "DIGEST_07": "distension_abdominal",
            "DIGEST_08": "ictericia",
        }
        leaf = digest_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "digestivo", leaf), "kind": "patient_fact"}

    if item_id.startswith("GU_"):
        gu_map = {
            "GU_01": "disuria",
            "GU_02": "polaquiuria_nicturia",
            "GU_03": "hematuria",
            "GU_04": "incontinencia",
            "GU_05": "urgencia",
            "GU_06": "dolor_flancos",
            "GU_07": "secrecion_genital",
            "GU_08": "sintomas_prostaticos",
        }
        leaf = gu_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "genitourinario", leaf), "kind": "patient_fact"}

    if item_id.startswith("NEURO_"):
        neuro_map = {
            "NEURO_01": "cefalea",
            "NEURO_02": "patron_cefalea",
            "NEURO_03": "focalidad",
            "NEURO_04": "mareo_vertigo",
            "NEURO_05": "conciencia",
            "NEURO_06": "meningeos",
            "NEURO_07": "lenguaje",
            "NEURO_08": "convulsiones",
            "NEURO_09": "memoria",
            "NEURO_10": "vision",
        }
        leaf = neuro_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "neurologico", leaf), "kind": "patient_fact"}

    if item_id.startswith("OSTEO_"):
        osteo_map = {
            "OSTEO_01": "dolor_articular",
            "OSTEO_02": "rigidez_matutina",
            "OSTEO_03": "tumefaccion",
            "OSTEO_04": "debilidad_muscular",
            "OSTEO_05": "limitacion_movilidad",
            "OSTEO_06": "traumatismos",
        }
        leaf = osteo_map.get(item_id)
        if leaf:
            return {"id": item_id, "path": ("hechos", "ros", "osteomuscular", leaf), "kind": "patient_fact"}

    return {"id": item_id, "path": tuple(), "kind": "unknown_mapping"}


def _get_by_path(root: Any, path: JsonPath) -> Any:
    cur = root
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _normalize_fact_value(value: Any) -> Tuple[Optional[bool], Dict[str, Any]]:
    """
    Interpreta valores del esquema simple:
    - bool -> present
    - list -> present=True, values={"lista":[...]}
    - str/num -> present=True, values={"valor":...}
    - dict:
        - si tiene `tiene`: usa eso
        - si tiene `lista`: lista adicional
        - el resto de keys se pasan como values (sin `_id/_kind/_label`)
    - None -> present=None
    """
    if value is None:
        return None, {}

    if isinstance(value, bool):
        return value, {}

    if isinstance(value, list):
        cleaned = [v for v in (_as_str(x) for x in value) if v]
        # Lista vacía: interpretamos "no hay" (p.ej. no cirugías, no medicación).
        return (True, {"lista": cleaned}) if cleaned else (False, {})

    if isinstance(value, (int, float, str)):
        text = _as_str(value)
        # String vacío equivale a "no especificado" -> desconocido.
        return (True, {"valor": text}) if text else (None, {})

    if isinstance(value, dict):
        # Permitir que el author use dict con `_id` en el caso (opcional)
        tiene = value.get("tiene")
        present: Optional[bool]
        if isinstance(tiene, bool):
            present = tiene
        elif tiene is None and "tiene" in value:
            present = None
        else:
            present = None

        values: Dict[str, Any] = {}
        for k, v in value.items():
            if str(k).startswith("_") or k == "tiene":
                continue
            if k == "lista" and isinstance(v, list):
                cleaned = [x for x in (_as_str(y) for y in v) if x]
                if cleaned:
                    values["lista"] = cleaned
                continue
            values[k] = v

        # Si no hay `tiene`, inferir presencia si hay valores “reales”
        if present is None and "tiene" not in value:
            if values:
                present = True

        return present, values

    return None, {}


def _is_simple_schema(caso: Dict[str, Any]) -> bool:
    dp = caso.get("datos_paciente")
    if not isinstance(dp, dict):
        return False
    return isinstance(dp.get("hechos"), dict) and isinstance(dp.get("frases"), dict)


def parse_simple_hechos(caso: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Lee `datos_paciente.hechos` y `datos_paciente.checklist_overrides` y devuelve:

    facts = {
      "RESP_01": {"present": True, "values": {...}, "path": ("hechos","ros","respiratorio","tos")},
      ...
    }

    La lista de ítems viene de `data/master_items.json` y los paths del template
    `casos_procesados/_TEMPLATE_CASO.json` (campo `_id`).
    """
    master = _load_master_items()
    mapping = _load_template_mapping()

    dp = caso.get("datos_paciente") or {}
    hechos = dp.get("hechos") if isinstance(dp, dict) else {}
    frases = dp.get("frases") if isinstance(dp, dict) else {}

    overrides = dp.get("checklist_overrides") if isinstance(dp, dict) else {}
    overrides = overrides if isinstance(overrides, dict) else {}

    # Normalizar overrides: puede venir por ID (RESP_01) o por clave (tos)
    normalized_overrides_by_id: Dict[str, Any] = {}
    normalized_overrides_by_key: Dict[str, Any] = {}
    for k, v in overrides.items():
        key = _as_str(k)
        if not key:
            continue
        if key in master:
            normalized_overrides_by_id[key] = v
        else:
            normalized_overrides_by_key[key] = v

    facts: Dict[str, Dict[str, Any]] = {}
    for item_id in master.keys():
        map_entry = mapping.get(item_id)
        if not map_entry:
            facts[item_id] = {"present": None, "values": {}, "path": None, "kind": "unknown_mapping"}
            continue

        path: JsonPath = tuple(map_entry.get("path") or ())
        kind = map_entry.get("kind") or "patient_fact"

        # Student actions: no tienen hecho clínico asociado.
        if kind == "student_action":
            facts[item_id] = {"present": None, "values": {}, "path": path, "kind": "student_action"}
            continue

        # Resolver root: la mayoría cuelga de hechos; algunos (ICE, motivo) cuelgan de frases/personalidad.
        root: Any = dp
        raw_value = _get_by_path(root, path)

        # Compatibilidad: permitir que el author rellene valores directamente en `hechos` con la misma ruta
        # que en template (sin envolver en dict con `_id`).
        if raw_value is None and path and path[0] == "hechos" and isinstance(hechos, dict):
            raw_value = _get_by_path({"hechos": hechos}, path)

        # Si el campo template era dict con `_id` y el author puso lista/bool directamente, raw_value será ese valor.
        present, values = _normalize_fact_value(raw_value)

        # Override por ID
        if item_id in normalized_overrides_by_id:
            present, values = _normalize_fact_value(normalized_overrides_by_id[item_id])
        else:
            # Override por clave (último segmento del path)
            leaf = path[-1] if path else ""
            if leaf and leaf in normalized_overrides_by_key:
                present, values = _normalize_fact_value(normalized_overrides_by_key[leaf])

        facts[item_id] = {"present": present, "values": values, "path": path, "kind": kind}

    return facts


def _format_fact_line(label: str, present: Optional[bool], values: Dict[str, Any]) -> Optional[str]:
    if present is None:
        return None

    if present is False:
        return f"- {label}: NO"

    # present True
    extras: List[str] = []
    lista = values.get("lista")
    if isinstance(lista, list) and lista:
        extras.append("; ".join([_as_str(x) for x in lista if _as_str(x)]))

    valor = values.get("valor")
    if valor is not None and _as_str(valor):
        extras.append(_as_str(valor))

    # Otras claves (nota, cantidad, duración, severidad...)
    for k, v in values.items():
        if k in {"lista", "valor"}:
            continue
        text = _as_str(v)
        if not text:
            continue
        extras.append(f"{k}={text}")

    if extras:
        return f"- {label}: SÍ ({', '.join(extras)})"
    return f"- {label}: SÍ"


def _render_item(label: str, item: Any) -> str:
    tiene, corta, detalle, lista = _extract_respuestas(item)
    lines: List[str] = [f"- {label}:"]

    if corta:
        lines.append(f"  - Respuesta corta: \"{corta}\"")
    elif tiene is False:
        lines.append("  - Respuesta corta: \"No.\"")
    else:
        lines.append("  - Respuesta corta: \"No lo sé / no me he fijado.\"")

    if detalle:
        lines.append(f"  - Si insisten: \"{detalle}\"")

    if lista:
        lines.append("  - Lista (si te piden concretar):")
        for entry in lista:
            lines.append(f"    - {entry}")

    return "\n".join(lines)


def _render_habitos(habitos: Any) -> str:
    if not isinstance(habitos, dict):
        return _render_item("Hábitos tóxicos", habitos)

    parts: List[str] = ["- Hábitos tóxicos:"]
    for key, label in (
        ("tabaco", "Tabaco"),
        ("alcohol", "Alcohol"),
        ("drogas", "Drogas"),
    ):
        if key not in habitos:
            continue
        tiene, corta, detalle, _ = _extract_respuestas(habitos.get(key))

        if isinstance(habitos.get(key), dict):
            extra_bits: List[str] = []
            cantidad = _as_str(habitos[key].get("cantidad"))
            duracion = _as_str(habitos[key].get("duracion"))
            if cantidad:
                extra_bits.append(f"cantidad={cantidad}")
            if duracion:
                extra_bits.append(f"duración={duracion}")
            extra = f" ({', '.join(extra_bits)})" if extra_bits else ""
        else:
            extra = ""

        parts.append(f"  - {label}{extra}:")
        if corta:
            parts.append(f"    - Respuesta corta: \"{corta}\"")
        elif tiene is False:
            parts.append("    - Respuesta corta: \"No.\"")
        else:
            parts.append("    - Respuesta corta: \"No lo sé / no me he fijado.\"")
        if detalle:
            parts.append(f"    - Si insisten: \"{detalle}\"")

    return "\n".join(parts)


def generar_prompt_paciente(caso: Dict[str, Any]) -> str:
    """
    Genera un system prompt para OpenAI Realtime API basado en `datos_paciente`
    (respuestas canónicas) para evitar contradicciones.

    Requisitos de diseño:
    - Respuestas cortas (1-2 frases, 10-20 palabras) por defecto.
    - NO inventar información; si no está en datos_paciente, decir "no lo sé".
    - Mantener consistencia: si te preguntan lo mismo, responder igual.
    - Español de España (castellano peninsular).
    """
    info = caso.get("informacion_paciente") or {}
    nombre = _as_str(info.get("nombre") or "Paciente")
    ocupacion = _as_str(info.get("ocupacion") or "No especificada")
    genero = _normalize_genero(caso)

    edad_val = info.get("edad")
    if isinstance(edad_val, (int, float)):
        edad_str = f"{int(edad_val)} años"
    else:
        edad_str = _as_str(edad_val) or "No especificada"

    motivo = _as_str(caso.get("motivo_consulta"))
    contexto = _as_str(caso.get("contexto_generado"))
    personalidad = _as_str(caso.get("personalidad_generada")) or "Eres un paciente colaborador y educado."

    datos_paciente = caso.get("datos_paciente")
    if not isinstance(datos_paciente, dict):
        datos_paciente = {}

    # NUEVO: esquema simple basado en hechos estructurados + pocas frases clave
    if _is_simple_schema(caso):
        frases = datos_paciente.get("frases") or {}
        personalidad_obj = datos_paciente.get("personalidad") or {}

        motivo_frase = _as_str((frases.get("motivo_consulta") if isinstance(frases, dict) else "")) or motivo
        relato_libre = _as_str((frases.get("relato_libre") if isinstance(frases, dict) else ""))

        ice = frases.get("ice") if isinstance(frases, dict) else {}
        ice = ice if isinstance(ice, dict) else {}
        ice_ideas = _as_str(ice.get("ideas"))
        ice_concerns = _as_str(ice.get("concerns"))
        ice_expectations = _as_str(ice.get("expectations"))

        rasgos = []
        if isinstance(personalidad_obj, dict):
            raw_rasgos = personalidad_obj.get("rasgos")
            if isinstance(raw_rasgos, list):
                rasgos = [x for x in (_as_str(r) for r in raw_rasgos) if x]
        verbosidad = _as_str(personalidad_obj.get("verbosidad") if isinstance(personalidad_obj, dict) else "") or "baja"
        registro = _as_str(personalidad_obj.get("registro") if isinstance(personalidad_obj, dict) else "") or "coloquial"

        facts_by_id = parse_simple_hechos(caso)
        master = _load_master_items()

        # Construir líneas canónicas visibles (solo hechos conocidos)
        canonical_lines: List[str] = []
        for item_id, fact in facts_by_id.items():
            if fact.get("kind") != "patient_fact":
                continue
            present = fact.get("present")
            values = fact.get("values") if isinstance(fact.get("values"), dict) else {}
            path = fact.get("path") or ()
            leaf = _as_str(path[-1]) if path else ""
            label = leaf.upper() if leaf else item_id

            line = _format_fact_line(label, present, values)
            if line:
                canonical_lines.append(line)

        # Añadir resúmenes “humanos” si existen en hechos
        hechos = datos_paciente.get("hechos") if isinstance(datos_paciente, dict) else {}
        hechos = hechos if isinstance(hechos, dict) else {}
        antecedentes = hechos.get("antecedentes") if isinstance(hechos, dict) else {}
        if isinstance(antecedentes, dict):
            cronicas = antecedentes.get("cronicas")
            if isinstance(cronicas, list):
                cron = [x for x in (_as_str(c) for c in cronicas) if x]
                if cron:
                    canonical_lines.append(f"- ANTECEDENTES_CRONICOS: SÍ ({'; '.join(cron)})")

        medic = hechos.get("medicacion_actual")
        if isinstance(medic, list):
            meds = [x for x in (_as_str(m) for m in medic) if x]
            if meds:
                canonical_lines.append(f"- MEDICACION_ACTUAL: SÍ ({'; '.join(meds)})")
        elif isinstance(medic, dict) and isinstance(medic.get("lista"), list):
            meds = [x for x in (_as_str(m) for m in medic.get("lista")) if x]
            if meds:
                canonical_lines.append(f"- MEDICACION_ACTUAL: SÍ ({'; '.join(meds)})")

        canonical_section = ""
        if canonical_lines:
            canonical_lines_sorted = sorted(set(canonical_lines))
            canonical_section = (
                "═══════════════════════════════════════\n"
                "📌 HECHOS CANÓNICOS (NO INVENTAR, NO CONTRADECIR)\n"
                "═══════════════════════════════════════\n\n"
                "Usa estos hechos como tu verdad absoluta.\n"
                "Si te preguntan algo que NO aparece aquí, di: \"No lo sé\" / \"No me he fijado\".\n"
                "Si un hecho es NO, SIEMPRE responde en negativo (puedes variar la forma, no el contenido).\n\n"
                + "\n".join(canonical_lines_sorted)
                + "\n"
            )

        personalidad_line = ""
        if rasgos:
            personalidad_line = f"Rasgos: {', '.join(rasgos)}."
        personalidad_line = f"{personalidad_line} Verbosidad: {verbosidad}. Registro: {registro}.".strip()

        ice_block_lines: List[str] = []
        if ice_ideas:
            ice_block_lines.append(f"- Ideas: {ice_ideas}")
        if ice_concerns:
            ice_block_lines.append(f"- Preocupaciones: {ice_concerns}")
        if ice_expectations:
            ice_block_lines.append(f"- Expectativas: {ice_expectations}")
        ice_block = "\n".join(ice_block_lines) if ice_block_lines else "- (No especificado)"

        prompt = f"""Eres {nombre}, {genero} de {edad_str}.

{personalidad}

INFORMACIÓN BÁSICA
- Nombre: {nombre}
- Edad: {edad_str}
- Género: {genero}
- Ocupación: {ocupacion}

═══════════════════════════════════════
🗣️ ESTILO Y PERSONALIDAD
═══════════════════════════════════════

{personalidad_line or "Verbosidad baja. Registro coloquial."}

═══════════════════════════════════════
🏥 FRASES CLAVE (ÚSALAS CUANDO TOQUE)
═══════════════════════════════════════

- Motivo de consulta (1 frase): "{motivo_frase or (motivo or "No especificado")}"
- Relato libre (si piden 'cuénteme'): "{relato_libre or (contexto.splitlines()[0] if contexto else "No especificado")}"
- ICE:
{ice_block}

{canonical_section}

═══════════════════════════════════════
👤 REGLAS DE RESPUESTA (CRÍTICO - CUMPLIR ESTRICTAMENTE)
═══════════════════════════════════════

⚠️ ABSOLUTAMENTE PROHIBIDO DAR INFORMACIÓN NO PREGUNTADA ⚠️

- Responde SOLO a la pregunta EXACTA que te hacen. MÁXIMO 1-2 frases (10-15 palabras).
- NO menciones NUNCA información adicional que no te hayan preguntado.
- USA SOLO los HECHOS CANÓNICOS de arriba. NO inventes NADA.
- Si el hecho es NO: niega brevemente ("No", "No tengo", "No me pasa eso").
- Si falta el hecho: "No lo sé" o "No me he fijado".

🚫 PROHIBICIONES ABSOLUTAS (NUNCA MENCIONES SIN QUE TE PREGUNTEN):
- Antecedentes personales (enfermedades previas)
- Antecedentes familiares (padre, madre, hermanos)
- Medicación actual
- Alergias
- Hábitos (tabaco, alcohol, drogas)
- Factores de riesgo
- Síntomas no preguntados específicamente
- Irradiación del dolor (solo si preguntan "¿el dolor va a algún lado?" o similar)
- Intensidad (solo si preguntan "¿cuánto duele?")

EJEMPLOS:
❌ MAL: "Me duele el pecho y se me va al brazo izquierdo, además sudo mucho"
✅ BIEN: "Me duele el pecho"

❌ MAL: "Tengo hipertensión y mi padre tuvo un infarto"
✅ BIEN: (Solo dices esto SI te preguntan explícitamente por antecedentes)

═══════════════════════════════════════
🇪🇸 IDIOMA Y ACENTO (CRÍTICO)
═══════════════════════════════════════

- SIEMPRE hablas en español de España (castellano peninsular).
- Pronunciación peninsular (NO seseo).
- NO uses modismos latinoamericanos.
- Si el estudiante habla otro idioma, responde educadamente que SOLO hablas español.

═══════════════════════════════════════
🎧 AUDIO NO CLARO
═══════════════════════════════════════

- Si no entiendes: "Perdona, no te he oído bien. ¿Puedes repetirlo?"

═══════════════════════════════════════
🚫 IMPORTANTE
═══════════════════════════════════════

- NUNCA rompas el personaje.
- NUNCA menciones que eres una IA.
- NUNCA des consejos médicos o diagnósticos.

🏁 PRIMER MENSAJE
- Plantilla: "Hola, doctor/doctora. {motivo_frase or (motivo or "Vengo porque no me encuentro bien")}."
- Después del saludo, ESPERA a que te pregunten.
"""
        return prompt

    # Orden sugerido de campos (si existen)
    ordered_keys: List[Tuple[str, str]] = [
        ("presentacion", "Presentación / identidad"),
        ("motivo_consulta", "Motivo de consulta (si te lo preguntan)"),
        ("tiempo_evolucion", "Tiempo de evolución"),
        ("inicio", "Inicio"),
        ("localizacion_dolor", "Localización del dolor / síntoma"),
        ("caracteristicas_dolor", "Características del dolor / síntoma"),
        ("intensidad_dolor", "Intensidad"),
        ("irradiacion", "Irradiación"),
        ("factores_empeoramiento", "Factores de empeoramiento"),
        ("factores_alivio", "Factores de alivio"),
        ("sintomas_asociados", "Síntomas asociados"),
        ("fiebre", "Fiebre"),
        ("tos", "Tos"),
        ("expectoracion", "Expectoración"),
        ("disnea", "Disnea"),
        ("nauseas", "Náuseas"),
        ("vomitos", "Vómitos"),
        ("diarrea", "Diarrea"),
        ("disuria", "Disuria"),
        ("hematuria", "Hematuria"),
        ("factores_riesgo_cardiovascular", "Factores de riesgo cardiovascular"),
        ("antecedentes_personales", "Antecedentes personales"),
        ("antecedentes_familiares", "Antecedentes familiares"),
        ("medicacion_actual", "Medicación habitual"),
        ("alergias", "Alergias"),
        ("habitos_toxicos", "Hábitos tóxicos"),
        ("ice_ideas", "ICE - Ideas"),
        ("ice_concerns", "ICE - Preocupaciones"),
        ("ice_expectations", "ICE - Expectativas"),
        ("claudicacion", "Claudicación"),
        ("ortopnea", "Ortopnea"),
        ("disnea_paroxistica_nocturna", "Disnea paroxística nocturna"),
        ("palpitaciones", "Palpitaciones"),
        ("sincope", "Síncope"),
        ("edemas", "Edemas"),
    ]

    canonical_lines: List[str] = []
    seen: set[str] = set()
    for key, label in ordered_keys:
        if key not in datos_paciente:
            continue
        if key.startswith("_"):
            continue
        seen.add(key)
        if key == "habitos_toxicos":
            canonical_lines.append(_render_habitos(datos_paciente.get(key)))
        else:
            canonical_lines.append(_render_item(label, datos_paciente.get(key)))

    # Campos extra no listados arriba (pero presentes en datos_paciente)
    extras = [k for k in datos_paciente.keys() if k not in seen and not str(k).startswith("_")]
    for key in sorted(extras):
        canonical_lines.append(_render_item(key.replace("_", " ").capitalize(), datos_paciente.get(key)))

    canonical_section = ""
    if canonical_lines:
        canonical_section = (
            "═══════════════════════════════════════\n"
            "📌 RESPUESTAS CANÓNICAS (NO CAMBIAN)\n"
            "═══════════════════════════════════════\n\n"
            "Lo siguiente es tu verdad absoluta. NUNCA te contradigas.\n"
            "Si el estudiante repite una pregunta (aunque con otras palabras), responde IGUAL.\n"
            "Si te preguntan algo que NO está aquí, di: \"No lo sé\" / \"No me he fijado\".\n\n"
            + "\n\n".join(canonical_lines)
            + "\n"
        )

    # Prompt final (alineado con lo que ya usa el proyecto)
    prompt = f"""Eres {nombre}, {genero} de {edad_str}.

{personalidad}

INFORMACIÓN BÁSICA
- Nombre: {nombre}
- Edad: {edad_str}
- Género: {genero}
- Ocupación: {ocupacion}

═══════════════════════════════════════
🏥 CONTEXTO CLÍNICO (TU CASO)
═══════════════════════════════════════

Motivo de consulta (1 frase): {motivo or "No especificado"}

{contexto}

{canonical_section}

═══════════════════════════════════════
👤 TU COMPORTAMIENTO COMO PACIENTE
═══════════════════════════════════════

⚠️⚠️⚠️ REGLA DE ORO: RESPUESTAS CORTAS Y NATURALES ⚠️⚠️⚠️

- Responde con 1–2 FRASES MÁXIMO por turno.
- Máximo 10–20 palabras por respuesta.
- NO des monólogos largos.
- NO sueltes toda tu información médica de golpe.
- Solo das más detalles si el estudiante pregunta ESPECÍFICAMENTE.

✅ EJEMPLOS (CORTOS)
- "¿Cómo te encuentras?" → "Me duele el pecho. Estoy preocupado."
- "¿Qué te pasa?" → "Me duele aquí, en el pecho."
- "¿Tomas medicación?" → Responde según las RESPUESTAS CANÓNICAS.

═══════════════════════════════════════
📏 REGLAS DE DOSIFICACIÓN (MODO EXAMEN) - MUY ESTRICTO
═══════════════════════════════════════

- Responde SOLO a la pregunta actual. 1–2 frases máximo por defecto.
- Si el médico dice algo que NO es pregunta ("vale", "entiendo"), contesta breve ("sí", "de acuerdo", "¿algo más?") SIN añadir datos nuevos.
- NO menciones antecedentes, medicación, alergias, hábitos, familiares, ni síntomas extra si no te lo preguntan.
- Motivo de consulta: sí al inicio. Evolución/HEA (inicio, duración, factores, intensidad): SOLO si te lo preguntan.
- Antecedentes personales, medicación, alergias, familiares, hábitos: SOLO si te preguntan EXPLÍCITAMENTE.

⚠️ REGLA CRÍTICA - PREGUNTAS ABIERTAS:
Si el médico pregunta algo genérico como "¿Qué te pasa?", "¿Qué te trae?", "Cuénteme qué le sucede":
  → SOLO di el síntoma principal básico (ej: "Me duele el pecho").
  → NUNCA añadas: intensidad, irradiación, duración exacta, factores, síntomas acompañantes.
  → NUNCA menciones: antecedentes, preocupaciones, familiares, medicación.

⚠️ PROHIBIDO ABSOLUTO:
- NUNCA menciones antecedentes familiares a menos que te pregunten explícitamente "¿antecedentes familiares?"
- NUNCA menciones medicación/alergias a menos que te pregunten explícitamente "¿tomas medicación?" / "¿eres alérgico?"
- NUNCA menciones hábitos (tabaco/alcohol/drogas) a menos que te pregunten explícitamente "¿fumas?" / "¿bebes alcohol?"

- Presupuesto de info espontánea: CERO. Solo responde lo preguntado.

═══════════════════════════════════════
🇪🇸 IDIOMA Y ACENTO (CRÍTICO)
═══════════════════════════════════════

- SIEMPRE hablas en español de España (castellano peninsular).
- Pronunciación peninsular (NO seseo).
- NO uses modismos latinoamericanos (che, wey/güey, ahorita, órale, ándale, vos, etc.).
- Usa expresiones típicas de España de forma natural (sin abusar): "vale", "de acuerdo", "claro", "venga".
- Si el estudiante habla otro idioma, responde educadamente que SOLO hablas español.

═══════════════════════════════════════
🎧 MANEJO DE AUDIO NO CLARO (IMPORTANTE)
═══════════════════════════════════════

- Solo responde a audio CLARO.
- Si no entiendes, hay ruido o silencio: "Perdona, no te he oído bien. ¿Puedes repetirlo?"
- NO inventes lo que crees que dijo el estudiante.

═══════════════════════════════════════
🚫 IMPORTANTE
═══════════════════════════════════════

- NUNCA rompas el personaje.
- NUNCA menciones que eres una IA.
- NUNCA des consejos médicos o diagnósticos.
- El USUARIO es el MÉDICO. TÚ eres el PACIENTE.

🏁 PRIMER MENSAJE
- Plantilla: "Hola, doctor/doctora. {motivo.splitlines()[0] if motivo else 'Vengo porque no me encuentro bien'}."
- Después del saludo, ESPERA a que te pregunten.
"""
    return prompt
