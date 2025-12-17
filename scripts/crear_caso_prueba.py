#!/usr/bin/env python3
"""
Script para crear un caso de prueba para testing del sistema ECOE
Genera un caso clínico simple pero completo
"""

import os
import json
import pickle
import sys
from pathlib import Path
from datetime import datetime

# Añadir path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

CASOS_DIR = BASE_DIR / 'casos_procesados'

def crear_caso_prueba():
    """Crea un caso de prueba para testing"""

    caso_prueba = {
        'id': 'caso_prueba_001',
        'titulo': 'Dolor Torácico Agudo - Caso de Prueba',
        'especialidad': 'Cardiología',
        'dificultad': 'Intermedio',
        'duracion_estimada': 15,

        'motivo_consulta': 'Dolor torácico de 2 horas de evolución',

        'informacion_paciente': {
            'nombre': 'Juan Pérez García',
            'edad': 55,
            'genero': 'masculino',
            'ocupacion': 'Profesor'
        },

        'contexto_generado': '''El paciente es un hombre de 55 años que acude a urgencias refiriendo dolor torácico de 2 horas de evolución.

HISTORIA CLÍNICA:
- Dolor retroesternal opresivo, con irradiación a brazo izquierdo y mandíbula
- Intensidad 8/10
- Asociado a sudoración profusa y náuseas
- Sin alivio con reposo

ANTECEDENTES:
- Hipertensión arterial en tratamiento
- Dislipidemia
- Fumador activo (20 cigarrillos/día desde hace 30 años)
- Padre fallecido por infarto agudo de miocardio a los 58 años

EXPLORACIÓN FÍSICA:
- TA: 160/95 mmHg
- FC: 105 lpm
- SatO2: 96% basal
- Sudoroso, ansioso
- Auscultación cardíaca: rítmico, sin soplos
- Auscultación pulmonar: murmullo vesicular conservado

SITUACIÓN ACTUAL:
El paciente está preocupado porque el dolor no cede. Refiere que "siente que le aprietan el pecho" y tiene miedo de que sea un infarto como el de su padre.''',

        'personalidad_generada': '''Eres un paciente colaborador pero ansioso por la situación.

ACTITUD:
- Respondes las preguntas de forma clara pero breve debido al malestar
- Muestras preocupación evidente
- Haces preguntas sobre si es grave
- Mencionas espontáneamente el antecedente familiar de tu padre

FORMA DE HABLAR:
- Frases cortas debido a la incomodidad
- Expresas el dolor con palabras como "me aprieta", "me pesa"
- Interrumpes ocasionalmente para decir que el dolor continúa

EXPECTATIVAS (ICE):
- Ideas: Crees que puede ser un infarto
- Concerns: Miedo a morir como tu padre
- Expectations: Que te hagan pruebas urgentes (ECG, analítica)''',

        'sintomas_principales': [
            'dolor torácico',
            'dolor retroesternal',
            'dolor opresivo',
            'irradiación a brazo',
            'sudoración',
            'náuseas',
            'disnea'
        ],

        'items_activos': [
            # Bloques universales (SIEMPRE activos)
            'presentacion',
            'motivo_consulta',
            'caracteristicas_dolor',
            'localizacion_dolor',
            'irradiacion',
            'intensidad_dolor',
            'factores_alivio',
            'factores_empeoramiento',
            'sintomas_asociados',
            'tiempo_evolucion',
            'antecedentes_personales',
            'antecedentes_familiares',
            'medicacion_actual',
            'alergias',
            'habitos_toxicos',
            'ice_ideas',
            'ice_concerns',
            'ice_expectations',
            'empatia',
            'comunicacion_clara',

            # Items específicos de cardiología activados por síntomas
            'factores_riesgo_cardiovascular',
            'claudicacion',
            'ortopnea',
            'disnea_paroxistica_nocturna',
            'palpitaciones',
            'sincope',
            'edemas'
        ],

        'multimedia': [
            {
                'tipo': 'ECG',
                'descripcion': 'ECG de 12 derivaciones',
                'url': '#',  # Placeholder
                'hallazgos': 'Elevación del segmento ST en derivaciones precordiales'
            }
        ],

        'instrucciones': '''Este es un caso de simulación de anamnesis completa.

OBJETIVOS:
1. Realizar anamnesis completa siguiendo el método SOCRATES para el dolor
2. Explorar Ideas, Concerns y Expectations (ICE) del paciente
3. Identificar factores de riesgo cardiovascular
4. Mantener comunicación empática

DURACIÓN: 15 minutos

EVALUACIÓN:
Serás evaluado en base al checklist maestro con activación por síntomas.''',

        'created_at': datetime.now().isoformat(),
        'version': '2.0'
    }

    return caso_prueba


def main():
    """Función principal"""
    print("="*60)
    print("🏥 CREANDO CASO DE PRUEBA PARA ECOE")
    print("="*60)

    # Crear directorio de casos si no existe
    CASOS_DIR.mkdir(parents=True, exist_ok=True)

    # Crear caso
    print("\n📝 Generando caso de prueba...")
    caso = crear_caso_prueba()

    # Guardar como .bin (pickle)
    output_path = CASOS_DIR / f"{caso['id']}.bin"

    with open(output_path, 'wb') as f:
        pickle.dump(caso, f)

    print(f"✅ Caso guardado: {output_path}")

    # También guardar como JSON para revisión
    json_path = CASOS_DIR / f"{caso['id']}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(caso, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON guardado: {json_path}")

    # Resumen
    print("\n" + "="*60)
    print("✅ CASO DE PRUEBA CREADO")
    print("="*60)
    print(f"ID: {caso['id']}")
    print(f"Título: {caso['titulo']}")
    print(f"Especialidad: {caso['especialidad']}")
    print(f"Dificultad: {caso['dificultad']}")
    print(f"Síntomas principales: {len(caso['sintomas_principales'])}")
    print(f"Items activos: {len(caso['items_activos'])}")
    print("\n🎯 Caso listo para testing en el dashboard")


if __name__ == '__main__':
    main()
