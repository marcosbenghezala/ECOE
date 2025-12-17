"""
Script para codificar casos .bin a JSON en base64 para GitHub
Sigue el formato del ejemplo del profesor de bioestadística
"""
import pickle
import base64
import json
import os
import sys

# Añadir el directorio padre al path para importar config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def encode_case_to_github(bin_filepath, output_dir=None):
    """
    Convierte un archivo .bin a JSON codificado en base64 para GitHub.
    Sigue el mismo formato que el ejemplo del profesor:
    https://raw.githubusercontent.com/ia4legos/Statistics/main/autoeval/auto_20_1.json
    
    Args:
        bin_filepath: Ruta al archivo .bin
        output_dir: Directorio donde guardar el .json (default: casos/)
    
    Returns:
        json_filepath: Ruta al archivo .json creado
    """
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, 'casos')
    
    # Crear directorio si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Leer archivo .bin
    with open(bin_filepath, 'rb') as f:
        case_data = pickle.load(f)
    
    # Serializar a pickle y codificar a base64
    pickled_data = pickle.dumps(case_data)
    encoded_data = base64.b64encode(pickled_data).decode('utf-8')
    
    # Guardar como JSON (solo el string codificado, como en el ejemplo del profesor)
    json_filename = os.path.basename(bin_filepath).replace('.bin', '.json')
    json_filepath = os.path.join(output_dir, json_filename)
    
    # Guardar solo el string codificado (formato simple)
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(encoded_data, f)
    
    print(f"✅ Caso codificado guardado en: {json_filepath}")
    return json_filepath

if __name__ == "__main__":
    if len(sys.argv) > 1:
        bin_file = sys.argv[1]
        if not os.path.exists(bin_file):
            print(f"❌ Error: Archivo no encontrado: {bin_file}")
            sys.exit(1)
        encode_case_to_github(bin_file)
    else:
        print("Uso: python encode_case_to_github.py <ruta_al_archivo.bin>")
        print("Ejemplo: python encode_case_to_github.py casos/Angina_estable_001.bin")

