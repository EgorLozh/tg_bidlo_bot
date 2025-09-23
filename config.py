import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
OLLAMA_HOST = os.getenv('OLLAMA_HOST')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')

# Загрузка системного промпта
def load_system_prompt():
    with open('prompts/system_prompt.txt', 'r', encoding='utf-8') as f:
        return f.read().strip()

SYSTEM_PROMPT = load_system_prompt()