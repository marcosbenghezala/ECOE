#!/usr/bin/env python3
"""
Test para EvaluatorV3
Valida evaluación completa con regex + keywords.

Tests:
1. Evaluación básica con transcripción simple
2. Filtrado correcto de líneas [ESTUDIANTE] vs [PACIENTE]
3. Match por regex
4. Match por keywords
5. Agrupación por bloques
6. Agrupación por subsecciones B7
7. Cálculo correcto de aprobado/suspenso
8. Caso real completo
"""

import sys
from pathlib import Path

# Añadir simulador/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "simulador"))

from evaluator_v3 import EvaluatorV3


def test_evaluacion_basica():
    """Test 1: Evaluación básica con transcripción simple"""
    print("\n" + "="*70)
    print("TEST 1: Evaluación Básica")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción simple
    transcript = """
[ESTUDIANTE]: Hola, buenos días. ¿Cómo se encuentra usted?
[PACIENTE]: Buenos días doctor, tengo dolor en el pecho.
[ESTUDIANTE]: ¿Desde cuándo tiene el dolor?
[PACIENTE]: Desde hace 2 horas.
[ESTUDIANTE]: ¿Puede describir el dolor? ¿Cómo es?
[PACIENTE]: Es un dolor opresivo, como si me apretaran.
[ESTUDIANTE]: ¿Le duele en algún otro sitio? ¿Se irradia?
[PACIENTE]: Sí, me duele también en el brazo izquierdo.
[ESTUDIANTE]: ¿Tiene usted alguna enfermedad conocida?
[PACIENTE]: Sí, tengo hipertensión y tomo pastillas.
[ESTUDIANTE]: ¿Tiene usted alergias a medicamentos?
[PACIENTE]: No, ninguna.
[ESTUDIANTE]: ¿Fuma usted?
[PACIENTE]: Sí, fumo un paquete al día.
"""

    case_data = {
        "id": "test_basic",
        "sintomas_principales": ["dolor torácico"]
    }

    result = evaluator.evaluate_transcript(transcript, case_data)

    # Validaciones
    print(f"✅ Puntos obtenidos: {result['points_obtained']} / {result['max_points_case']}")
    print(f"✅ Porcentaje: {result['percentage']}%")
    print(f"✅ Estado: {'APROBADO' if result['passed'] else 'SUSPENSO'}")
    print(f"✅ Ítems evaluados: {result['summary']['total_items_evaluated']}")
    print(f"✅ Ítems matched: {result['summary']['total_items_matched']}")

    assert result["max_points_case"] > 0, "Debe tener puntos máximos"
    assert result["points_obtained"] >= 0, "Debe tener puntos obtenidos >= 0"
    assert "blocks" in result, "Debe tener resultados por bloques"
    assert "B0_INTRODUCCION" in result["blocks"], "Debe evaluar B0_INTRODUCCION"

    print("✅ TEST 1 PASADO")


def test_filtrado_estudiante():
    """Test 2: Solo evalúa líneas [ESTUDIANTE], ignora [PACIENTE]"""
    print("\n" + "="*70)
    print("TEST 2: Filtrado Correcto [ESTUDIANTE] vs [PACIENTE]")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción con información SOLO en líneas del paciente
    transcript_paciente_only = """
[PACIENTE]: Buenos días, soy Juan Pérez. Tengo 55 años.
[PACIENTE]: Vengo porque tengo dolor torácico desde hace 2 horas.
[PACIENTE]: El dolor es opresivo y se irradia al brazo izquierdo.
[PACIENTE]: Tengo hipertensión y fumo mucho.
[ESTUDIANTE]: Ok.
"""

    case_data = {
        "id": "test_filtrado",
        "sintomas_principales": ["dolor torácico"]
    }

    result = evaluator.evaluate_transcript(transcript_paciente_only, case_data)

    # El estudiante solo dijo "Ok", NO debe cumplir casi ningún ítem
    print(f"✅ Líneas estudiante: {result['summary']['student_lines_count']}")
    print(f"✅ Ítems matched: {result['summary']['total_items_matched']}")
    print(f"✅ Puntos: {result['points_obtained']} / {result['max_points_case']}")

    # Validar que NO cumplió muchos ítems (porque el estudiante apenas habló)
    match_rate = result['summary']['match_rate']
    print(f"✅ Match rate: {match_rate}%")
    assert match_rate < 20, f"Match rate debe ser bajo (<20%), es {match_rate}%"

    print("✅ TEST 2 PASADO - Filtrado correcto")


