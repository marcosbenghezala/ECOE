import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CASES_DIR = os.path.join(BASE_DIR, "casos")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# Constants
MASTER_ITEMS_PATH = os.path.join(DATA_DIR, "master_items.json")
TEMPLATES_PATH = os.path.join(DATA_DIR, "templates_especialidad.json")
