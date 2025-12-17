import numpy as np
from openai import OpenAI
from config import settings
import json
import os

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

MASTER_ITEMS_PATH = os.path.join(settings.BASE_DIR, 'data', 'master_items.json')
EMBEDDINGS_PATH = os.path.join(settings.BASE_DIR, 'data', 'master_items_embeddings.npy')

def get_embedding(text):
    """Generates embedding for a text string."""
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def load_master_data():
    """Loads master items and their embeddings."""
    if os.path.exists(MASTER_ITEMS_PATH):
        with open(MASTER_ITEMS_PATH, 'r', encoding='utf-8') as f:
            master_items = json.load(f)
    else:
        master_items = []

    if os.path.exists(EMBEDDINGS_PATH):
        embeddings = np.load(EMBEDDINGS_PATH)
    else:
        embeddings = np.empty((0, 1536)) # Assuming 1536 dim for text-embedding-3-small

    return master_items, embeddings

def save_master_data(master_items, embeddings):
    """Saves updated master items and embeddings."""
    with open(MASTER_ITEMS_PATH, 'w', encoding='utf-8') as f:
        json.dump(master_items, f, indent=2, ensure_ascii=False)
    np.save(EMBEDDINGS_PATH, embeddings)

def check_duplicates(new_items, threshold=0.90):
    """
    Checks new items against master items using cosine similarity.
    Returns a list of unique items to add.
    """
    master_items, master_embeddings = load_master_data()
    unique_items = []
    
    if len(master_items) == 0:
        # First run, all items are unique
        # We need to generate embeddings for them
        new_embeddings_list = []
        for item in new_items:
            emb = get_embedding(item['texto'])
            new_embeddings_list.append(emb)
            unique_items.append(item)
        
        if unique_items:
            save_master_data(unique_items, np.array(new_embeddings_list))
        return unique_items

    # Normal run
    new_embeddings_list = []
    items_to_add = []
    
    for item in new_items:
        item_embedding = get_embedding(item['texto'])
        
        # Calculate cosine similarity with all master embeddings
        # Cosine similarity = (A . B) / (||A|| * ||B||)
        # Assuming embeddings are normalized from OpenAI, it's just dot product
        similarities = np.dot(master_embeddings, item_embedding)
        max_similarity = np.max(similarities)
        
        if max_similarity >= threshold:
            print(f"Duplicate found: '{item['texto']}' (Sim: {max_similarity:.2f})")
            # Ideally, we should map this new item to the existing ID
            # For now, we just skip adding it to master (reuse logic handled elsewhere)
        else:
            items_to_add.append(item)
            new_embeddings_list.append(item_embedding)
    
    # Update master data
    if items_to_add:
        updated_items = master_items + items_to_add
        updated_embeddings = np.vstack([master_embeddings, np.array(new_embeddings_list)])
        save_master_data(updated_items, updated_embeddings)
        print(f"Added {len(items_to_add)} new items to master.")
    
    return items_to_add

if __name__ == "__main__":
    # Test
    test_items = [
        {"texto": "Preguntar por fiebre", "id": "TEST_01"},
        {"texto": "Indagar sobre dolor torácico", "id": "TEST_02"}
    ]
    check_duplicates(test_items)