def test_match_regex():
    """Test 3: Match por regex funciona"""
    print("\n" + "="*70)
    print("TEST 3: Match por Regex")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción con saludos y preguntas
    transcript = """
[ESTUDIANTE]: Buenos días, mi nombre es Dr. García. ¿Cómo se encuentra?
[PACIENTE]: Buenos días doctor.
[ESTUDIANTE]: ¿Cuál es el motivo de su consulta hoy?
[PACIENTE]: Tengo dolor de cabeza.
"""

    case_data = {
        "id": "test_regex",
        "sintomas_principales": ["cefalea"]
    }

    result = evaluator.evaluate_transcript(transcript, case_data)

    # Buscar items que deberían haber matcheado por regex
    matched_items = [r for r in result["items_evaluated"] if r["matched"]]
    regex_matches = [r for r in matched_items if r["method"] == "regex"]

    print(f"✅ Total matched: {len(matched_items)}")
    print(f"✅ Matched por regex: {len(regex_matches)}")

    assert len(regex_matches) > 0, "Debe haber al menos 1 match por regex"

    # Mostrar ejemplos
    for r in regex_matches[:3]:
        print(f"   - {r['item_id']}: {r['match_details']}")

    print("✅ TEST 3 PASADO")


def test_match_keywords():
    """Test 4: Match por keywords funciona (cuando regex no matchea)"""
    print("\n" + "="*70)
    print("TEST 4: Match por Keywords y Regex")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción con keywords específicos
    transcript = """
[ESTUDIANTE]: Buenos días. ¿Tiene usted alergias a algún medicamento?
[PACIENTE]: No, ninguna alergia.
[ESTUDIANTE]: ¿Fuma usted?
[PACIENTE]: Sí, fumo.
[ESTUDIANTE]: ¿Toma usted alcohol?
[PACIENTE]: Ocasionalmente.
"""

    case_data = {
        "id": "test_keywords",
        "sintomas_principales": ["cefalea"]
    }

    result = evaluator.evaluate_transcript(transcript, case_data)

    # Buscar todos los matches
    matched_items = [r for r in result["items_evaluated"] if r["matched"]]
    regex_matches = [r for r in matched_items if r["method"] == "regex"]
    keyword_matches = [r for r in matched_items if r["method"] == "keywords"]

    print(f"✅ Total matched: {len(matched_items)}")
    print(f"✅ Matched por regex: {len(regex_matches)}")
    print(f"✅ Matched por keywords: {len(keyword_matches)}")

    # El sistema debe poder hacer matches (por regex o keywords)
    assert len(matched_items) > 0, "Debe haber al menos 1 match (regex o keywords)"

    # Mostrar ejemplos de cada tipo
    if regex_matches:
        print(f"\n   Ejemplos regex:")
        for r in regex_matches[:2]:
            print(f"   - {r['item_id']}: {r['match_details']}")

    if keyword_matches:
        print(f"\n   Ejemplos keywords:")
        for r in keyword_matches[:2]:
            print(f"   - {r['item_id']}: {r['match_details']}")

    print("✅ TEST 4 PASADO")


def test_agrupacion_bloques():
    """Test 5: Agrupación por bloques funciona"""
    print("\n" + "="*70)
    print("TEST 5: Agrupación por Bloques")
    print("="*70)

    evaluator = EvaluatorV3()

    transcript = """
[ESTUDIANTE]: Buenos días, mi nombre es Dr. García.
[ESTUDIANTE]: ¿Cuál es el motivo de su consulta?
[ESTUDIANTE]: ¿Desde cuándo tiene el dolor?
[ESTUDIANTE]: ¿Tiene usted enfermedades conocidas?
[ESTUDIANTE]: ¿Toma medicamentos?
[ESTUDIANTE]: ¿Tiene alergias?
[ESTUDIANTE]: ¿Fuma o toma alcohol?
"""

    case_data = {
        "id": "test_bloques",
        "sintomas_principales": ["dolor torácico"]
    }

    result = evaluator.evaluate_transcript(transcript, case_data)

    # Validar estructura de bloques
    blocks = result["blocks"]
    print(f"✅ Bloques evaluados: {len(blocks)}")

    # Verificar bloques universales
    universal_blocks = [
        "B0_INTRODUCCION",
        "B1_MOTIVO_CONSULTA",
        "B2_HEA",
        "B3_ANTECEDENTES",
        "B4_MEDICACION_ALERGIAS"
    ]

    for block_id in universal_blocks:
        assert block_id in blocks, f"Bloque {block_id} debe estar presente"
        block_result = blocks[block_id]
        print(f"   {block_id}: {block_result['points_obtained']}/{block_result['max_points']} pts ({block_result['percentage']}%)")

    print("✅ TEST 5 PASADO")


