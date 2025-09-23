import asyncio
import logging
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

@dp.message(Command("start"))
async def start_command(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(f"🤖 Бот @{bot_info.username} активен! Упоминайте меня в чатах или отвечайте на мои сообщения.")

@dp.message(Command("ping"))
async def ping_command(message: types.Message):
    """Проверка работы бота"""
    await message.answer("🏓 Понг! Бот работает исправно!")

@dp.message()
async def handle_messages(message: types.Message):
    """Обработчик сообщений с поддержкой упоминаний и ответов"""
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower()
    bot_id = bot_info.id
    text = message.text or ""
    
    logger.info(f"Сообщение: {text}")
    logger.info(f"Тип чата: {message.chat.type}")
    logger.info(f"Ответ на сообщение: {message.reply_to_message}")
    
    # Проверяем условия по приоритету:
    
    # 1. Личные сообщения (отвечаем всегда)
    if message.chat.type == "private":
        logger.info("Обрабатываем личное сообщение")
        await process_ai_message(message, text)
        return
    
    # 2. Ответ на сообщение бота
    if (message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_id):
        logger.info("Обрабатываем ответ на сообщение бота")
        await process_ai_message(message, text)
        return
    
    # 3. Упоминание бота в тексте
    if f"@{bot_username}" in text.lower():
        logger.info("Обрабатываем упоминание бота")
        # Извлекаем вопрос после упоминания
        question = text.lower().split(f"@{bot_username}")[-1].strip()
        if question:
            await process_ai_message(message, question)
        else:
            await message.reply("❌ Пожалуйста, задайте вопрос после упоминания!")
        return
    
    logger.info("Сообщение не требует ответа - игнорируем")

async def process_ai_message(message: types.Message, question: str):
    """Обработка AI запроса"""
    try:
        logger.info(f"Обрабатываем вопрос: {question}")
        
        # Отправляем действие "печатает"
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от Ollama
        response = ollama_client.generate_response(question)
        
        # Отправляем ответ
        await message.reply(response)
        
        logger.info("Ответ успешно отправлен")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.reply("⚠️ Произошла ошибка при обработке запроса.")

async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Пропускаем накопленные updates
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())