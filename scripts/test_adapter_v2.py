#!/usr/bin/env python3
"""
Test para CaseAdapterV2
Valida adaptación dinámica de checklist según síntomas del caso.

Tests:
1. Caso dolor torácico → activa CARDIOVASCULAR + RESPIRATORIO
2. Caso cefalea → activa NEUROLOGICO
3. Caso dolor abdominal + náuseas → activa DIGESTIVO
4. Caso sin síntomas → activa TODAS las subsecciones B7 (fallback)
5. Validar que max_points_case < 180 cuando B7 es parcial
6. Validar recálculo correcto de min_points_case
"""

import sys
from pathlib import Path

# Añadir simulador/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "simulador"))

from case_adapter_v2 import CaseAdapterV2


def test_dolor_toracico():
    """Test: caso dolor torácico activa CARDIOVASCULAR + RESPIRATORIO"""
    print("\n" + "="*70)
    print("TEST 1: Dolor Torácico → CARDIOVASCULAR + RESPIRATORIO")
    print("="*70)

    adapter = CaseAdapterV2()

    case_data = {
        "id": "test_001",
        "sintomas_principales": [
            "dolor torácico",
            "dolor retroesternal",
            "disnea",
            "sudoración"
        ],
        "motivo_consulta": "Dolor torácico de 2 horas de evolución"
    }

    result = adapter.adapt_to_case(case_data)

    # Validaciones
    subsections = result["subsections_b7_activas"]
    print(f"✅ Subsecciones B7 activas: {subsections}")

    assert "CARDIOVASCULAR" in subsections, "Debe activar CARDIOVASCULAR"
    assert "RESPIRATORIO" in subsections, "Debe activar RESPIRATORIO"
    assert len(subsections) == 2, f"Debe activar solo 2 subsecciones, activó {len(subsections)}"

    # Validar que max_points_case < 180 (porque B7 es parcial)
    max_points = result["max_points_case"]
    print(f"✅ max_points_case: {max_points} (< 180 porque B7 parcial)")
    assert max_points < 180, f"max_points_case debe ser < 180, es {max_points}"

    # Validar min_points_case
    min_points = result["min_points_case"]
    expected_min = int(max_points * 57.2 / 100) + (1 if max_points * 57.2 % 100 > 0 else 0)
    print(f"✅ min_points_case: {min_points} (57.2% de {max_points})")
    assert min_points == expected_min, f"min_points_case debe ser {expected_min}, es {min_points}"

    # Validar items activos
    total_items = result["total_items_activos"]
    print(f"✅ Total items activos: {total_items}")
    assert total_items < 180, f"Total items debe ser < 180, es {total_items}"

    print(f"✅ Bloques activos: {result['blocks_activos']}")
    print("✅ TEST 1 PASADO")


def test_cefalea():
    """Test: caso cefalea activa NEUROLOGICO"""
    print("\n" + "="*70)
    print("TEST 2: Cefalea → NEUROLOGICO")
    print("="*70)

    adapter = CaseAdapterV2()

    case_data = {
        "id": "test_002",
        "sintomas_principales": ["cefalea", "mareo"],
        "motivo_consulta": "Cefalea intensa desde hace 3 días"
    }

    result = adapter.adapt_to_case(case_data)

    subsections = result["subsections_b7_activas"]
    print(f"✅ Subsecciones B7 activas: {subsections}")

    assert "NEUROLOGICO" in subsections, "Debe activar NEUROLOGICO"
    # Mareo activa NEUROLOGICO + CARDIOVASCULAR
    assert "CARDIOVASCULAR" in subsections, "Mareo debe activar también CARDIOVASCULAR"

    print(f"✅ max_points_case: {result['max_points_case']}")
    print(f"✅ Total items activos: {result['total_items_activos']}")
    print("✅ TEST 2 PASADO")


def test_dolor_abdominal():
    """Test: dolor abdominal + náuseas activa DIGESTIVO"""
    print("\n" + "="*70)
    print("TEST 3: Dolor Abdominal + Náuseas → DIGESTIVO")
    print("="*70)

    adapter = CaseAdapterV2()

    case_data = {
        "id": "test_003",
        "sintomas_principales": ["dolor abdominal", "náuseas", "vómitos"],
        "motivo_consulta": "Dolor abdominal y vómitos",
        "contexto_generado": "Paciente con dolor epigástrico y náuseas desde hace 6 horas"
    }

    result = adapter.adapt_to_case(case_data)

    subsections = result["subsections_b7_activas"]
    print(f"✅ Subsecciones B7 activas: {subsections}")

    assert "DIGESTIVO" in subsections, "Debe activar DIGESTIVO"
    assert len(subsections) == 1, f"Debe activar solo DIGESTIVO, activó {subsections}"

    print(f"✅ max_points_case: {result['max_points_case']}")
    print(f"✅ Síntomas detectados: {result['sintomas_detectados']}")
    print("✅ TEST 3 PASADO")