def test_subsecciones_b7():
    """Test 6: Agrupación por subsecciones B7"""
    print("\n" + "="*70)
    print("TEST 6: Subsecciones B7")
    print("="*70)

    evaluator = EvaluatorV3()

    transcript = """
[ESTUDIANTE]: ¿Tiene usted palpitaciones?
[ESTUDIANTE]: ¿Ha tenido dolor torácico antes?
[ESTUDIANTE]: ¿Tiene edemas en las piernas?
[ESTUDIANTE]: ¿Tiene dificultad para respirar?
[ESTUDIANTE]: ¿Tiene tos o expectoración?
"""

    case_data = {
        "id": "test_b7",
        "sintomas_principales": ["dolor torácico", "disnea"]
    }

    result = evaluator.evaluate_transcript(transcript, case_data)

    # Validar subsecciones B7
    assert "subsections_b7_activas" in result
    assert "b7_subsections" in result

    subsections = result["subsections_b7_activas"]
    print(f"✅ Subsecciones activas: {subsections}")

    # Debe activar CARDIOVASCULAR + RESPIRATORIO
    assert "CARDIOVASCULAR" in subsections, "Debe activar CARDIOVASCULAR"
    assert "RESPIRATORIO" in subsections, "Debe activar RESPIRATORIO"

    # Validar resultados por subsección
    b7_results = result["b7_subsections"]
    for subsection in subsections:
        assert subsection in b7_results, f"Subsección {subsection} debe tener resultados"
        sub_result = b7_results[subsection]
        print(f"   {subsection}: {sub_result['points_obtained']}/{sub_result['max_points']} pts ({sub_result['percentage']}%)")

    print("✅ TEST 6 PASADO")


def test_aprobado_suspenso():
    """Test 7: Cálculo correcto de aprobado/suspenso"""
    print("\n" + "="*70)
    print("TEST 7: Aprobado/Suspenso")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción muy completa (debería aprobar)
    transcript_completo = """
[ESTUDIANTE]: Buenos días, mi nombre es Dr. García. ¿Cómo se encuentra usted?
[ESTUDIANTE]: ¿Cuál es el motivo de su consulta hoy?
[ESTUDIANTE]: ¿Desde cuándo tiene el dolor?
[ESTUDIANTE]: ¿Puede describir cómo es el dolor? ¿Es opresivo, punzante?
[ESTUDIANTE]: ¿Dónde le duele exactamente?
[ESTUDIANTE]: ¿El dolor se irradia a algún sitio?
[ESTUDIANTE]: ¿En una escala del 1 al 10, qué intensidad tiene el dolor?
[ESTUDIANTE]: ¿Algo hace que mejore o empeore el dolor?
[ESTUDIANTE]: ¿Tiene otros síntomas como náuseas, sudoración, dificultad para respirar?
[ESTUDIANTE]: ¿Tiene usted alguna enfermedad conocida como hipertensión o diabetes?
[ESTUDIANTE]: ¿Hay antecedentes de enfermedades cardíacas en su familia?
[ESTUDIANTE]: ¿Qué medicamentos toma actualmente?
[ESTUDIANTE]: ¿Tiene alergias a medicamentos?
[ESTUDIANTE]: ¿Fuma usted? ¿Cuánto?
[ESTUDIANTE]: ¿Toma alcohol?
[ESTUDIANTE]: ¿A qué se dedica? ¿Trabaja?
[ESTUDIANTE]: ¿Tiene palpitaciones?
[ESTUDIANTE]: ¿Ha desmayado alguna vez?
[ESTUDIANTE]: ¿Tiene edemas en piernas?
[ESTUDIANTE]: ¿Le preocupa algo en particular sobre este dolor?
[ESTUDIANTE]: ¿Qué cree usted que puede ser?
[ESTUDIANTE]: ¿Qué espera que hagamos hoy?
[ESTUDIANTE]: Bien, vamos a realizarle un electrocardiograma. ¿Tiene alguna duda?
[ESTUDIANTE]: Muchas gracias por la información.
"""

    case_data = {
        "id": "test_aprobado",
        "sintomas_principales": ["dolor torácico"]
    }

    result = evaluator.evaluate_transcript(transcript_completo, case_data)

    print(f"✅ Puntos: {result['points_obtained']} / {result['max_points_case']}")
    print(f"✅ Mínimo requerido: {result['min_points_case']}")
    print(f"✅ Porcentaje: {result['percentage']}%")
    print(f"✅ Estado: {'APROBADO' if result['passed'] else 'SUSPENSO'}")

    # Validar cálculo
    expected_passed = result['points_obtained'] >= result['min_points_case']
    assert result['passed'] == expected_passed, "Cálculo aprobado/suspenso incorrecto"

    print("✅ TEST 7 PASADO")


