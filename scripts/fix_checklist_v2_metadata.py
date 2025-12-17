"""
Corrige y valida la metadata del checklist v2 (schema plano) y genera
data/master-checklist-v2.json a partir del archivo existente (WIP o final).
"""

import json
import math
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Set


DATA_DIR = Path(__file__).parent.parent / "data"


def _load_source() -> Path:
    """Devuelve el path de origen (WIP si existe, si no el final)."""
    wip = DATA_DIR / "master-checklist.v2.work-in-progress.json"
    final = DATA_DIR / "master-checklist-v2.json"
    if wip.exists():
        return wip
    if final.exists():
        return final
    raise FileNotFoundError("No se encontró checklist v2 en data/")


def _validate(data: Dict) -> None:
    """Validaciones básicas: IDs únicos, regex compilables."""
    block_ids: Set[str] = set()
    for b in data.get("blocks", []):
        bid = b.get("block_id")
        if not bid or bid in block_ids:
            raise ValueError(f"block_id duplicado o vacío: {bid}")
        block_ids.add(bid)

    item_ids: Set[str] = set()
    for it in data.get("items", []):
        iid = it.get("id")
        if not iid or iid in item_ids:
            raise ValueError(f"id de item duplicado o vacío: {iid}")
        item_ids.add(iid)
        for pat in it.get("regex", []) or []:
            re.compile(pat, re.IGNORECASE)


def _validate_block_references(data: Dict) -> None:
    """Valida que cada item.block_id existe en blocks."""
    block_ids_declared = {b["block_id"] for b in data.get("blocks", [])}

    for item in data.get("items", []):
        item_block_id = item.get("block_id")
        if not item_block_id:
            raise ValueError(f"Item {item.get('id', 'unknown')} no tiene block_id")
        if item_block_id not in block_ids_declared:
            raise ValueError(
                f"Item {item['id']} referencia bloque inexistente: {item_block_id}"
            )


def _validate_block_consistency(data: Dict) -> None:
    """Valida que suma de puntos de items coincida con blocks.max_points."""
    # Agrupar items por block_id y sumar puntos (solo no_applicable=false)
    block_totals = {}
    for item in data.get("items", []):
        if not item.get("no_applicable", False):
            bid = item["block_id"]
            block_totals[bid] = block_totals.get(bid, 0) + item.get("points", 0)

    # Verificar coherencia contra blocks declarados
    for block in data.get("blocks", []):
        bid = block["block_id"]
        expected = block.get("max_points", 0)
        actual = block_totals.get(bid, 0)

        if actual != expected:
            raise ValueError(
                f"Bloque {bid}: suma items={actual} ≠ max_points={expected}"
            )


def fix_metadata() -> None:
    """Actualiza metadata y guarda como master-checklist-v2.json."""
    file_path = _load_source()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validaciones (orden importante)
    _validate(data)
    _validate_block_references(data)
    _validate_block_consistency(data)

    total_items = len(data["items"])
    total_points = sum(
        item["points"] for item in data["items"] if not item.get("no_applicable", False)
    )

    # Calcular min_points_required desde passing_percentage
    passing_percentage = 57.2
    min_points_required = math.ceil(total_points * passing_percentage / 100)

    data["metadata"] = {
        "version": "2.0",
        "name": "Checklist ECOE - Anamnesis Clínica",
        "total_blocks": len(data.get("blocks", [])),
        "total_items": total_items,
        "max_points": total_points,
        "min_points_required": min_points_required,
        "passing_percentage": passing_percentage,
        "date_created": "2025-12-15",
        "language": "es",
    }

    # Detectar subsecciones (items con campo 'subsection')
    subsections = set()
    for item in data["items"]:
        if "subsection" in item and item["subsection"]:
            subsections.add(item["subsection"])

    # Escritura atómica: temp file + rename
    output_path = DATA_DIR / "master-checklist-v2.json"
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        delete=False,
        dir=output_path.parent,
        suffix='.tmp'
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    # Atomic move
    shutil.move(str(tmp_path), str(output_path))

    print("✅ Checklist v2 normalizado y validado:")
    print(f"   - Archivo: {output_path}")
    print(f"   - Bloques: {data['metadata']['total_blocks']}")
    print(f"   - Ítems: {total_items}")
    print(f"   - Puntos máximos: {total_points}")
    print(f"   - Puntos mínimos (aprobado): {min_points_required} ({passing_percentage}%)")
    if subsections:
        print(f"   - Subsecciones: {len(subsections)} ({', '.join(sorted(subsections))})")


if __name__ == "__main__":
    fix_metadata()
