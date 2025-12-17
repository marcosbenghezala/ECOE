import json
import os
import pickle
from openai import OpenAI
from config import settings
from scripts.generador_items import generate_checklist_for_case
from scripts.detector_duplicados import check_duplicates

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def load_prompt(filename):
    """Loads a prompt template from the prompts directory."""
    filepath = os.path.join(settings.BASE_DIR, 'prompts', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def generate_system_prompt(case_data):
    """Generates the system prompt for the patient simulator."""
    prompt_template = load_prompt('prompt_respuestas_paciente.txt')
    
    # Fill placeholders
    prompt = prompt_template.replace('{{diagnostico}}', case_data['diagnostico'])
    prompt = prompt.replace('{{historia_clinica}}', case_data['historia_clinica'])
    prompt = prompt.replace('{{edad}}', str(case_data['edad']))
    prompt = prompt.replace('{{sexo}}', case_data['sexo'])
    prompt = prompt.replace('{{ocupacion}}', case_data['ocupacion'])
    prompt = prompt.replace('{{personalidad}}', case_data.get('personalidad', 'Neutro'))
    prompt = prompt.replace('{{sintomas_permitidos}}', ", ".join(case_data.get('sintomas_permitidos', [])))
    prompt = prompt.replace('{{sintomas_ocultos}}', ", ".join(case_data.get('sintomas_ocultos', [])))
    
    # These placeholders are dynamic during simulation, but we set the static part here
    # Ideally, the simulator backend should handle the full prompt construction
    # For the .bin file, we store the *template* or a pre-filled base
    return prompt

def process_case(case_data):
    """
    Main pipeline:
    1. Generate checklist items
    2. Check for duplicates
    3. Generate system prompt
    4. Save case to .bin
    """
    print(f"Processing case: {case_data['diagnostico']}")
    
    # 1. Generate Items
    generated_items = generate_checklist_for_case(case_data)
    
    # 1b. Pre-calculate Embeddings for Items (Optimization)
    print("Pre-calculating item embeddings...")
    for item in generated_items:
        try:
            txt = item.get('texto', item.get('item', ''))
            if txt:
                # We can use the detector_duplicados function or direct client call
                # Let's use direct client call to avoid circular imports or complex deps
                resp = client.embeddings.create(input=[txt.replace("\n", " ")], model="text-embedding-3-small")
                item['embedding'] = resp.data[0].embedding
        except Exception as e:
            print(f"Failed to embed item '{txt}': {e}")

    # 2. Check Duplicates & Update Master
    # We only add non-duplicates to master, but for the case itself we use the generated ones
    # (or mapped ones if we implemented full mapping logic)
    check_duplicates(generated_items)
    
    # 3. Generate System Prompt
    system_prompt = generate_system_prompt(case_data)
    
    # 4. Construct Case Object
    case_obj = {
        "metadata": case_data,
        "checklist": generated_items,
        "system_prompt": system_prompt,
        "voice_settings": case_data.get("voice_settings", {"model": "tts-1", "voice": "alloy"})
    }
    
    # 5. Save to .bin
    filename = f"{case_data['diagnostico'].replace(' ', '_')}_001.bin" # Simple naming for now
    filepath = os.path.join(settings.BASE_DIR, 'casos', filename)
    
    with open(filepath, 'wb') as f:
        pickle.dump(case_obj, f)
    
    print(f"Case saved to {filepath}")
    
    # 6. NUEVO: También generar versión codificada para GitHub
    try:
        from scripts.encode_case_to_github import encode_case_to_github
        json_filepath = encode_case_to_github(filepath)
        print(f"Encoded case saved to {json_filepath} (ready for GitHub)")
    except Exception as e:
        print(f"⚠️  Warning: Could not encode case for GitHub: {e}")
    
    return filepath

if __name__ == "__main__":
    # Load sample input
    sample_input_path = os.path.join(settings.BASE_DIR, 'data', 'sample_case_input.json')
    if os.path.exists(sample_input_path):
        with open(sample_input_path, 'r') as f:
            case_data = json.load(f)
        if isinstance(case_data, list):
            for case in case_data:
                process_case(case)
        else:
            process_case(case_data)
    else:
        print("Sample input not found.")
