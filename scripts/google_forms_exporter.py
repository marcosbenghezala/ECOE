"""
Google Forms Exporter
Envía resultados de evaluación a Google Forms usando POST directo
"""

import requests
import json
import os
from datetime import datetime

class GoogleFormsExporter:
    def __init__(self, config_path=None):
        """
        Inicializa el exportador con configuración de Google Forms
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'config', 
                'google_forms_config.json'
            )
        
        self.config = self._load_config(config_path)
        
    def _load_config(self, path):
        """Carga la configuración desde JSON"""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Configuración por defecto (placeholder)
            return {
                "results_form": {
                    "url": "CONFIGURAR_URL_AQUI",
                    "fields": {
                        "correo": "entry.000000001",
                        "nombre": "entry.000000002",
                        "matricula": "entry.000000003",
                        "caso": "entry.000000004",
                        "puntuacion": "entry.000000005",
                        "porcentaje_items": "entry.000000006",
                        "items_detalle": "entry.000000007",
                        "tiempo": "entry.000000008",
                        "diagnostico": "entry.000000009",
                        "diagnostico_diff": "entry.000000010",
                        "justificacion": "entry.000000011",
                        "transcripcion": "entry.000000012",
                        "feedback": "entry.000000013"
                    }
                }
            }
    
    def crear_diccionario(self, student_data, case_data, evaluation_report, transcript, diagnosis_data):
        """
        Crea el diccionario de datos para enviar al formulario
        
        Args:
            student_data: dict con nombre, matricula, correo
            case_data: dict con información del caso
            evaluation_report: dict con resultados de evaluación
            transcript: str con transcripción completa
            diagnosis_data: dict con diagnóstico del estudiante
        """
        fields = self.config["results_form"]["fields"]
        
        # Preparar detalle de ítems
        items_completados = sum(1 for item in evaluation_report['details'] if item['done'])
        total_items = len(evaluation_report['details'])
        porcentaje_items = f"{items_completados}/{total_items} ({evaluation_report['percentage']:.1f}%)"
        
        # Formatear detalle de ítems
        items_detalle = []
        for item in evaluation_report['details']:
            icon = "✅" if item['done'] else "❌"
            match_info = f" [{item.get('match_type', 'N/A')}]" if item['done'] else ""
            items_detalle.append(
                f"{icon} {item['item']}{match_info} ({item['score']}/{item['max_score']})"
            )
        items_detalle_str = "\n".join(items_detalle)
        
        # Crear diccionario
        diccionario = {
            fields["correo"]: student_data.get("correo", ""),
            fields["nombre"]: student_data.get("nombre", ""),
            fields["matricula"]: student_data.get("matricula", ""),
            fields["caso"]: case_data.get("titulo", ""),
            fields["puntuacion"]: str(round(evaluation_report['percentage'])),
            fields["porcentaje_items"]: porcentaje_items,
            fields["items_detalle"]: items_detalle_str,
            fields["tiempo"]: student_data.get("tiempo_utilizado", "N/A"),
            fields["diagnostico"]: diagnosis_data.get("principal", ""),
            fields["diagnostico_diff"]: diagnosis_data.get("diferencial", ""),
            fields["justificacion"]: diagnosis_data.get("justificacion", ""),
            fields["transcripcion"]: transcript[:5000],  # Limitar a 5000 chars
            fields["feedback"]: self._generar_feedback(evaluation_report)
        }
        
        return diccionario
    
    def _generar_feedback(self, report):
        """Genera feedback automático basado en el reporte"""
        percentage = report['percentage']
        
        if percentage >= 85:
            nivel = "Excelente"
            comentario = "Demuestras un dominio muy sólido de la anamnesis."
        elif percentage >= 70:
            nivel = "Bueno"
            comentario = "Buen desempeño general, con margen de mejora en algunos aspectos."
        elif percentage >= 50:
            nivel = "Aceptable"
            comentario = "Cubriste los aspectos básicos, pero faltan elementos importantes."
        else:
            nivel = "Insuficiente"
            comentario = "Necesitas reforzar varias áreas de la entrevista clínica."
        
        # Identificar fortalezas y debilidades
        completados = [item for item in report['details'] if item['done']]
        faltantes = [item for item in report['details'] if not item['done']]
        
        feedback = f"**Nivel: {nivel}** ({percentage:.1f}%)\n\n{comentario}\n\n"
        
        if completados:
            feedback += f"**Fortalezas** ({len(completados)} ítems):\n"
            for item in completados[:5]:  # Top 5
                feedback += f"• {item['item']}\n"
        
        if faltantes:
            feedback += f"\n**A mejorar** ({len(faltantes)} ítems faltantes):\n"
            for item in faltantes[:5]:  # Top 5
                feedback += f"• {item['item']}\n"
        
        return feedback
    
    def enviar_respuesta(self, student_data, case_data, evaluation_report, transcript, diagnosis_data):
        """
        Envía los datos al Google Form
        
        Returns:
            bool: True si se envió correctamente, False si hubo error
        """
        url = self.config["results_form"]["url"]
        
        if url == "CONFIGURAR_URL_AQUI":
            print("⚠️  Google Forms no configurado. Ver docs/08_GOOGLE_FORMS_SETUP.md")
            return False
        
        diccionario = self.crear_diccionario(
            student_data, 
            case_data, 
            evaluation_report, 
            transcript, 
            diagnosis_data
        )
        
        try:
            response = requests.post(url, data=diccionario, timeout=10)
            
            if response.status_code == 200:
                print("✅ Resultados enviados correctamente a Google Forms")
                return True
            else:
                print(f"❌ Error al enviar: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error al enviar resultados: {e}")
            return False


# Función de conveniencia para usar en notebook
def enviar_resultados_estudiante(student_data, case_data, evaluation_report, transcript, diagnosis_data):
    """
    Función wrapper para enviar resultados desde el notebook
    """
    exporter = GoogleFormsExporter()
    return exporter.enviar_respuesta(
        student_data, 
        case_data, 
        evaluation_report, 
        transcript, 
        diagnosis_data
    )


if __name__ == "__main__":
    # Test
    print("Testing Google Forms Exporter...")
    
    # Datos de prueba
    student_data = {
        "correo": "estudiante@test.com",
        "nombre": "Juan Pérez",
        "matricula": "12345",
        "tiempo_utilizado": "14:23"
    }
    
    case_data = {
        "titulo": "Caso 1: Dolor torácico"
    }
    
    evaluation_report = {
        "percentage": 85.5,
        "details": [
            {"item": "Saluda al paciente", "done": True, "match_type": "keyword", "score": 1, "max_score": 1},
            {"item": "Pregunta por dolor", "done": True, "match_type": "embedding", "score": 3, "max_score": 3},
            {"item": "Pregunta por alergias", "done": False, "score": 0, "max_score": 1}
        ]
    }
    
    transcript = "Hola doctor. Me duele el pecho cuando subo escaleras."
    
    diagnosis_data = {
        "principal": "Angina estable",
        "diferencial": "Infarto, Pericarditis",
        "justificacion": "Por el dolor opresivo relacionado con el esfuerzo"
    }
    
    exporter = GoogleFormsExporter()
    exporter.enviar_respuesta(student_data, case_data, evaluation_report, transcript, diagnosis_data)
