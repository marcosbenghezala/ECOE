"""
Procesador de Casos V2 - Mejorado con GPT-4 y activación por síntomas
Completa automáticamente los items del caso usando el checklist maestro
"""
import json
import os
import sys
import pickle
from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI

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

# Paths
MASTER_ITEMS_PATH = os.path.join(BASE_DIR, 'data', 'master_items.json')
PROMPTS_DIR = os.path.join(BASE_DIR, 'prompts')
CASOS_DIR = os.path.join(BASE_DIR, 'casos')

# Ensure casos directory exists
os.makedirs(CASOS_DIR, exist_ok=True)

class CaseProcessorV2:
    """
    Procesador mejorado que:
    1. Usa GPT-4 para sugerir items relevantes del maestro
    2. Activa items basándose en síntomas (no especialidad)
    3. Genera contexto automáticamente si está vacío
    4. Completa personalidad si falta
    5. Procesa multimedia (URLs)
    """

    def __init__(self, api_key: str, master_items_path: str):
        self.client = OpenAI(api_key=api_key)

        # Cargar master items
        with open(master_items_path, 'r', encoding='utf-8') as f:
            self.master_data = json.load(f)

    def load_prompt_template(self, filename: str) -> str:
        """Carga un template de prompt"""
        filepath = os.path.join(PROMPTS_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def generate_context_if_missing(self, caso: Dict) -> str:
        """
        Genera contexto clínico usando GPT-4 si está vacío.

        Args:
            caso: Datos del caso

        Returns:
            Contexto generado o existente
        """
        if caso.get('contexto') and caso['contexto'].strip():
            return caso['contexto']

        print("📝 Generando contexto clínico con GPT-4...")

        prompt = f"""Eres un médico experto creando un caso clínico para estudiantes de medicina.

Datos del caso:
- Título: {caso['titulo']}
- Especialidad: {caso['especialidad']}
- Síntomas principales: {', '.join(caso['sintomas_principales'])}
- Paciente: {caso['paciente']['sexo']}, {caso['paciente']['edad']} años, {caso['paciente']['ocupacion']}

Genera un contexto clínico breve (2-3 párrafos) que incluya:
1. Presentación del motivo de consulta
2. Historia de enfermedad actual (HEA)
3. Antecedentes relevantes si procede

El contexto debe ser realista y apropiado para una simulación ECOE.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un médico experto en casos clínicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Error generando contexto: {e}")
            return f"Paciente que consulta por {', '.join(caso['sintomas_principales'])}."

    def generate_personality_if_missing(self, caso: Dict) -> str:
        """
        Genera personalidad del paciente usando GPT-4 si está vacía.

        Args:
            caso: Datos del caso

        Returns:
            Personalidad generada o existente
        """
        if caso.get('personalidad') and caso['personalidad'].strip():
            return caso['personalidad']

        print("🎭 Generando personalidad del paciente con GPT-4...")

        prompt = f"""Eres un director de casting médico creando un personaje realista para simulación ECOE.

Paciente: {caso['paciente']['sexo']}, {caso['paciente']['edad']} años, {caso['paciente']['ocupacion']}
Síntomas: {', '.join(caso['sintomas_principales'])}

Genera una descripción breve de personalidad (2-3 líneas) que incluya:
- Tono emocional (ansioso, calmado, impaciente, colaborador, etc.)
- Nivel de comunicación (directo, reservado, detallista, etc.)
- Actitud hacia el médico

Sé breve y específico. El actor simulado usará esta descripción.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un experto en creación de personajes para simulaciones médicas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Error generando personalidad: {e}")
            return "Paciente colaborador, algo ansioso por sus síntomas."

    def suggest_items_from_master(self, caso: Dict) -> List[str]:
        """
        Usa GPT-4 para sugerir items relevantes del checklist maestro.

        Args:
            caso: Datos del caso

        Returns:
            Lista de IDs de items sugeridos
        """
        print("🤖 Analizando caso con GPT-4 para sugerir items relevantes...")

        # Construir lista de todos los items del maestro
        all_items = []

        # Bloques universales
        for bloque_key, bloque_data in self.master_data['bloques_universales'].items():
            for item in bloque_data['items']:
                all_items.append({
                    'id': item['id'],
                    'texto': item['texto'],
                    'bloque': bloque_data['nombre'],
                    'tipo': 'universal'
                })

        # Items por sistemas
        for sistema_key, sistema_data in self.master_data['items_por_sistemas'].items():
            for item in sistema_data['items']:
                all_items.append({
                    'id': item['id'],
                    'texto': item['texto'],
                    'sistema': sistema_data['nombre'],
                    'tipo': 'sistema',
                    'sintomas_trigger': item.get('sintomas_trigger', [])
                })

        # Crear prompt para GPT-4
        items_texto = "\n".join([f"- {item['id']}: {item['texto']}" for item in all_items[:50]])  # Limitar para no exceder tokens

        prompt = f"""Eres un profesor de medicina experto en evaluación clínica ECOE.

CASO CLÍNICO:
Título: {caso['titulo']}
Especialidad: {caso['especialidad']}
Síntomas principales: {', '.join(caso['sintomas_principales'])}
Paciente: {caso['paciente']['sexo']}, {caso['paciente']['edad']} años

ITEMS DISPONIBLES EN EL CHECKLIST MAESTRO (primeros 50):
{items_texto}

TAREA:
Selecciona los IDs de items que son MÁS RELEVANTES para evaluar a un estudiante en este caso.
Incluye solo items que:
1. Son críticos para este diagnóstico
2. Corresponden a los síntomas principales
3. Son esenciales en la anamnesis de este caso

Responde SOLO con una lista de IDs separados por comas, sin explicaciones.
Ejemplo: ID_01,MC_01,SOCR_01,RESP_03,CARDIO_01
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un experto en evaluación clínica ECOE."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )

            ids_text = response.choices[0].message.content.strip()
            suggested_ids = [id.strip() for id in ids_text.split(',') if id.strip()]

            print(f"✅ GPT-4 sugiere {len(suggested_ids)} items: {', '.join(suggested_ids[:10])}...")
            return suggested_ids

        except Exception as e:
            print(f"⚠️ Error en sugerencia de GPT-4: {e}")
            return []

    def activate_items_by_symptoms(self, sintomas: List[str]) -> Dict:
        """
        Activa items del maestro basándose en los síntomas del caso.

        Args:
            sintomas: Lista de síntomas principales

        Returns:
            Diccionario con items activados
        """
        print(f"🔍 Activando items para síntomas: {', '.join(sintomas)}")

        items_activados = []

        # SIEMPRE incluir bloques universales
        for bloque_key, bloque_data in self.master_data['bloques_universales'].items():
            for item in bloque_data['items']:
                items_activados.append(item)

        # Activar items por sistemas según síntomas
        for sistema_key, sistema_data in self.master_data['items_por_sistemas'].items():
            for item in sistema_data['items']:
                sintomas_trigger = item.get('sintomas_trigger', [])

                # Verificar si algún síntoma del caso coincide
                for sintoma_caso in sintomas:
                    sintoma_lower = sintoma_caso.lower().strip()
                    for trigger in sintomas_trigger:
                        if sintoma_lower in trigger.lower() or trigger.lower() in sintoma_lower:
                            items_activados.append(item)
                            break

        print(f"✅ {len(items_activados)} items activados")
        return items_activados

    def combine_items(self, activated_items: List[Dict], suggested_ids: List[str]) -> List[Dict]:
        """
        Combina items activados automáticamente con sugerencias de GPT-4.

        Args:
            activated_items: Items activados por síntomas
            suggested_ids: IDs sugeridos por GPT-4

        Returns:
            Lista final de items combinados (sin duplicados)
        """
        # Usar set para IDs únicos
        final_items_dict = {}

        # Añadir items activados
        for item in activated_items:
            final_items_dict[item['id']] = item

        # Añadir items sugeridos por GPT-4 (buscar en maestro)
        all_master_items = []
        for bloque_key, bloque_data in self.master_data['bloques_universales'].items():
            all_master_items.extend(bloque_data['items'])
        for sistema_key, sistema_data in self.master_data['items_por_sistemas'].items():
            all_master_items.extend(sistema_data['items'])

        for suggested_id in suggested_ids:
            for master_item in all_master_items:
                if master_item['id'] == suggested_id:
                    final_items_dict[suggested_id] = master_item
                    break

        final_items = list(final_items_dict.values())
        print(f"📋 Total items en checklist final: {len(final_items)}")

        return final_items

    def generate_system_prompt(self, caso: Dict) -> str:
        """
        Genera el system prompt para el simulador de paciente.

        Args:
            caso: Datos completos del caso

        Returns:
            System prompt completo
        """
        # Cargar template
        template = self.load_prompt_template('prompt_respuestas_paciente.txt')

        if not template:
            # Template por defecto si no existe archivo
            template = """Eres un paciente simulado para una práctica ECOE de medicina.

DATOS DEL PACIENTE:
- Nombre: {{nombre}}
- Edad: {{edad}} años
- Sexo: {{sexo}}
- Ocupación: {{ocupacion}}

PERSONALIDAD:
{{personalidad}}

CONTEXTO CLÍNICO:
{{contexto}}

SÍNTOMAS QUE PUEDES REVELAR:
{{sintomas_principales}}

INSTRUCCIONES:
1. Responde SOLO como el paciente, nunca salgas del personaje
2. Revela síntomas gradualmente según te pregunten
3. Sé realista y coherente con tu historia
4. NO des diagnósticos, solo describe tus síntomas
5. Si te preguntan algo que no sabes, di "No lo sé" o "No me he fijado"
6. Mantén la personalidad descrita arriba
"""

        # Reemplazar placeholders
        prompt = template.replace('{{nombre}}', caso['paciente']['nombre'])
        prompt = prompt.replace('{{edad}}', str(caso['paciente']['edad']))
        prompt = prompt.replace('{{sexo}}', caso['paciente']['sexo'])
        prompt = prompt.replace('{{ocupacion}}', caso['paciente']['ocupacion'])
        prompt = prompt.replace('{{personalidad}}', caso['personalidad'])
        prompt = prompt.replace('{{contexto}}', caso['contexto'])
        prompt = prompt.replace('{{sintomas_principales}}', ', '.join(caso['sintomas_principales']))

        return prompt

    def determine_voice_settings(self, caso: Dict) -> Dict:
        """
        Determina automáticamente la configuración de voz según el sexo.

        Args:
            caso: Datos del caso

        Returns:
            Configuración de voz para Realtime API
        """
        sexo = caso['paciente']['sexo'].lower()

        if 'mujer' in sexo or 'femenino' in sexo or sexo == 'f':
            # Mujer: shimmer o sage
            return {
                "model": "gpt-4o-realtime-preview",
                "voice": "shimmer",  # O "sage" alternativamente
                "instructions": "Usa tono femenino natural"
            }
        else:
            # Hombre: ash o echo
            return {
                "model": "gpt-4o-realtime-preview",
                "voice": "ash",  # O "echo" alternativamente
                "instructions": "Usa tono masculino natural"
            }

    def process_case(self, caso: Dict) -> str:
        """
        Procesa un caso completo desde Google Forms.

        Args:
            caso: Diccionario con datos del caso desde fetch_from_sheets

        Returns:
            Ruta al archivo .bin generado
        """
        print("\n" + "="*70)
        print(f"🔄 PROCESANDO CASO: {caso['titulo']}")
        print("="*70)

        # 1. Generar contexto si falta
        caso['contexto'] = self.generate_context_if_missing(caso)

        # 2. Generar personalidad si falta
        caso['personalidad'] = self.generate_personality_if_missing(caso)

        # 3. Activar items por síntomas
        activated_items = self.activate_items_by_symptoms(caso['sintomas_principales'])

        # 4. Sugerir items con GPT-4 (opcional, puede ser lento)
        # suggested_ids = self.suggest_items_from_master(caso)

        # 5. Combinar items (por ahora solo usamos activated)
        # final_items = self.combine_items(activated_items, suggested_ids)
        final_items = activated_items  # Simplificado

        # 6. Pre-calcular embeddings de items (optimización)
        print("📊 Generando embeddings de items...")
        for item in final_items:
            try:
                txt = item.get('texto', '')
                if txt and 'embedding' not in item:
                    resp = self.client.embeddings.create(
                        input=[txt.replace("\n", " ")],
                        model="text-embedding-3-small"
                    )
                    item['embedding'] = resp.data[0].embedding
            except Exception as e:
                print(f"⚠️ Error embedding item '{txt}': {e}")

        # 7. Generar system prompt
        system_prompt = self.generate_system_prompt(caso)

        # 8. Determinar voice settings
        voice_settings = self.determine_voice_settings(caso)

        # 9. Construir objeto del caso
        case_obj = {
            "metadata": {
                "titulo": caso['titulo'],
                "especialidad": caso['especialidad'],
                "sintomas_principales": caso['sintomas_principales'],
                "paciente": caso['paciente'],
                "timestamp": caso.get('timestamp', datetime.now().isoformat()),
                "profesor": caso.get('profesor_nombre', 'Unknown'),
                "fecha_creacion": datetime.now().isoformat()
            },
            "contexto": caso['contexto'],
            "personalidad": caso['personalidad'],
            "multimedia": caso.get('multimedia', {}),
            "checklist": final_items,
            "system_prompt": system_prompt,
            "voice_settings": voice_settings,
            "preguntas_desarrollo": caso.get('preguntas_desarrollo', [])
        }

        # 10. Guardar como .bin
        filename = f"{caso['titulo'].replace(' ', '_')}.bin"
        filepath = os.path.join(CASOS_DIR, filename)

        with open(filepath, 'wb') as f:
            pickle.dump(case_obj, f)

        print(f"✅ Caso guardado: {filepath}")

        # 11. Codificar para GitHub (JSON base64)
        try:
            from scripts.encode_case_to_github import encode_case_to_github
            json_filepath = encode_case_to_github(filepath)
            print(f"✅ Caso codificado para GitHub: {json_filepath}")
        except Exception as e:
            print(f"⚠️ Error codificando para GitHub: {e}")

        return filepath


def main():
    """Función principal para testing"""
    print("🚀 PROCESADOR DE CASOS V2")
    print("="*70)

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY no encontrada")
        return

    processor = CaseProcessorV2(
        api_key=OPENAI_API_KEY,
        master_items_path=MASTER_ITEMS_PATH
    )

    # Cargar casos nuevos desde fetch_from_sheets
    casos_temp_file = os.path.join(BASE_DIR, 'data', 'casos_nuevos_temp.json')

    if not os.path.exists(casos_temp_file):
        print(f"❌ No se encontró {casos_temp_file}")
        print("Ejecuta primero: python scripts/fetch_from_sheets.py")
        return

    with open(casos_temp_file, 'r', encoding='utf-8') as f:
        casos = json.load(f)

    if not casos:
        print("✅ No hay casos para procesar")
        return

    print(f"\n📋 Procesando {len(casos)} casos...\n")

    for caso in casos:
        try:
            filepath = processor.process_case(caso)

            # Marcar como procesado
            from scripts.fetch_from_sheets import mark_as_processed
            mark_as_processed(caso)

        except Exception as e:
            print(f"❌ Error procesando caso '{caso['titulo']}': {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
