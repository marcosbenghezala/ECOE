"""
Pipeline completo para profesores: Forms → Sheets → GitHub
Ejecuta todo el flujo de procesamiento de casos automáticamente
"""
import os
import sys

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fetch_from_sheets import get_new_cases, mark_as_processed
from scripts.procesador_casos_v2 import CaseProcessorV2
from scripts.upload_to_github import upload_cases_to_github

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

MASTER_ITEMS_PATH = os.path.join(BASE_DIR, 'data', 'master_items.json')


def run_full_pipeline(auto_upload: bool = True):
    """
    Ejecuta el pipeline completo de procesamiento.

    Args:
        auto_upload: Si debe subir automáticamente a GitHub

    Returns:
        Número de casos procesados
    """
    print("\n" + "🚀 PIPELINE COMPLETO DE PROCESAMIENTO DE CASOS " + "\n")
    print("="*70)
    print("PASOS:")
    print("  1. Obtener casos nuevos desde Google Sheets")
    print("  2. Procesar casos con GPT-4 (contexto, items, etc.)")
    print("  3. Generar archivos .bin y .json (base64)")
    print("  4. Subir a GitHub automáticamente")
    print("="*70 + "\n")

    # PASO 1: Obtener casos desde Sheets
    print("📊 PASO 1: Obtener casos desde Google Sheets")
    print("-"*70)
    try:
        casos = get_new_cases()
    except Exception as e:
        print(f"❌ Error obteniendo casos: {e}")
        import traceback
        traceback.print_exc()
        return 0

    if not casos:
        print("✅ No hay casos nuevos para procesar\n")
        return 0

    print(f"✅ {len(casos)} casos nuevos encontrados\n")

    # PASO 2: Procesar casos
    print("🔄 PASO 2: Procesar casos con GPT-4")
    print("-"*70)

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY no encontrada")
        return 0

    processor = CaseProcessorV2(
        api_key=OPENAI_API_KEY,
        master_items_path=MASTER_ITEMS_PATH
    )

    casos_procesados = 0
    errores = []

    for i, caso in enumerate(casos, 1):
        print(f"\n[{i}/{len(casos)}] Procesando: {caso['titulo']}")

        try:
            filepath = processor.process_case(caso)
            mark_as_processed(caso)
            casos_procesados += 1

        except Exception as e:
            print(f"❌ Error procesando '{caso['titulo']}': {e}")
            errores.append({
                'caso': caso['titulo'],
                'error': str(e)
            })

    print("\n" + "="*70)
    print(f"✅ PROCESAMIENTO COMPLETADO: {casos_procesados}/{len(casos)} exitosos")
    if errores:
        print(f"⚠️  {len(errores)} errores:")
        for err in errores:
            print(f"   - {err['caso']}: {err['error']}")
    print("="*70 + "\n")

    # PASO 3: Subir a GitHub
    if auto_upload and casos_procesados > 0:
        print("⬆️  PASO 3: Subir a GitHub")
        print("-"*70)

        commit_msg = f"""Nuevos casos ECOE procesados ({casos_procesados})

Casos añadidos:
{chr(10).join(['- ' + c['titulo'] for c in casos[:5]])}
{"..." if len(casos) > 5 else ""}

🤖 Generated with Claude Code
"""

        try:
            success = upload_cases_to_github(commit_message=commit_msg)
            if success:
                print("\n✅ Pipeline completado exitosamente!")
            else:
                print("\n⚠️  Pipeline completado con advertencias (revisar git)")
        except Exception as e:
            print(f"\n❌ Error subiendo a GitHub: {e}")
            print("Los casos están procesados localmente en casos/")

    print("\n" + "="*70)
    print(f"📊 RESUMEN FINAL")
    print("="*70)
    print(f"Casos procesados: {casos_procesados}")
    print(f"Ubicación: TO_GITHUB/casos/")
    if auto_upload:
        print(f"GitHub: https://github.com/{os.getenv('GITHUB_USERNAME', 'usuario')}/{os.getenv('GITHUB_REPO', 'ECOE')}/tree/main/casos")
    print("="*70 + "\n")

    return casos_procesados


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Pipeline completo: Google Forms → Procesamiento → GitHub'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='No subir automáticamente a GitHub'
    )

    args = parser.parse_args()

    casos_procesados = run_full_pipeline(auto_upload=not args.no_upload)

    if casos_procesados == 0:
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