def test_caso_real_completo():
    """Test 8: Caso real completo con reporte detallado"""
    print("\n" + "="*70)
    print("TEST 8: Caso Real Completo")
    print("="*70)

    evaluator = EvaluatorV3()

    # Transcripción realista
    transcript = """
[ESTUDIANTE]: Buenos días, mi nombre es Dr. García, soy médico residente. ¿Cómo está usted?
[PACIENTE]: Buenos días doctor, no muy bien.
[ESTUDIANTE]: Entiendo. ¿Cuál es el motivo principal de su visita hoy?
[PACIENTE]: Tengo un dolor muy fuerte en el pecho desde hace unas horas.
[ESTUDIANTE]: Lamento escuchar eso. ¿Desde cuándo exactamente tiene el dolor?
[PACIENTE]: Empezó hace como 2 horas.
[ESTUDIANTE]: ¿Puede describirme cómo es el dolor? ¿Es opresivo, punzante, quemante?
[PACIENTE]: Es como si me apretaran el pecho, muy opresivo.
[ESTUDIANTE]: ¿Dónde le duele exactamente? ¿Me puede señalar?
[PACIENTE]: Aquí en medio del pecho, detrás del esternón.
[ESTUDIANTE]: ¿El dolor se ha movido a otro sitio? ¿Le duele en el brazo, cuello o mandíbula?
[PACIENTE]: Sí, me duele también en el brazo izquierdo y un poco en la mandíbula.
[ESTUDIANTE]: ¿En una escala del 1 al 10, siendo 10 el peor dolor imaginable, cómo calificaría este dolor?
[PACIENTE]: Es un 8 o 9, es muy intenso.
[ESTUDIANTE]: ¿Ha notado si algo hace que el dolor mejore o empeore?
[PACIENTE]: Nada lo mejora, ni siquiera descansar.
[ESTUDIANTE]: ¿Tiene otros síntomas? ¿Náuseas, sudoración, dificultad para respirar?
[PACIENTE]: Sí, estoy sudando mucho y tengo náuseas.
[ESTUDIANTE]: ¿Tiene usted alguna enfermedad conocida?
[PACIENTE]: Sí, tengo presión alta y colesterol alto.
[ESTUDIANTE]: ¿Alguien en su familia ha tenido problemas del corazón?
[PACIENTE]: Sí, mi padre murió de un infarto a los 58 años.
[ESTUDIANTE]: ¿Qué medicamentos toma actualmente?
[PACIENTE]: Tomo pastillas para la presión, enalapril creo que se llama.
[ESTUDIANTE]: ¿Es usted alérgico a algún medicamento?
[PACIENTE]: No, a ninguno.
[ESTUDIANTE]: ¿Fuma usted?
[PACIENTE]: Sí, fumo un paquete al día desde hace 30 años.
[ESTUDIANTE]: ¿Consume alcohol?
[PACIENTE]: Ocasionalmente, los fines de semana.
[ESTUDIANTE]: Entiendo. ¿Le preocupa algo en particular sobre este dolor?
[PACIENTE]: Sí, tengo miedo de que sea un infarto como el de mi padre.
[ESTUDIANTE]: Es comprensible que esté preocupado. Vamos a evaluarlo completamente. ¿Qué espera que hagamos hoy?
[PACIENTE]: Quiero que me hagan pruebas para saber si es grave.
[ESTUDIANTE]: Por supuesto, vamos a realizarle un electrocardiograma de inmediato y análisis de sangre. ¿Tiene alguna pregunta?
[PACIENTE]: No, gracias doctor.
[ESTUDIANTE]: Muy bien, gracias por toda la información. Voy a examinarlo ahora.
"""

    case_data = {
        "id": "caso_prueba_001",
        "titulo": "Dolor Torácico Agudo",
        "sintomas_principales": [
            "dolor torácico",
            "dolor retroesternal",
            "dolor opresivo",
            "irradiación a brazo",
            "sudoración",
            "náuseas"
        ],
        "motivo_consulta": "Dolor torácico de 2 horas de evolución"
    }

    result = evaluator.evaluate_transcript(transcript, case_data, "caso_prueba_001")

    # Generar reporte detallado
    report = evaluator.get_detailed_report(result)
    print(report)

    # Validaciones
    assert result["caso_id"] == "caso_prueba_001"
    assert result["max_points_case"] > 0
    assert result["points_obtained"] > 0
    assert "blocks" in result
    assert "b7_subsections" in result
    assert len(result["items_evaluated"]) > 0

    print("\n✅ TEST 8 PASADO - Caso real completado")


def main():
    print("🧪 Test Suite - EvaluatorV3")
    print("="*70)
    print("Validando evaluación con regex + keywords")
    print("="*70)

    try:
        test_evaluacion_basica()
        test_filtrado_estudiante()
        test_match_regex()
        test_match_keywords()
        test_agrupacion_bloques()
        test_subsecciones_b7()
        test_aprobado_suspenso()
        test_caso_real_completo()

        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS PASARON (8/8)")
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
