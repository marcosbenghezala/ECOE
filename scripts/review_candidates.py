"""
Script para revisar candidatos a nuevos ítems
Interfaz CLI para profesores que permite aprobar/rechazar candidatos
"""
import sys
import os
import json

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR
    OPENAI_API_KEY = settings.OPENAI_API_KEY
except:
    from dotenv import load_dotenv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(script_dir)
    env_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
    load_dotenv(env_path)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

from simulador.learning_system import LearningSystem

# Paths
MASTER_ITEMS_PATH = os.path.join(BASE_DIR, 'data', 'master_items.json')
EMBEDDINGS_PATH = os.path.join(BASE_DIR, 'data', 'master_items_embeddings.npz')
INDEX_PATH = os.path.join(BASE_DIR, 'data', 'master_items_index.json')

def display_candidate(candidato: dict, index: int, total: int):
    """Muestra un candidato en formato legible"""
    print("\n" + "="*70)
    print(f"CANDIDATO {index}/{total} - ID: {candidato['id']}")
    print("="*70)
    print(f"\n📝 TEXTO: {candidato['texto']}")
    print(f"\n📊 OCURRENCIAS: {candidato['ocurrencias']} veces")
    print(f"📅 Primera vez: {candidato['fecha_primera_ocurrencia'][:10]}")

    # Mostrar análisis de similitud
    analisis = candidato['analisis']
    print(f"\n🔍 ANÁLISIS DE SIMILITUD:")
    print(f"   - Similitud con ítem más cercano: {analisis['similitud']:.2%}")
    print(f"   - Ítem más similar: {analisis['item_mas_similar']['texto']}")
    print(f"   - Confianza de novedad: {analisis['confianza'].upper()}")
    print(f"   - ¿Es nuevo?: {'✅ SÍ' if analisis['es_nuevo'] else '❌ NO (muy similar a existente)'}")

    # Mostrar casos donde apareció
    print(f"\n📋 CASOS DONDE APARECIÓ:")
    for i, caso in enumerate(candidato['casos'][:3], 1):  # Mostrar max 3
        print(f"   {i}. Caso: {caso['caso_id']} - {caso['fecha'][:10]}")
        if caso.get('contexto'):
            print(f"      Contexto: {caso['contexto']}")

    if len(candidato['casos']) > 3:
        print(f"   ... y {len(candidato['casos']) - 3} más")

