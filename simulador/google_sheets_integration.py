#!/usr/bin/env python3
"""
Google Sheets Integration - Guardar sesiones de estudiantes
22 columnas según especificación
"""

import os
from datetime import datetime
from typing import Dict, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsIntegration:
    """
    Integración con Google Sheets para guardar datos de estudiantes
    """

    def __init__(self, credentials_path: str = None, spreadsheet_id: str = None):
        """
        Args:
            credentials_path: Ruta al archivo JSON de credenciales de servicio
            spreadsheet_id: ID de la hoja de cálculo de destino
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')

        if not self.credentials_path:
            print("⚠️  GOOGLE_SHEETS_CREDENTIALS no configurado")
            self.service = None
            return

        if not self.spreadsheet_id:
            print("⚠️  GOOGLE_SHEETS_ID no configurado")
            self.service = None
            return

        # Inicializar servicio de Google Sheets
        self.service = self._init_service()

    def _init_service(self):
        """Inicializar servicio de Google Sheets API"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )

            service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API conectado")

            return service

        except Exception as e:
            print(f"❌ Error inicializando Google Sheets: {e}")
            return None

    def save_student_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guardar sesión de estudiante en Google Sheets

        Args:
            data: Diccionario con los datos de la sesión (22 columnas)

        Returns:
            Resultado de la operación
        """

        if not self.service:
            print("⚠️  Google Sheets no configurado, guardando en logs...")
            self._save_to_fallback(data)
            return {'success': False, 'error': 'Google Sheets no configurado'}

        try:
            # Preparar fila con las 22 columnas en orden
            row = [
                data.get('timestamp', datetime.now().isoformat()),
                data.get('estudiante_nombre', ''),
                data.get('estudiante_dni', ''),
                data.get('estudiante_matricula', ''),
                data.get('caso_id', ''),
                data.get('caso_titulo', ''),
                data.get('especialidad', ''),
                data.get('duracion_minutos', 0),
                data.get('transcripcion_completa', ''),
                data.get('puntuacion_total', 0),
                data.get('puntuacion_maxima', 0),
                data.get('porcentaje', 0),
                data.get('calificacion', ''),
                data.get('feedback_general', ''),
                data.get('items_evaluados', ''),
                data.get('reflexion_pregunta_1', ''),
                data.get('reflexion_pregunta_2', ''),
                data.get('reflexion_pregunta_3', ''),
                data.get('reflexion_pregunta_4', ''),
                data.get('encuesta_valoracion', 0),
                data.get('encuesta_comentarios', ''),
                data.get('session_id', '')
            ]

            # Añadir fila a la hoja
            body = {
                'values': [row]
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Sesiones!A:V',  # 22 columnas = A hasta V
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            print(f"✅ Sesión guardada en Google Sheets: {result.get('updates', {}).get('updatedRows', 0)} fila(s)")

            return {
                'success': True,
                'updates': result.get('updates')
            }

        except HttpError as e:
            print(f"❌ Error HTTP en Google Sheets: {e}")
            self._save_to_fallback(data)
            return {'success': False, 'error': str(e)}

        except Exception as e:
            print(f"❌ Error guardando en Google Sheets: {e}")
            self._save_to_fallback(data)
            return {'success': False, 'error': str(e)}

    def _save_to_fallback(self, data: Dict[str, Any]):
        """Guardar en archivo local si Google Sheets falla"""
        try:
            from pathlib import Path
            fallback_file = Path(__file__).parent.parent / 'sesiones_fallback.jsonl'

            import json
            with open(fallback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

            print(f"💾 Sesión guardada en fallback: {fallback_file}")

        except Exception as e:
            print(f"❌ Error guardando fallback: {e}")

    def create_sheet_with_headers(self, sheet_name: str = 'Sesiones'):
        """
        Crear hoja con headers (ejecutar una vez para inicializar)

        Args:
            sheet_name: Nombre de la hoja
        """

        if not self.service:
            print("⚠️  Google Sheets no configurado")
            return

        headers = [
            'Timestamp',
            'Estudiante - Nombre',
            'Estudiante - DNI',
            'Estudiante - Matrícula',
            'Caso - ID',
            'Caso - Título',
            'Especialidad',
            'Duración (minutos)',
            'Transcripción Completa',
            'Puntuación Total',
            'Puntuación Máxima',
            'Porcentaje (%)',
            'Calificación',
            'Feedback General',
            'Items Evaluados (JSON)',
            'Reflexión - Pregunta 1',
            'Reflexión - Pregunta 2',
            'Reflexión - Pregunta 3',
            'Reflexión - Pregunta 4',
            'Encuesta - Valoración (1-5)',
            'Encuesta - Comentarios',
            'Session ID'
        ]

        try:
            # Verificar si la hoja ya existe
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            sheets = sheet_metadata.get('sheets', [])
            sheet_exists = any(s['properties']['title'] == sheet_name for s in sheets)

            if not sheet_exists:
                # Crear hoja
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]

                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()

                print(f"✅ Hoja '{sheet_name}' creada")

            # Escribir headers
            body = {
                'values': [headers]
            }

            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A1:V1',
                valueInputOption='RAW',
                body=body
            ).execute()

            # Formatear headers (negrita, fondo gris)
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': self._get_sheet_id(sheet_name),
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            print(f"✅ Headers escritos en '{sheet_name}'")

        except Exception as e:
            print(f"❌ Error creando hoja: {e}")

    def _get_sheet_id(self, sheet_name: str) -> int:
        """Obtener ID numérico de una hoja por nombre"""
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']

            return 0

        except Exception as e:
            print(f"❌ Error obteniendo sheet ID: {e}")
            return 0

    def get_case_questions(self, case_id: str) -> list:
        """
        Obtener preguntas de desarrollo para un caso específico.

        Intenta leer desde Google Sheets primero, luego usa fallback JSON.

        Args:
            case_id: ID del caso

        Returns:
            Lista de preguntas con estructura:
            [
                {
                    "id": 1,
                    "question": "texto de la pregunta",
                    "field_name": "nombre del campo",
                    "criteria": "criterios de evaluación",
                    "max_score": 100
                },
                ...
            ]
        """
        # 1. Intentar desde Google Sheets (si está configurado)
        if self.service:
            try:
                # Leer desde hoja "Preguntas" con estructura:
                # Columna A: caso_id
                # Columna B: pregunta_id
                # Columna C: question
                # Columna D: field_name
                # Columna E: criteria
                # Columna F: max_score

                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range='Preguntas!A:F'
                ).execute()

                rows = result.get('values', [])

                if not rows:
                    print(f"⚠️  Hoja 'Preguntas' vacía, usando fallback")
                else:
                    # Filtrar por case_id (saltar header)
                    questions = []
                    for row in rows[1:]:  # Skip header
                        if len(row) >= 6 and row[0] == case_id:
                            questions.append({
                                "id": int(row[1]),
                                "question": row[2],
                                "field_name": row[3],
                                "criteria": row[4],
                                "max_score": int(row[5]) if row[5] else 100
                            })

                    if questions:
                        print(f"✅ Preguntas cargadas desde Google Sheets: {len(questions)}")
                        return sorted(questions, key=lambda x: x['id'])
                    else:
                        print(f"⚠️  No se encontraron preguntas para caso '{case_id}' en Sheets, usando fallback")

            except HttpError as e:
                print(f"⚠️  Error HTTP en Google Sheets (preguntas): {e}, usando fallback")
            except Exception as e:
                print(f"⚠️  Error obteniendo preguntas desde Sheets: {e}, usando fallback")

        # 2. Fallback: usar JSON local
        return self._get_questions_from_fallback(case_id)

    def _get_questions_from_fallback(self, case_id: str) -> list:
        """
        Cargar preguntas desde archivo JSON fallback.

        Args:
            case_id: ID del caso

        Returns:
            Lista de preguntas
        """
        try:
            from pathlib import Path
            import json

            fallback_file = Path(__file__).parent / 'data' / 'questions_fallback.json'

            if not fallback_file.exists():
                print(f"❌ Archivo fallback no encontrado: {fallback_file}")
                # Retornar preguntas genéricas hardcoded
                return self._get_hardcoded_questions()

            with open(fallback_file, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)

            # Buscar preguntas para el caso específico
            if case_id in questions_data:
                print(f"✅ Preguntas cargadas desde fallback (caso específico): {case_id}")
                return questions_data[case_id]

            # Si no existe el caso, usar preguntas default
            if 'default' in questions_data:
                print(f"✅ Preguntas cargadas desde fallback (default)")
                return questions_data['default']

            print(f"⚠️  No se encontraron preguntas en fallback, usando hardcoded")
            return self._get_hardcoded_questions()

        except Exception as e:
            print(f"❌ Error leyendo fallback de preguntas: {e}")
            return self._get_hardcoded_questions()

    def _get_hardcoded_questions(self) -> list:
        """Preguntas genéricas hardcoded (último recurso)"""
        return [
            {
                "id": 1,
                "question": "Resume el motivo de consulta y los síntomas más importantes del paciente.",
                "field_name": "resumen_caso",
                "criteria": "Identifica correctamente síntomas principales y motivo de consulta",
                "max_score": 100
            },
            {
                "id": 2,
                "question": "¿Cuál es tu diagnóstico más probable? Justifícalo con datos de la anamnesis.",
                "field_name": "diagnostico_principal",
                "criteria": "Diagnóstico correcto y bien justificado",
                "max_score": 100
            },
            {
                "id": 3,
                "question": "Indica dos diagnósticos diferenciales razonables.",
                "field_name": "diagnosticos_diferenciales",
                "criteria": "Dos diagnósticos diferenciales válidos",
                "max_score": 100
            },
            {
                "id": 4,
                "question": "¿Qué pruebas complementarias solicitarías?",
                "field_name": "pruebas_diagnosticas",
                "criteria": "Pruebas apropiadas y justificadas",
                "max_score": 100
            }
        ]


# ========== EJEMPLO DE USO ==========

def example_usage():
    """Ejemplo de uso de Google Sheets Integration"""

    # Inicializar
    sheets = GoogleSheetsIntegration()

    # Crear hoja con headers (solo una vez)
    # sheets.create_sheet_with_headers('Sesiones')

    # Guardar sesión de ejemplo
    data = {
        'timestamp': datetime.now().isoformat(),
        'estudiante_nombre': 'María García',
        'estudiante_dni': '12345678A',
        'estudiante_matricula': 'MED2024001',
        'caso_id': 'caso_001',
        'caso_titulo': 'Dolor torácico agudo',
        'especialidad': 'Cardiología',
        'duracion_minutos': 14,
        'transcripcion_completa': '[ESTUDIANTE]: Hola, ¿qué le trae por aquí?\n[PACIENTE]: Tengo dolor en el pecho...',
        'puntuacion_total': 75,
        'puntuacion_maxima': 100,
        'porcentaje': 75.0,
        'calificacion': 'Notable',
        'feedback_general': 'Buena anamnesis inicial. Se recomienda profundizar en ICE.',
        'items_evaluados': '[{"item": "Presentación", "evaluado": true}, ...]',
        'reflexion_pregunta_1': 'El diagnóstico diferencial incluye IAM, angina...',
        'reflexion_pregunta_2': 'Aprendí la importancia de hacer ECG temprano...',
        'reflexion_pregunta_3': 'Mejoraría mi exploración física...',
        'reflexion_pregunta_4': 'Sí, considero que mi comunicación fue empática.',
        'encuesta_valoracion': 5,
        'encuesta_comentarios': 'Excelente experiencia de aprendizaje',
        'session_id': 'abc123-def456'
    }

    result = sheets.save_student_session(data)
    print(f"Resultado: {result}")


if __name__ == '__main__':
    example_usage()
