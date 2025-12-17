#!/usr/bin/env python3
"""
Smoke test para ChecklistLoaderV2
Verifica carga, índices y helpers.

Exit codes:
  0 = OK
  1 = Error
"""

import sys
from pathlib import Path

# Añadir parent al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulador.checklist_loader_v2 import load_checklist_v2


def test_load():
    """Test: cargar checklist sin errores"""
    try:
        loader = load_checklist_v2()
        print("✅ Checklist cargado sin errores")
        return loader
    except Exception as e:
        print(f"❌ Error al cargar checklist: {e}")
        sys.exit(1)


def test_metadata(loader):
    """Test: metadata correcta"""
    meta = loader.metadata

    # Verificar valores esperados
    if meta["total_blocks"] != 10:
        print(f"❌ total_blocks debe ser 10, es {meta['total_blocks']}")
        sys.exit(1)

    if meta["total_items"] != 180:
        print(f"❌ total_items debe ser 180, es {meta['total_items']}")
        sys.exit(1)

    print(
        f"✅ Metadata: {meta['total_blocks']} bloques, "
        f"{meta['total_items']} ítems, "
        f"{meta['max_points']} pts máx"
    )


def test_indices(loader):
    """Test: índices construidos correctamente"""
    # blocks_by_id
    if len(loader.blocks_by_id) != 10:
        print(f"❌ blocks_by_id debe tener 10 bloques, tiene {len(loader.blocks_by_id)}")
        sys.exit(1)

    # items_by_id
    if len(loader.items_by_id) != 180:
        print(f"❌ items_by_id debe tener 180 ítems, tiene {len(loader.items_by_id)}")
        sys.exit(1)

    # items_by_block
    if len(loader.items_by_block) != 10:
        print(
            f"❌ items_by_block debe tener 10 bloques, tiene {len(loader.items_by_block)}"
        )
        sys.exit(1)

    # items_by_subsection
    if len(loader.items_by_subsection) != 10:
        print(
            f"❌ items_by_subsection debe tener 10 subsecciones, "
            f"tiene {len(loader.items_by_subsection)}"
        )
        sys.exit(1)

    print(
        f"✅ Índices: {len(loader.blocks_by_id)} bloques, "
        f"{len(loader.items_by_id)} ítems, "
        f"{len(loader.items_by_subsection)} subsecciones"
    )


def test_helpers(loader):
    """Test: helpers funcionan correctamente"""
    # get_block
    block = loader.get_block("B0_INTRODUCCION")
    if not block or block["block_id"] != "B0_INTRODUCCION":
        print(f"❌ get_block('B0_INTRODUCCION') falló")
        sys.exit(1)

    # get_items_for_block
    items_b0 = loader.get_items_for_block("B0_INTRODUCCION")
    if len(items_b0) != 12:
        print(f"❌ B0 debe tener 12 ítems, tiene {len(items_b0)}")
        sys.exit(1)

    # get_items_for_subsection
    items_cardio = loader.get_items_for_subsection("CARDIOVASCULAR")
    if len(items_cardio) == 0:
        print(f"❌ CARDIOVASCULAR debe tener ítems, tiene 0")
        sys.exit(1)

    # list_subsections
    subsections = loader.list_subsections()
    if len(subsections) != 10:
        print(f"❌ list_subsections() debe devolver 10, devuelve {len(subsections)}")
        sys.exit(1)

    # get_subsections_for_block (B7)
    b7_subsections = loader.get_subsections_for_block("B7_ANAMNESIS_APARATOS")
    if len(b7_subsections) != 10:
        print(
            f"❌ B7 debe tener 10 subsecciones, tiene {len(b7_subsections)}: {b7_subsections}"
        )
        sys.exit(1)

    # get_applicable_items
    applicable = loader.get_applicable_items()
    if len(applicable) != 180:
        print(f"❌ get_applicable_items() debe devolver 180, devuelve {len(applicable)}")
        sys.exit(1)

    print(
        f"✅ Helpers: get_block OK, get_items_for_block OK, "
        f"list_subsections OK ({len(subsections)} subsecciones)"
    )


def test_compiled_regex(loader):
    """Test: regex pre-compilados"""
    total_compiled = sum(len(patterns) for patterns in loader.compiled_regex.values())
    if total_compiled == 0:
        print(f"❌ No hay regex compilados (esperado > 0)")
        sys.exit(1)

    print(f"✅ Regex pre-compilados: {total_compiled} patrones en {len(loader.compiled_regex)} ítems")


def test_cache():
    """Test: @lru_cache funciona (singleton)"""
    loader1 = load_checklist_v2()
    loader2 = load_checklist_v2()

    if loader1 is not loader2:
        print(f"❌ load_checklist_v2() no está cacheado (singleton esperado)")
        sys.exit(1)

    print("✅ Cache: load_checklist_v2() retorna singleton (cached)")


def main():
    print("🧪 Smoke Test - ChecklistLoaderV2")
    print("=" * 70)

    loader = test_load()
    test_metadata(loader)
    test_indices(loader)
    test_helpers(loader)
    test_compiled_regex(loader)
    test_cache()

    print("=" * 70)
    print("✅ TODOS LOS TESTS PASARON")
    sys.exit(0)


if __name__ == "__main__":
    main()