def review_candidates_interactive():
    """Interfaz interactiva para revisar candidatos"""

    # Verificar API key
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY no encontrada")
        print("Por favor, configura tu API key en el archivo .env")
        sys.exit(1)

    print("🎓 SISTEMA DE REVISIÓN DE CANDIDATOS A NUEVOS ÍTEMS")
    print("="*70)

    # Inicializar sistema de aprendizaje
    learning_system = LearningSystem(
        master_items_path=MASTER_ITEMS_PATH,
        embeddings_path=EMBEDDINGS_PATH,
        index_path=INDEX_PATH,
        api_key=OPENAI_API_KEY
    )

    # Obtener estadísticas
    stats = learning_system.get_statistics()
    print(f"\n📊 ESTADÍSTICAS DEL SISTEMA:")
    print(f"   - Candidatos pendientes: {stats['total_candidatos_pendientes']}")
    print(f"   - Listos para revisión: {stats['candidatos_listos_para_revision']}")
    print(f"   - Aprobados históricos: {stats['total_aprobados']}")
    print(f"   - Rechazados históricos: {stats['total_rechazados']}")

    # Obtener candidatos para revisión
    candidatos = learning_system.get_candidates_for_review()

    if not candidatos:
        print("\n✅ No hay candidatos pendientes de revisión")
        print(f"   (Se requieren mínimo {stats['configuracion']['minimo_casos_para_aprender']} ocurrencias)")
        return

    print(f"\n🔍 Revisando {len(candidatos)} candidatos...")

    # Revisar cada candidato
    for i, candidato in enumerate(candidatos, 1):
        display_candidate(candidato, i, len(candidatos))

        # Solicitar decisión
        print("\n" + "-"*70)
        print("OPCIONES:")
        print("  [a] Aprobar - Añadir al checklist maestro")
        print("  [r] Rechazar - No es un ítem válido")
        print("  [s] Saltar - Revisar después")
        print("  [q] Salir")

        while True:
            decision = input("\n¿Qué deseas hacer? [a/r/s/q]: ").strip().lower()

            if decision == 'q':
                print("\n👋 Saliendo del sistema de revisión...")
                return

            elif decision == 's':
                print("⏭️  Candidato omitido")
                break

            elif decision == 'r':
                razon = input("Razón del rechazo: ").strip()
                validador = input("Tu nombre: ").strip()

                result = learning_system.reject_candidate(
                    candidato['id'],
                    razon,
                    validador
                )
                print(f"✅ {result['mensaje']}")
                break

            elif decision == 'a':
                print("\n📋 METADATOS DEL NUEVO ÍTEM:")
                print("Completa la siguiente información:\n")

                # Solicitar metadatos
                id_sugerido = input(f"ID (ej: SIST_XX): ").strip()
                descripcion = input("Descripción breve: ").strip()
                keywords = input("Keywords (separadas por comas): ").strip().split(',')
                keywords = [k.strip() for k in keywords if k.strip()]
                sintomas = input("Síntomas trigger (separados por comas, opcional): ").strip()
                sintomas_trigger = [s.strip() for s in sintomas.split(',') if s.strip()] if sintomas else []

                peso = input("Peso (1-3) [1]: ").strip() or "1"
                critico = input("¿Es crítico? (s/n) [n]: ").strip().lower() == 's'
                nivel = input("Nivel (basico/intermedio/avanzado) [basico]: ").strip() or "basico"
                tipo_opciones = ["cardinal", "comunicacion", "diagnostico_diferencial", "contexto"]
                print(f"Tipo: {', '.join(tipo_opciones)}")
                tipo = input("Tipo [cardinal]: ").strip() or "cardinal"

                validador = input("\nTu nombre: ").strip()

                item_metadata = {
                    'id': id_sugerido,
                    'descripcion': descripcion,
                    'keywords': keywords,
                    'sintomas_trigger': sintomas_trigger,
                    'peso': int(peso),
                    'critico': critico,
                    'nivel': nivel,
                    'tipo': tipo
                }

                result = learning_system.approve_candidate(
                    candidato['id'],
                    item_metadata,
                    validador
                )
                print(f"\n✅ {result['mensaje']}")
                print(f"   Nuevo ítem ID: {result['nuevo_item']['id']}")
                break

            else:
                print("❌ Opción inválida. Usa: a, r, s, o q")

    print("\n" + "="*70)
    print("✅ REVISIÓN COMPLETADA")
    print("="*70)

    # Mostrar estadísticas actualizadas
    stats = learning_system.get_statistics()
    print(f"\n📊 ESTADÍSTICAS ACTUALIZADAS:")
    print(f"   - Candidatos pendientes: {stats['total_candidatos_pendientes']}")
    print(f"   - Aprobados total: {stats['total_aprobados']}")
    print(f"   - Rechazados total: {stats['total_rechazados']}")

def show_statistics():
    """Muestra solo las estadísticas sin revisar"""
    learning_system = LearningSystem(
        master_items_path=MASTER_ITEMS_PATH,
        embeddings_path=EMBEDDINGS_PATH,
        index_path=INDEX_PATH,
        api_key=OPENAI_API_KEY
    )

    stats = learning_system.get_statistics()

    print("\n📊 ESTADÍSTICAS DEL SISTEMA DE APRENDIZAJE")
    print("="*70)
    print(f"Candidatos pendientes: {stats['total_candidatos_pendientes']}")
    print(f"Listos para revisión: {stats['candidatos_listos_para_revision']}")
    print(f"Aprobados (histórico): {stats['total_aprobados']}")
    print(f"Rechazados (histórico): {stats['total_rechazados']}")
    print("\nConfiguración:")
    print(f"  - Umbral similitud mínimo: {stats['configuracion']['umbral_similitud_minimo']}")
    print(f"  - Mínimo ocurrencias: {stats['configuracion']['minimo_casos_para_aprender']}")
    print(f"  - Requiere validación humana: {stats['configuracion']['requiere_validacion_humana']}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--stats':
        show_statistics()
    else:
        review_candidates_interactive()