def test_sin_sintomas_fallback():
    """Test: caso sin síntomas activa TODAS las subsecciones (fallback)"""
    print("\n" + "="*70)
    print("TEST 4: Sin Síntomas → TODAS las subsecciones (fallback)")
    print("="*70)

    adapter = CaseAdapterV2()

    case_data = {
        "id": "test_004",
        "motivo_consulta": "Revisión general"
    }

    result = adapter.adapt_to_case(case_data)

    subsections = result["subsections_b7_activas"]
    print(f"✅ Subsecciones B7 activas: {subsections}")

    # Debe activar todas las 10 subsecciones
    assert len(subsections) == 10, f"Debe activar 10 subsecciones, activó {len(subsections)}"

    # max_points_case debe ser 180 (checklist completo)
    max_points = result["max_points_case"]
    print(f"✅ max_points_case: {max_points} (checklist completo)")
    assert max_points == 180, f"max_points_case debe ser 180, es {max_points}"

    print("✅ TEST 4 PASADO")


def test_bloques_universales():
    """Test: bloques universales siempre activos"""
    print("\n" + "="*70)
    print("TEST 5: Bloques Universales Siempre Activos")
    print("="*70)

    adapter = CaseAdapterV2()

    case_data = {
        "id": "test_005",
        "sintomas_principales": ["cefalea"]  # Solo NEUROLOGICO
    }

    result = adapter.adapt_to_case(case_data)

    blocks = result["blocks_activos"]
    print(f"✅ Bloques activos: {list(blocks.keys())}")

    # Verificar bloques universales
    universal_blocks = [
        "B0_INTRODUCCION",
        "B1_MOTIVO_CONSULTA",
        "B2_HEA",
        "B3_ANTECEDENTES",
        "B4_MEDICACION_ALERGIAS",
        "B5_SOCIAL",
        "B6_FAMILIAR",
        "B8_CIERRE",
        "B9_COMUNICACION"
    ]

    for block_id in universal_blocks:
        assert block_id in blocks, f"Bloque universal {block_id} debe estar activo"
        assert blocks[block_id] > 0, f"Bloque {block_id} debe tener puntos > 0"

    # B7 debe estar activo pero con menos puntos que el máximo
    assert "B7_ANAMNESIS_APARATOS" in blocks, "B7 debe estar activo"
    b7_points = blocks["B7_ANAMNESIS_APARATOS"]
    print(f"✅ B7_ANAMNESIS_APARATOS: {b7_points} pts (parcial)")
    assert b7_points < 75, f"B7 debe tener menos de 75 pts (parcial), tiene {b7_points}"

    print("✅ TEST 5 PASADO")


def test_caso_real():
    """Test: caso real de dolor torácico del sistema"""
    print("\n" + "="*70)
    print("TEST 6: Caso Real - Dolor Torácico (caso_prueba_001)")
    print("="*70)

    adapter = CaseAdapterV2()

    # Caso real del sistema
    case_data = {
        "id": "caso_prueba_001",
        "titulo": "Dolor Torácico Agudo - Caso de Prueba",
        "sintomas_principales": [
            "dolor torácico",
            "dolor retroesternal",
            "dolor opresivo",
            "irradiación a brazo",
            "sudoración",
            "náuseas",
            "disnea"
        ],
        "motivo_consulta": "Dolor torácico de 2 horas de evolución"
    }

    result = adapter.adapt_to_case(case_data)

    print(f"✅ Síntomas detectados: {result['sintomas_detectados']}")
    print(f"✅ Subsecciones B7: {result['subsections_b7_activas']}")
    print(f"✅ max_points_case: {result['max_points_case']}")
    print(f"✅ min_points_case: {result['min_points_case']}")
    print(f"✅ Total items: {result['total_items_activos']}")

    # Debe activar CARDIOVASCULAR + RESPIRATORIO + DIGESTIVO (por náuseas)
    subsections = result["subsections_b7_activas"]
    assert "CARDIOVASCULAR" in subsections
    assert "RESPIRATORIO" in subsections
    assert "DIGESTIVO" in subsections

    # Validar estructura completa
    assert "items_activos" in result
    assert len(result["items_activos"]) > 0
    assert "blocks_activos" in result

    print("✅ TEST 6 PASADO")


def main():
    print("🧪 Test Suite - CaseAdapterV2")
    print("="*70)
    print("Validando adaptación dinámica de checklist según síntomas")
    print("="*70)

    try:
        test_dolor_toracico()
        test_cefalea()
        test_dolor_abdominal()
        test_sin_sintomas_fallback()
        test_bloques_universales()
        test_caso_real()

        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS PASARON (6/6)")
        print("="*70)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ TEST FALLIDO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
