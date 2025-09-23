import requests
import logging
from config import OLLAMA_HOST, OLLAMA_MODEL, SYSTEM_PROMPT

class OllamaClient:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.host = OLLAMA_HOST
        logging.info(f"Инициализирован OllamaClient с моделью: {self.model}")
    
    def generate_response(self, user_message: str) -> str:
        """Генерация ответа через chat API (лучше для системных промптов)"""
        try:
            url = f"{self.host}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user", 
                        "content": user_message
                    }
                ],
                "stream": False
            }
            
            logging.info(f"Отправка запроса к {url} с моделью {self.model}")
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            raw_response = result['message']['content']
            
            # Фильтруем тег <think> если он есть
            cleaned_response = self._remove_think_tags(raw_response)
            
            return cleaned_response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP error: {e}")
            return f"❌ Ошибка соединения с Ollama: {str(e)}"
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return f"❌ Неожиданная ошибка: {str(e)}"
    
    def _remove_think_tags(self, text: str) -> str:
        """Удаляет теги <think> и их содержимое из текста"""
        import re
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
        cleaned_text = cleaned_text.strip()
        return cleaned_text if cleaned_text else "Извините, не удалось сгенерировать ответ."