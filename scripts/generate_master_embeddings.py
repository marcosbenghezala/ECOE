"""
Script para generar embeddings del master_items.json
Genera embeddings semánticos para cada ítem del checklist maestro
Permite comparación y aprendizaje automático del sistema
"""
import json
import numpy as np
import os
import sys
from openai import OpenAI
from typing import List, Dict

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OPENAI_API_KEY = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None
except:
    # Determinar BASE_DIR correctamente
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(script_dir)  # TO_GITHUB directory

    # Cargar .env desde la raíz del proyecto (un nivel arriba de TO_GITHUB)
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
    load_dotenv(env_path)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configuración
EMBEDDING_MODEL = "text-embedding-3-small"
MASTER_ITEMS_PATH = os.path.join(BASE_DIR, 'data', 'master_items.json')
EMBEDDINGS_OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'master_items_embeddings.npz')
ITEM_INDEX_PATH = os.path.join(BASE_DIR, 'data', 'master_items_index.json')

def load_master_items(filepath: str) -> Dict:
    """Carga el archivo master_items.json"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_items_for_embedding(master_data: Dict) -> tuple[List[Dict], List[str]]:
    """
    Extrae todos los ítems y sus textos para generar embeddings.

    Returns:
        items_metadata: Lista de metadatos de cada ítem (id, bloque, texto, etc.)
        texts_to_embed: Lista de textos combinados para generar embeddings
    """
    items_metadata = []
    texts_to_embed = []

    # Procesar bloques universales (es un diccionario)
    bloques_universales = master_data.get('bloques_universales', {})
    for bloque_key, bloque_data in bloques_universales.items():
        bloque_nombre = bloque_data['nombre']
        for item in bloque_data['items']:
            # Crear texto completo para embedding (combina texto + descripción + keywords)
            texto_completo = f"{item['texto']}. {item.get('descripcion', '')}. "
            texto_completo += f"Keywords: {', '.join(item.get('keywords', []))}"

            items_metadata.append({
                'id': item['id'],
                'bloque': bloque_nombre,
                'tipo_bloque': 'universal',
                'texto': item['texto'],
                'sistema': None
            })
            texts_to_embed.append(texto_completo)

    # Procesar items por sistemas (es un diccionario)
    items_por_sistemas = master_data.get('items_por_sistemas', {})
    for sistema_key, sistema_data in items_por_sistemas.items():
        sistema_nombre = sistema_data['nombre']
        for item in sistema_data['items']:
            # Crear texto completo para embedding
            texto_completo = f"{item['texto']}. {item.get('descripcion', '')}. "
            texto_completo += f"Keywords: {', '.join(item.get('keywords', []))}. "
            texto_completo += f"Síntomas: {', '.join(item.get('sintomas_trigger', []))}"

            items_metadata.append({
                'id': item['id'],
                'bloque': None,
                'tipo_bloque': 'sistema',
                'texto': item['texto'],
                'sistema': sistema_nombre
            })
            texts_to_embed.append(texto_completo)

    return items_metadata, texts_to_embed

def generate_embeddings(texts: List[str], api_key: str, batch_size: int = 100) -> np.ndarray:
    """
    Genera embeddings para una lista de textos usando OpenAI API.
    Procesa en batches para evitar límites de rate.
    """
    client = OpenAI(api_key=api_key)
    all_embeddings = []

    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1

        print(f"📊 Procesando batch {batch_num}/{total_batches} ({len(batch)} items)...")

        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch
            )

            # Extraer embeddings de la respuesta
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        except Exception as e:
            print(f"❌ Error en batch {batch_num}: {str(e)}")
            raise

    return np.array(all_embeddings)

def save_embeddings(embeddings: np.ndarray, metadata: List[Dict],
                    embeddings_path: str, index_path: str):
    """
    Guarda los embeddings y el índice de metadatos.

    Args:
        embeddings: Array numpy con los embeddings
        metadata: Lista de metadatos de cada ítem
        embeddings_path: Ruta donde guardar embeddings (.npz)
        index_path: Ruta donde guardar índice (.json)
    """
    # Guardar embeddings como archivo .npz (comprimido)
    np.savez_compressed(embeddings_path, embeddings=embeddings)

    # Guardar índice de metadatos
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Embeddings guardados en: {embeddings_path}")
    print(f"✅ Índice guardado en: {index_path}")

def main():
    """Función principal para generar embeddings del master"""

    # Verificar API key
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY no encontrada")
        print("Por favor, configura tu API key en el archivo .env")
        sys.exit(1)

    print("🚀 Iniciando generación de embeddings del checklist maestro...")
    print(f"📁 Leyendo master_items.json desde: {MASTER_ITEMS_PATH}")

    # Cargar master items
    if not os.path.exists(MASTER_ITEMS_PATH):
        print(f"❌ Error: No se encuentra {MASTER_ITEMS_PATH}")
        sys.exit(1)

    master_data = load_master_items(MASTER_ITEMS_PATH)

    # Extraer items y textos
    print("📝 Extrayendo ítems para embeddings...")
    items_metadata, texts_to_embed = extract_items_for_embedding(master_data)

    print(f"✅ Total de ítems a procesar: {len(items_metadata)}")
    print(f"   - Bloques universales: {len([m for m in items_metadata if m['tipo_bloque'] == 'universal'])}")
    print(f"   - Items por sistemas: {len([m for m in items_metadata if m['tipo_bloque'] == 'sistema'])}")

    # Generar embeddings
    print(f"\n🔄 Generando embeddings con modelo {EMBEDDING_MODEL}...")
    embeddings = generate_embeddings(texts_to_embed, OPENAI_API_KEY)

    print(f"✅ Embeddings generados: {embeddings.shape}")
    print(f"   - Dimensiones: {embeddings.shape[1]}")

    # Guardar resultados
    print("\n💾 Guardando embeddings e índice...")
    save_embeddings(embeddings, items_metadata, EMBEDDINGS_OUTPUT_PATH, ITEM_INDEX_PATH)

    # Estadísticas finales
    print("\n" + "="*60)
    print("✅ GENERACIÓN DE EMBEDDINGS COMPLETADA")
    print("="*60)
    print(f"Total ítems procesados: {len(items_metadata)}")
    print(f"Dimensión de embeddings: {embeddings.shape[1]}")
    print(f"Tamaño del archivo: {os.path.getsize(EMBEDDINGS_OUTPUT_PATH) / 1024:.2f} KB")
    print("\nArchivos generados:")
    print(f"  - {EMBEDDINGS_OUTPUT_PATH}")
    print(f"  - {ITEM_INDEX_PATH}")
    print("\n🎯 Sistema listo para aprendizaje automático y evaluación semántica")

if __name__ == "__main__":
    main()
