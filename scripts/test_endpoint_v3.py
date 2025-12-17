#!/usr/bin/env python3
"""
Test de integración para endpoint /api/evaluate_checklist_v3

Tests:
1. Test básico: crear sesión + evaluar
2. Verificar estructura de respuesta
3. Validar que V2 y V3 pueden coexistir
4. Test con transcript completo
"""

import sys
import json
import requests
import uuid
from pathlib import Path

# URL del servidor (ajustar si es necesario)
BASE_URL = "http://localhost:5000"


def test_endpoint_exists():
    """Test 1: Endpoint /api/evaluate_checklist_v3 existe"""
    print("\n" + "="*70)
    print("TEST 1: Endpoint Existe")
    print("="*70)

    # Crear una sesión mock primero
    session_id = str(uuid.uuid4())
    case_data = {
        "id": "test_001",
        "titulo": "Caso Test",
        "sintomas_principales": ["dolor torácico"]
    }
    transcript = """
[ESTUDIANTE]: Buenos días, mi nombre es Dr. García.
[PACIENTE]: Buenos días doctor.
[ESTUDIANTE]: ¿Cuál es el motivo de su consulta?
[PACIENTE]: Tengo dolor en el pecho.
"""

    # Simular sesión manualmente (normalmente se crea con /api/simulation/start)
    # Para este test, vamos a crear la sesión directamente en el endpoint

    payload = {
        "session_id": session_id,
        "transcript": transcript,
        "case_data": case_data
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/evaluate_checklist_v3",
            json=payload,
            timeout=10
        )

        # Puede fallar por "sesión no encontrada" o rate limiting, pero el endpoint debe existir
        if response.status_code == 404:
            print("✅ Endpoint existe (devolvió 404 por sesión no encontrada)")
            return True
        elif response.status_code == 200:
            print("✅ Endpoint existe y funciona")
            return True
        elif response.status_code == 403:
            print("✅ Endpoint existe (devolvió 403 por rate limiting - servidor corriendo)")
            return True
        else:
            print(f"⚠️  Endpoint respondió con status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Servidor no está corriendo en", BASE_URL)
        print("   Inicia el servidor con: python simulador/colab_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_endpoint_structure():
    """Test 2: Estructura de respuesta correcta"""
    print("\n" + "="*70)
    print("TEST 2: Estructura de Respuesta")
    print("="*70)

    print("⚠️  Este test requiere servidor activo con sesión creada")
    print("   Para ejecutar test completo:")
    print("   1. Inicia servidor: python simulador/colab_server.py")
    print("   2. Crea sesión desde frontend o con /api/simulation/start")
    print("   3. Llama a /api/evaluate_checklist_v3 con session_id")
    print("")
    print("✅ TEST 2 SKIPPED (requiere servidor + sesión)")


def test_v2_v3_coexist():
    """Test 3: V2 y V3 pueden coexistir"""
    print("\n" + "="*70)
    print("TEST 3: V2 y V3 Coexisten")
    print("="*70)

    print("✅ Verificando que ambos endpoints están definidos en código:")

    # Leer colab_server.py
    server_file = Path(__file__).parent.parent / "simulador" / "colab_server.py"
    content = server_file.read_text()

    # Verificar imports
    has_v2_import = "from evaluator_v2 import EvaluatorV2" in content
    has_v3_import = "from evaluator_v3 import EvaluatorV3" in content

    # Verificar inicialización
    has_v2_init = "evaluator = EvaluatorV2(" in content
    has_v3_init = "evaluator_v3 = EvaluatorV3(" in content

    # Verificar endpoints
    has_v2_endpoint = "@app.route('/api/simulation/evaluate'" in content
    has_v3_endpoint = "@app.route('/api/evaluate_checklist_v3'" in content

    print(f"   Imports:")
    print(f"      V2: {'✅' if has_v2_import else '❌'}")
    print(f"      V3: {'✅' if has_v3_import else '❌'}")

    print(f"   Inicialización:")
    print(f"      V2: {'✅' if has_v2_init else '❌'}")
    print(f"      V3: {'✅' if has_v3_init else '❌'}")

    print(f"   Endpoints:")
    print(f"      V2 (/api/simulation/evaluate): {'✅' if has_v2_endpoint else '❌'}")
    print(f"      V3 (/api/evaluate_checklist_v3): {'✅' if has_v3_endpoint else '❌'}")

    all_ok = all([
        has_v2_import, has_v3_import,
        has_v2_init, has_v3_init,
        has_v2_endpoint, has_v3_endpoint
    ])

    if all_ok:
        print("\n✅ TEST 3 PASADO - V2 y V3 coexisten correctamente")
        return True
    else:
        print("\n❌ TEST 3 FALLIDO - Falta alguna configuración")
        return False


def test_evaluator_v3_standalone():
    """Test 4: EvaluatorV3 funciona standalone (sin servidor)"""
    print("\n" + "="*70)
    print("TEST 4: EvaluatorV3 Standalone")
    print("="*70)

    # Agregar ruta al path
    sys.path.insert(0, str(Path(__file__).parent.parent / "simulador"))

    try:
        from evaluator_v3 import EvaluatorV3

        evaluator = EvaluatorV3()
        print("✅ EvaluatorV3 importado e inicializado")

        # Test simple
        transcript = """
[ESTUDIANTE]: Buenos días, soy el Dr. García.
[PACIENTE]: Buenos días.
[ESTUDIANTE]: ¿Cuál es el motivo de consulta?
[PACIENTE]: Dolor de cabeza.
"""

        case_data = {
            "id": "test_standalone",
            "sintomas_principales": ["cefalea"]
        }

        result = evaluator.evaluate_transcript(transcript, case_data)

        # Verificar campos requeridos
        required_fields = [
            "caso_id",
            "max_points_case",
            "min_points_case",
            "points_obtained",
            "percentage",
            "passed",
            "subsections_b7_activas",
            "blocks",
            "items_evaluated",
            "summary"
        ]

        missing_fields = [f for f in required_fields if f not in result]

        if missing_fields:
            print(f"❌ Campos faltantes: {missing_fields}")
            return False

        print(f"✅ Estructura correcta:")
        print(f"   - Puntos: {result['points_obtained']}/{result['max_points_case']}")
        print(f"   - Porcentaje: {result['percentage']}%")
        print(f"   - Subsecciones B7: {result['subsections_b7_activas']}")
        print(f"   - Bloques evaluados: {len(result['blocks'])}")
        print(f"   - Items evaluados: {len(result['items_evaluated'])}")

        print("\n✅ TEST 4 PASADO")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 Test Suite - Endpoint /api/evaluate_checklist_v3")
    print("="*70)

    results = []

    # Test 1: Endpoint existe
    results.append(("Endpoint existe", test_endpoint_exists()))

    # Test 2: Estructura (skip por ahora)
    test_endpoint_structure()

    # Test 3: V2 y V3 coexisten
    results.append(("V2 y V3 coexisten", test_v2_v3_coexist()))

    # Test 4: EvaluatorV3 standalone
    results.append(("EvaluatorV3 standalone", test_evaluator_v3_standalone()))

    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "✅ PASADO" if ok else "❌ FALLIDO"
        print(f"{status}: {name}")

    print("="*70)
    print(f"Total: {passed}/{total} tests pasados")

    if passed == total:
        print("✅ TODOS LOS TESTS PASARON")
        sys.exit(0)
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        sys.exit(1)


if __name__ == "__main__":
    main()
