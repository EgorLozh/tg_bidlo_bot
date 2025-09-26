import asyncio
import logging
from collections import deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN
from ollama_client import OllamaClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ollama_client = OllamaClient()

# Хранилище сообщений и их связей
message_storage = {}  # {message_id: {message_data}}
MAX_CHAIN_DEPTH = 10
BOT_TRIGGER_WORD = "хуба"

class MessageNode:
    def __init__(self, message_id: int, chat_id: int, user_id: int, username: str, text: str, is_bot: bool = False):
        self.message_id = message_id
        self.chat_id = chat_id
        self.user_id = user_id
        self.username = username
        self.text = text
        self.is_bot = is_bot
        self.reply_to_message_id = None  # ID сообщения, на которое это ответ
        self.timestamp = types.Message.date  # Время сообщения

def get_message_chain(message: types.Message) -> list:
    """Рекурсивно собирает цепочку сообщений по дереву ответов"""
    chain = []
    current_message = message
    depth = 0
    
    while current_message and depth < MAX_CHAIN_DEPTH:
        # Добавляем текущее сообщение в цепочку
        chain.append({
            "role": "assistant" if (current_message.reply_to_message and 
                                   current_message.reply_to_message.from_user.id == bot.id) else "user",
            "name": current_message.from_user.username or current_message.from_user.first_name,
            "content": current_message.text
        })
        
        # Если это ответ на сообщение бота, идем дальше по цепочке
        if (current_message.reply_to_message and 
            current_message.reply_to_message.from_user.id == bot.id):
            current_message = current_message.reply_to_message
            depth += 1
        else:
            break
    
    # Разворачиваем цепочку в правильном порядке (от старого к новому)
    chain.reverse()
    return chain

def should_respond_to_message(text: str) -> bool:
    """Проверяем, должно ли сообщение активировать бота"""
    if not text or not text.strip():
        return False
    
    cleaned_text = text.strip().lower()
    return cleaned_text.startswith(BOT_TRIGGER_WORD.lower())

def extract_question(text: str) -> str:
    """Извлекаем вопрос после ключевого слова"""
    if not text:
        return ""
    
    cleaned_text = text.strip()
    if cleaned_text.lower().startswith(BOT_TRIGGER_WORD.lower()):
        question = cleaned_text[len(BOT_TRIGGER_WORD):].strip()
        return question
    return ""

@dp.message(Command("start"))
async def start_command(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(
        f"🤖 Бот @{bot_info.username} активен!\n\n"
        f"💬 **Как использовать:**\n"
        f"Напишите сообщение начинающееся с слова `{BOT_TRIGGER_WORD}`\n\n"
        f"📚 Бот запоминает контекст цепочки диалога (глубина: {MAX_CHAIN_DEPTH} сообщений)."
    )

@dp.message(Command("ping"))
async def ping_command(message: types.Message):
    await message.answer("🏓 Понг! Бот работает исправно!")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        f"💡 **Помощь по использованию бота:**\n\n"
        f"Начните сообщение с `{BOT_TRIGGER_WORD}` или отвечайте на сообщения бота.\n"
        f"Бот будет помнить контекст всей цепочки диалога.\n\n"
        f"**Пример:**\n"
        f"1. Вы: `{BOT_TRIGGER_WORD} что такое Python?`\n"
        f"2. Бот: объясняет про Python\n"
        f"3. Вы (ответом на сообщение бота): `А чем он отличается от Java?`\n"
        f"4. Бот: отвечает с учетом предыдущего контекста"
    )

@dp.message()
async def handle_messages(message: types.Message):
    """Обработчик сообщений с цепочкой ответов"""
    text = message.text or ""
    
    logger.info(f"Получено сообщение: {text}")
    logger.info(f"Ответ на сообщение: {message.reply_to_message}")
    
    # Проверяем активацию по ключевому слову ИЛИ ответ на сообщение бота
    should_respond = False
    question = ""
    
    # Случай 1: Сообщение начинается с ключевого слова
    if should_respond_to_message(text):
        logger.info("Активация по ключевому слову")
        question = extract_question(text)
        should_respond = bool(question)
    
    # Случай 2: Ответ на сообщение бота
    elif (message.reply_to_message and 
          message.reply_to_message.from_user and 
          message.reply_to_message.from_user.id == (await bot.get_me()).id):
        logger.info("Активация по ответу на сообщение бота")
        question = text
        should_respond = True
    
    # Обрабатываем если нужно
    if should_respond and question:
        await process_ai_message(message, question)
    else:
        logger.info("Сообщение не требует ответа - игнорируем")

async def process_ai_message(message: types.Message, question: str):
    """Обработка AI запроса с цепочкой контекста"""
    try:
        logger.info(f"Обрабатываем вопрос: {question}")
        
        # Собираем цепочку сообщений
        message_chain = get_message_chain(message)
        logger.info(f"Собрана цепочка из {len(message_chain)} сообщений")
        
        # Отправляем действие "печатает"
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от Ollama с цепочкой контекста
        response = ollama_client.generate_response(question, message_chain)
        
        # Отправляем ответ
        reply_message = await message.reply(response)
        
        logger.info("Ответ успешно отправлен")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.reply("⚠️ Произошла ошибка при обработке запроса.")

async def main():
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())