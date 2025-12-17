"""
Google Sheets Importer
Lee casos clínicos desde Google Sheets y genera archivos .bin automáticamente
"""

import os
import sys
import json
import pickle
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generador_items import generate_checklist_for_case
from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class GoogleSheetsImporter:
    def __init__(self, credentials_path=None, config_path=None):
        """
        Inicializa el importador con credenciales de Google
        """
        if credentials_path is None:
            credentials_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'config', 
                'google_credentials.json'
            )
        
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'config', 
                'google_forms_config.json'
            )
        
        self.credentials_path = credentials_path
        self.config = self._load_config(config_path)
        self.service = None
        
    def _load_config(self, path):
        """Carga configuración"""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "cases_sheet": {
                    "spreadsheet_id": "CONFIGURAR_SPREADSHEET_ID",
                    "sheet_name": "Respuestas de formulario 1",
                    "processed_column": "AA"  # Columna para marcar procesado
                }
            }
    
    def _authenticate(self):
        """Autentica con Google Sheets API"""
        if not os.path.exists(self.credentials_path):
            print(f"⚠️  Credenciales no encontradas en: {self.credentials_path}")
            print("Ver docs/08_GOOGLE_FORMS_SETUP.md para instrucciones")
            return False
        
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=creds)
            return True
        except Exception as e:
            print(f"❌ Error de autenticación: {e}")
            return False
    
    def fetch_new_cases(self):
        """
        Lee casos nuevos desde Google Sheets
        
        Returns:
            list: Lista de diccionarios con datos de casos
        """
        if not self._authenticate():
            return []
        
        config = self.config["cases_sheet"]
        spreadsheet_id = config["spreadsheet_id"]
        sheet_name = config["sheet_name"]
        
        if spreadsheet_id == "CONFIGURAR_SPREADSHEET_ID":
            print("⚠️  Spreadsheet ID no configurado")
            return []
        
        try:
            # Leer todas las filas
            range_name = f"{sheet_name}!A:AA"  # Hasta columna AA
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            
            if not rows:
                print("No hay datos en la hoja")
                return []
            
            # Primera fila = headers
            headers = rows[0]
            
            # Mapear columnas (asumiendo el orden del formulario diseñado)
            col_map = self._create_column_mapping(headers)
            
            # Procesar filas (saltando header)
            cases = []
            for idx, row in enumerate(rows[1:], start=2):  # Empezar en fila 2
                # Verificar si ya fue procesado
                processed_col_idx = len(headers)  # Última columna
                if len(row) > processed_col_idx and row[processed_col_idx]:
                    continue  # Ya procesado, saltar
                
                case = self._parse_row(row, col_map)
                if case:
                    case['row_number'] = idx  # Guardar número de fila
                    cases.append(case)
            
            print(f"📥 Encontrados {len(cases)} casos nuevos")
            return cases
            
        except HttpError as e:
            print(f"❌ Error al leer Google Sheets: {e}")
            return []
    
    def _create_column_mapping(self, headers):
        """Crea mapeo de columnas basado en los headers"""
        # Mapeo flexible basado en nombres de columnas
        mapping = {}
        for idx, header in enumerate(headers):
            header_lower = header.lower()
            
            if 'correo' in header_lower or 'email' in header_lower:
                mapping['correo'] = idx
            elif 'título' in header_lower or 'titulo' in header_lower:
                mapping['titulo'] = idx
            elif 'diagnóstico principal' in header_lower or 'diagnostico' in header_lower:
                mapping['diagnostico'] = idx
            elif 'especialidad' in header_lower:
                mapping['especialidad'] = idx
            elif 'aparato' in header_lower or 'sistema' in header_lower:
                mapping['aparato'] = idx
            elif 'historia clínica' in header_lower or 'historia' in header_lower:
                mapping['historia_clinica'] = idx
            elif 'síntomas principales' in header_lower or 'sintomas' in header_lower:
                mapping['sintomas_principales'] = idx
            elif 'síntomas ocultos' in header_lower:
                mapping['sintomas_ocultos'] = idx
            elif 'edad' in header_lower:
                mapping['edad'] = idx
            elif 'sexo' in header_lower:
                mapping['sexo'] = idx
            elif 'ocupación' in header_lower or 'ocupacion' in header_lower:
                mapping['ocupacion'] = idx
            elif 'personalidad' in header_lower:
                mapping['personalidad'] = idx
            elif 'contexto' in header_lower:
                mapping['contexto'] = idx
            elif 'voz' in header_lower:
                mapping['voz'] = idx
        
        return mapping
    
    def _parse_row(self, row, col_map):
        """Convierte una fila en un diccionario de caso"""
        def get_value(key, default=''):
            idx = col_map.get(key)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return default
        
        # Validar campos obligatorios
        titulo = get_value('titulo')
        diagnostico = get_value('diagnostico')
        especialidad = get_value('especialidad')
        historia_clinica = get_value('historia_clinica')
        
        if not all([titulo, diagnostico, especialidad, historia_clinica]):
            return None  # Datos incompletos
        
        # Construir diccionario de caso
        case = {
            'titulo': titulo,
            'diagnostico': diagnostico,
            'especialidad': especialidad,
            'aparato': get_value('aparato', 'General'),
            'historia_clinica': historia_clinica,
            'sintomas_principales': get_value('sintomas_principales', ''),
            'edad': int(get_value('edad', '50')),
            'sexo': get_value('sexo', 'Masculino'),
            'ocupacion': get_value('ocupacion', 'No especificado'),
            'personalidad': get_value('personalidad', 'Colaborador'),
            'contexto': get_value('contexto', 'Consulta externa')
        }
        
        # Procesar síntomas
        if case['sintomas_principales']:
            case['sintomas_permitidos'] = [s.strip() for s in case['sintomas_principales'].split(',')]
        else:
            case['sintomas_permitidos'] = []
        
        sintomas_ocultos = get_value('sintomas_ocultos')
        if sintomas_ocultos:
            case['sintomas_ocultos'] = [s.strip() for s in sintomas_ocultos.split(',')]
        else:
            case['sintomas_ocultos'] = []
        
        # Voz
        voz = get_value('voz', 'Alloy').lower()
        voces_map = {
            'alloy': 'alloy',
            'echo': 'echo',
            'fable': 'fable',
            'onyx': 'onyx',
            'nova': 'nova',
            'shimmer': 'shimmer'
        }
        case['voice_settings'] = {
            'model': 'tts-1',
            'voice': voces_map.get(voz, 'alloy')
        }
        
        return case
    
    def mark_as_processed(self, row_number):
        """Marca una fila como procesada"""
        if not self.service:
            return
        
        config = self.config["cases_sheet"]
        spreadsheet_id = config["spreadsheet_id"]
        sheet_name = config["sheet_name"]
        processed_col = config["processed_column"]
        
        range_name = f"{sheet_name}!{processed_col}{row_number}"
        
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [['PROCESADO']]}
            ).execute()
        except Exception as e:
            print(f"⚠️  No se pudo marcar fila {row_number}: {e}")
    
    def process_and_generate_cases(self):
        """
        Workflow completo: lee casos, genera checklists y archivos .bin
        """
        print("🔄 Sincronizando casos desde Google Sheets...")
        
        new_cases = self.fetch_new_cases()
        
        if not new_cases:
            print("✅ No hay casos nuevos para procesar")
            return
        
        from scripts.procesador_casos import process_case
        
        for case in new_cases:
            try:
                print(f"\n📝 Procesando: {case['titulo']}")
                process_case(case)
case['row_number'] = row_number  # Para marcar después
                self.mark_as_processed(case['row_number'])
                print(f"✅ Caso procesado y marcado")
            except Exception as e:
                print(f"❌ Error procesando caso: {e}")


def sync_cases_from_sheets():
    """Función wrapper para usar en scripts o notebooks"""
    importer = GoogleSheetsImporter()
    importer.process_and_generate_cases()


if __name__ == "__main__":
    print("=" * 60)
    print("📥 Google Sheets Importer - ECOE Cases")
    print("=" * 60)
    sync_cases_from_sheets()
