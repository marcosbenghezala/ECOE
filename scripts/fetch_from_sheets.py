"""
Script para obtener casos desde Google Sheets (desde Google Forms de profesores)
Lee filas nuevas del formulario y las prepara para procesamiento
"""
import os
import sys
import json
from typing import List, Dict, Optional
from datetime import datetime

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR
except:
    from dotenv import load_dotenv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(script_dir)
    env_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
    load_dotenv(env_path)

# Importar Google Sheets API
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️ Warning: google-api-python-client no instalado")
    print("Instala con: pip install google-api-python-client google-auth")

# Configuración
CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'config/google_credentials.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# ID del Google Sheet (se debe configurar)
SHEET_ID = os.getenv('GOOGLE_SHEET_ID_PROFESORES', None)
SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Respuestas de formulario 1')

# Archivo para tracking de casos ya procesados
PROCESSED_CASES_FILE = os.path.join(BASE_DIR, 'data', 'casos_procesados.json')


def load_processed_cases() -> Dict:
    """Carga el registro de casos ya procesados"""
    if os.path.exists(PROCESSED_CASES_FILE):
        with open(PROCESSED_CASES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'version': '1.0',
        'ultima_actualizacion': datetime.now().isoformat(),
        'casos_procesados': []
    }


def save_processed_cases(data: Dict):
    """Guarda el registro de casos procesados"""
    data['ultima_actualizacion'] = datetime.now().isoformat()
    with open(PROCESSED_CASES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_credentials() -> Optional[Credentials]:
    """
    Obtiene las credenciales de Google Sheets.

    Returns:
        Credentials object o None si falla
    """
    if not GOOGLE_AVAILABLE:
        print("❌ Google API no disponible")
        return None

    creds_path = os.path.join(os.path.dirname(BASE_DIR), CREDENTIALS_PATH)

    if not os.path.exists(creds_path):
        print(f"❌ Archivo de credenciales no encontrado: {creds_path}")
        print("Descarga las credenciales desde Google Cloud Console:")
        print("https://console.cloud.google.com/apis/credentials")
        return None

    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        return creds
    except Exception as e:
        print(f"❌ Error cargando credenciales: {e}")
        return None


def fetch_sheet_data(sheet_id: str, range_name: str) -> Optional[List[List]]:
    """
    Obtiene datos de un Google Sheet.

    Args:
        sheet_id: ID del Google Sheet
        range_name: Rango a leer (ej: 'Sheet1!A1:Z')

    Returns:
        Lista de filas (cada fila es una lista de valores)
    """
    creds = get_credentials()
    if not creds:
        return None

    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        return values

    except Exception as e:
        print(f"❌ Error leyendo Google Sheet: {e}")
        return None


def parse_form_response(row: List, headers: List) -> Dict:
    """
    Parsea una fila del formulario de Google Forms.

    Args:
        row: Fila de datos
        headers: Cabeceras de las columnas

    Returns:
        Diccionario con los datos del caso
    """
    # Crear diccionario con headers como keys
    data = {}
    for i, header in enumerate(headers):
        data[header] = row[i] if i < len(row) else ''

    # Mapear a estructura esperada
    # NOTA: Los nombres de las columnas deben coincidir con las preguntas del Forms
    caso = {
        'timestamp': data.get('Marca temporal', ''),
        'titulo': data.get('Título del caso', ''),
        'especialidad': data.get('Especialidad', ''),
        'sintomas_principales': data.get('Síntomas principales (separados por comas)', '').split(','),
        'sintomas_principales': [s.strip() for s in caso.get('sintomas_principales', []) if s.strip()],

        # Datos del paciente
        'paciente': {
            'nombre': data.get('Nombre del paciente (ficticio)', ''),
            'edad': data.get('Edad', ''),
            'sexo': data.get('Sexo', ''),
            'ocupacion': data.get('Ocupación', '')
        },

        # Items del caso (pueden venir como texto libre o estructurados)
        'items_caso': data.get('Items del caso (uno por línea)', '').split('\n'),
        'items_caso': [item.strip() for item in caso.get('items_caso', []) if item.strip()],

        # Contexto y personalidad
        'contexto': data.get('Contexto clínico (opcional)', ''),
        'personalidad': data.get('Personalidad del paciente (opcional)', ''),

        # Multimedia (URLs de Google Drive)
        'multimedia': {
            'radiografia': data.get('URL Radiografía (Google Drive)', ''),
            'ecg': data.get('URL ECG (Google Drive)', ''),
            'analitica': data.get('URL Analítica (Google Drive)', ''),
            'otros': data.get('URL Otros archivos (Google Drive)', '')
        },

        # Preguntas de desarrollo
        'preguntas_desarrollo': data.get('Preguntas de desarrollo (opcionales)', '').split('\n'),
        'preguntas_desarrollo': [p.strip() for p in caso.get('preguntas_desarrollo', []) if p.strip()],

        # Metadata
        'profesor_nombre': data.get('Tu nombre (profesor)', ''),
        'profesor_email': data.get('Tu email', ''),
        'procesado': False,
        'fecha_importacion': datetime.now().isoformat()
    }

    return caso


def get_new_cases() -> List[Dict]:
    """
    Obtiene casos nuevos desde Google Sheets que no han sido procesados.

    Returns:
        Lista de casos nuevos
    """
    if not SHEET_ID:
        print("❌ GOOGLE_SHEET_ID_PROFESORES no configurado en .env")
        print("Añade: GOOGLE_SHEET_ID_PROFESORES=tu_sheet_id")
        return []

    print(f"📊 Obteniendo datos de Google Sheet: {SHEET_ID}")

    # Leer todas las filas del sheet
    range_name = f"{SHEET_NAME}!A:Z"
    data = fetch_sheet_data(SHEET_ID, range_name)

    if not data:
        print("❌ No se pudieron obtener datos del sheet")
        return []

    if len(data) < 2:
        print("⚠️ Sheet vacío o sin datos")
        return []

    # Primera fila son los headers
    headers = data[0]
    rows = data[1:]

    print(f"✅ {len(rows)} respuestas encontradas en el formulario")

    # Cargar casos ya procesados
    processed_data = load_processed_cases()
    processed_timestamps = [c['timestamp'] for c in processed_data['casos_procesados']]

    # Parsear cada fila
    nuevos_casos = []
    for row in rows:
        caso = parse_form_response(row, headers)

        # Verificar si ya fue procesado (por timestamp)
        if caso['timestamp'] not in processed_timestamps:
            nuevos_casos.append(caso)

    print(f"🆕 {len(nuevos_casos)} casos nuevos sin procesar")

    return nuevos_casos


def mark_as_processed(caso: Dict):
    """
    Marca un caso como procesado.

    Args:
        caso: Diccionario con datos del caso
    """
    processed_data = load_processed_cases()

    processed_data['casos_procesados'].append({
        'timestamp': caso['timestamp'],
        'titulo': caso['titulo'],
        'fecha_procesamiento': datetime.now().isoformat()
    })

    save_processed_cases(processed_data)


def main():
    """Función principal para testing"""
    print("🚀 FETCH DE CASOS DESDE GOOGLE SHEETS")
    print("="*70)

    casos = get_new_cases()

    if not casos:
        print("\n✅ No hay casos nuevos para procesar")
        return

    print(f"\n📋 CASOS NUEVOS ENCONTRADOS:\n")
    for i, caso in enumerate(casos, 1):
        print(f"{i}. {caso['titulo']}")
        print(f"   Especialidad: {caso['especialidad']}")
        print(f"   Síntomas: {', '.join(caso['sintomas_principales'])}")
        print(f"   Profesor: {caso['profesor_nombre']}")
        print(f"   Fecha: {caso['timestamp']}")
        print()

    # Guardar casos en archivo temporal para inspección
    temp_file = os.path.join(BASE_DIR, 'data', 'casos_nuevos_temp.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(casos, f, ensure_ascii=False, indent=2)

    print(f"💾 Casos guardados temporalmente en: {temp_file}")
    print("\nPróximo paso: Ejecutar procesador_casos_v2.py para completar los casos")


if __name__ == "__main__":
    main()
