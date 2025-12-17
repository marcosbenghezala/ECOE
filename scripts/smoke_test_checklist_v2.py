#!/usr/bin/env python3
"""
Smoke test para master-checklist-v2.json
Verifica estructura, coherencia y compilación de regex.

Exit codes:
  0 = OK
  1 = Error de validación
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict

DATA_DIR = Path(__file__).parent.parent / "data"
CHECKLIST_PATH = DATA_DIR / "master-checklist-v2.json"


def test_file_exists():
    """Test: archivo existe"""
    if not CHECKLIST_PATH.exists():
        print(f"❌ Archivo no existe: {CHECKLIST_PATH}")
        sys.exit(1)
    print(f"✅ Archivo existe: {CHECKLIST_PATH}")


def test_valid_json():
    """Test: JSON válido"""
    try:
        with open(CHECKLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✅ JSON válido")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido: {e}")
        sys.exit(1)


def test_metadata(data: Dict):
    """Test: metadata correcta"""
    meta = data.get("metadata", {})

    # Verificar campos requeridos
    required = [
        "version",
        "total_blocks",
        "total_items",
        "max_points",
        "min_points_required",
        "passing_percentage",
    ]
    for field in required:
        if field not in meta:
            print(f"❌ Metadata falta campo: {field}")
            sys.exit(1)

    # Verificar valores esperados
    if meta["total_blocks"] != 10:
        print(f"❌ total_blocks debe ser 10, es {meta['total_blocks']}")
        sys.exit(1)

    if meta["total_items"] != 180:
        print(f"❌ total_items debe ser 180, es {meta['total_items']}")
        sys.exit(1)

    if meta["max_points"] != 180:
        print(f"❌ max_points debe ser 180, es {meta['max_points']}")
        sys.exit(1)

    # Verificar cálculo de min_points (debe ser ceil de passing_percentage)
    import math

    expected_min = math.ceil(meta["max_points"] * meta["passing_percentage"] / 100)
    actual_min = meta["min_points_required"]
    if actual_min != expected_min:
        print(
            f"❌ min_points_required={actual_min}, esperado {expected_min} "
            f"(ceil de {meta['passing_percentage']}% de {meta['max_points']})"
        )
        sys.exit(1)

    print(
        f"✅ Metadata: {meta['total_blocks']} bloques, {meta['total_items']} ítems, "
        f"{meta['max_points']} pts máx, {meta['min_points_required']} pts mín ({meta['passing_percentage']}%)"
    )


def test_unique_ids(data: Dict):
    """Test: IDs únicos en blocks e items"""
    block_ids = [b["block_id"] for b in data.get("blocks", [])]
    if len(block_ids) != len(set(block_ids)):
        print("❌ IDs de bloques duplicados")
        sys.exit(1)

    item_ids = [i["id"] for i in data.get("items", [])]
    if len(item_ids) != len(set(item_ids)):
        print("❌ IDs de ítems duplicados")
        sys.exit(1)

    print(f"✅ IDs únicos: {len(block_ids)} bloques, {len(item_ids)} ítems")


def test_block_item_consistency(data: Dict):
    """Test: suma de items coincide con blocks.max_points"""
    blocks_map = {b["block_id"]: b for b in data.get("blocks", [])}

    # Sumar puntos por bloque (solo items aplicables)
    block_totals = {}
    for item in data.get("items", []):
        if not item.get("no_applicable", False):
            bid = item["block_id"]
            block_totals[bid] = block_totals.get(bid, 0) + item.get("points", 0)

    # Verificar coherencia
    for bid, total in block_totals.items():
        if bid not in blocks_map:
            print(f"❌ Item referencia bloque inexistente: {bid}")
            sys.exit(1)

        expected = blocks_map[bid]["max_points"]
        if total != expected:
            print(f"❌ Bloque {bid}: suma items={total} ≠ max_points={expected}")
            sys.exit(1)

    print("✅ Coherencia blocks ↔ items: suma de puntos coincide")


def test_subsections(data: Dict):
    """Test: subsecciones detectadas (items con campo 'subsection')"""
    subsections = set()
    for item in data.get("items", []):
        if "subsection" in item and item["subsection"]:
            subsections.add(item["subsection"])

    if len(subsections) != 10:
        print(
            f"❌ Se esperan 10 subsecciones, encontradas {len(subsections)}: "
            f"{', '.join(sorted(subsections))}"
        )
        sys.exit(1)

    print(f"✅ Subsecciones: 10 detectadas ({', '.join(sorted(subsections))})")


def test_regex_compilable(data: Dict):
    """Test: todos los regex compilan sin errores"""
    errors = []
    total_patterns = 0

    for item in data.get("items", []):
        for pattern in item.get("regex", []):
            total_patterns += 1
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                errors.append(f"Item {item['id']}: regex inválido '{pattern}': {e}")

    if errors:
        print("❌ Errores en regex:")
        for err in errors:
            print(f"   {err}")
        sys.exit(1)

    print(f"✅ Regex: {total_patterns} patrones compilados OK")


def main():
    print("🧪 Smoke Test - Checklist V2")
    print("=" * 70)

    test_file_exists()
    data = test_valid_json()
    test_metadata(data)
    test_unique_ids(data)
    test_block_item_consistency(data)
    test_subsections(data)
    test_regex_compilable(data)

    print("=" * 70)
    print("✅ TODOS LOS TESTS PASARON")
    sys.exit(0)


if __name__ == "__main__":
    main()
