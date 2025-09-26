import asyncio
import logging
from collections import deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from config import BOT_TOKEN
from ollama_client import OllamaClient
from meme_generator import MemeGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ollama_client = OllamaClient()
meme_generator = MemeGenerator()

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

@dp.message(Command("meme"))
async def meme_command(message: types.Message):
    """Обработчик команды для создания мемов"""
    try:
        print("Получено сообщение:", message.text)
        print("Есть фото:", bool(message.photo))
        print("Caption:", message.caption)
        
        # Способ 1: Проверяем caption (текст прикрепленный к фото)
        if message.caption and message.caption.startswith('/meme'):
            # Используем текст из caption
            meme_text = message.caption.split(' ', 1)[1].strip() if ' ' in message.caption else ""
            use_caption = True
        elif message.text and message.text.startswith('/meme'):
            # Используем текст из message.text
            meme_text = message.text.split(' ', 1)[1].strip() if ' ' in message.text else ""
            use_caption = False
        else:
            await message.answer(
                "📝 **Использование команды /meme:**\n\n"
                "`/meme ваш текст` - создать мем с текстом\n"
                "`/meme ваш текст` + фото - создать мем на вашем фото\n\n"
                "**Примеры:**\n"
                "`/meme Привет мир!`\n"
                "Отправьте фото с подписью `/meme Это тестовый мем`"
            )
            return
        
        # Проверяем, что текст не пустой
        if not meme_text:
            await message.answer("❌ Пожалуйста, укажите текст для мема после команды /meme")
            return
        
        print(f"Текст мема: '{meme_text}'")
        print(f"Используем caption: {use_caption}")
        
        # Проверяем, есть ли прикрепленное фото
        if message.photo:
            print("Обрабатываем фото...")
            # Скачиваем фото
            photo = message.photo[-1]  # Берем самую большую версию фото
            file_info = await bot.get_file(photo.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            # Создаем мем на основе пользовательского фото
            meme_image = await meme_generator.create_meme_from_image(
                image_data=downloaded_file.read(),
                text=meme_text
            )
            
        else:
            print("Создаем мем из шаблона...")
            # Создаем мем со стандартным шаблоном
            meme_image = await meme_generator.create_meme_from_template(
                template_name="default",
                text=meme_text
            )
        
        # Отправляем результат
        meme_file = BufferedInputFile(meme_image, filename="meme.jpg")
        await message.answer_photo(
            meme_file,
            caption=f"🎨 Ваш мем готов!\nТекст: {meme_text}"
        )
        
    except Exception as e:
        logger.error(f"Error creating meme: {e}")
        await message.answer("❌ Произошла ошибка при создании мема. Попробуйте позже.")

# @dp.message(Command("memetemplates"))
# async def meme_templates_command(message: types.Message):
#     """Показать доступные шаблоны мемов"""
#     try:
#         templates = await meme_generator.get_available_templates()
#         templates_text = "📋 **Доступные шаблоны мемов:**\n\n" + "\n".join(
#             f"• {name}" for name in templates
#         )
#         await message.answer(templates_text)
#     except Exception as e:
#         logger.error(f"Error getting templates: {e}")
#         await message.answer("❌ Ошибка при получении списка шаблонов.")


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