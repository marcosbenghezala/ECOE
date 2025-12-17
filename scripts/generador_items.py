import json
import os
from openai import OpenAI
from config import settings

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def load_prompt(filename):
    """Loads a prompt template from the prompts directory."""
    filepath = os.path.join(settings.BASE_DIR, 'prompts', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_key_questions(case_data):
    """
    Uses GPT-4 to extract key anamnesis questions from the case description.
    """
    prompt_template = load_prompt('prompt_preguntas_clave.txt')
    
    # Fill placeholders
    prompt = prompt_template.replace('{{diagnostico}}', case_data['diagnostico'])
    prompt = prompt.replace('{{especialidad}}', case_data['especialidad'])
    prompt = prompt.replace('{{historia_clinica}}', case_data['historia_clinica'])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error extracting key questions: {e}")
        return {"preguntas": []}

def generate_items_from_questions(questions_json, case_data):
    """
    Converts key questions into evaluable checklist items.
    """
    prompt_template = load_prompt('prompt_generar_items.txt')
    
    # Fill placeholders
    prompt = prompt_template.replace('{{lista_preguntas_json}}', json.dumps(questions_json, indent=2))
    prompt = prompt.replace('{{especialidad}}', case_data['especialidad'])
    prompt = prompt.replace('{{aparato}}', case_data.get('aparato', 'General'))
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error generating items: {e}")
        return {"items": []}

def validate_item(item):
    """
    Validates a single item using GPT-4.
    """
    prompt_template = load_prompt('prompt_validar_item.txt')
    
    prompt = prompt_template.replace('{{texto_item}}', item['texto'])
    prompt = prompt.replace('{{aparato}}', item['aparato'])
    prompt = prompt.replace('{{tipo}}', item['tipo'])
    prompt = prompt.replace('{{nivel}}', item['nivel'])
    prompt = prompt.replace('{{keywords}}', str(item['keywords']))
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error validating item: {e}")
        return {"estado": "error", "motivo": str(e)}

def generate_checklist_for_case(case_data):
    """
    Orchestrates the full item generation pipeline.
    """
    print(f"Generating checklist for case: {case_data['diagnostico']}...")
    
    # Step 1: Extract questions
    questions = extract_key_questions(case_data)
    print(f"Extracted {len(questions.get('preguntas', []))} key questions.")
    
    # Step 2: Convert to items
    items_data = generate_items_from_questions(questions, case_data)
    items = items_data.get('items', [])
    print(f"Generated {len(items)} initial items.")
    
    # Step 3: Validate items (Optional, can be slow)
    validated_items = []
    for item in items:
        validation = validate_item(item)
        if validation.get('estado') == 'aceptable':
            validated_items.append(item)
        elif validation.get('estado') == 'problematico':
            # Apply suggestions if available
            if validation.get('sugerencia_texto'):
                item['texto'] = validation['sugerencia_texto']
            if validation.get('sugerencia_keywords'):
                item['keywords'] = validation['sugerencia_keywords']
            validated_items.append(item) # Add corrected item
            
    print(f"Final validated items: {len(validated_items)}")
    return validated_items

if __name__ == "__main__":
    # Test with dummy data
    dummy_case = {
        "diagnostico": "Neumonía adquirida en la comunidad",
        "especialidad": "Neumología",
        "historia_clinica": "Paciente de 65 años que acude por fiebre de 39ºC y tos productiva de 3 días de evolución.",
        "aparato": "Respiratorio"
    }
    items = generate_checklist_for_case(dummy_case)
    print(json.dumps(items, indent=2, ensure_ascii=False))
